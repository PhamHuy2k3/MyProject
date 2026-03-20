from io import BytesIO
from datetime import datetime
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.conf import settings
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import logging

logger = logging.getLogger(__name__)
try:
    font_path = settings.BASE_DIR / 'static' / 'fonts'
    font_candidates = [
        ('Roboto-Regular.ttf', 'Roboto-Bold.ttf'),
        ('roboto-regular.ttf', 'roboto-bold.ttf'),
        ('Arial.ttf', 'Arial-Bold.ttf'),
        ('arial.ttf', 'arialbd.ttf'),
        ('OpenSans-Regular.ttf', 'OpenSans-Bold.ttf'),
        ('TimesNewRoman.ttf', 'TimesNewRoman-Bold.ttf'),
    ]
    
    DEFAULT_FONT = 'Helvetica'
    DEFAULT_FONT_BOLD = 'Helvetica-Bold'
    
    for regular, bold in font_candidates:
        if (font_path / regular).exists():
            pdfmetrics.registerFont(TTFont('VietFont', str(font_path / regular)))
            if (font_path / bold).exists():
                pdfmetrics.registerFont(TTFont('VietFont-Bold', str(font_path / bold)))
            else:
                pdfmetrics.registerFont(TTFont('VietFont-Bold', str(font_path / regular)))
            registerFontFamily('VietFont', normal='VietFont', bold='VietFont-Bold')
            
            DEFAULT_FONT = 'VietFont'
            DEFAULT_FONT_BOLD = 'VietFont-Bold'
            logger.info(f"Loaded Vietnamese font successfully: {regular}")
            break
            
except Exception as e:
    logger.error(f"Error loading font: {e}")
    DEFAULT_FONT = 'Helvetica'
    DEFAULT_FONT_BOLD = 'Helvetica-Bold'


class InvoicePDFGenerator:
    def __init__(self, order):
        self.order = order
        self.user = order.user
        self.user_profile = self.user.profile if hasattr(self.user, 'profile') else None
        
    def generate(self):
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
        )
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=DEFAULT_FONT_BOLD
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            fontName=DEFAULT_FONT_BOLD
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=5,
            fontName=DEFAULT_FONT
        )
        
        elements.append(Paragraph("HÓA ĐƠN THANH TOÁN", title_style))
        elements.append(Spacer(1, 0.15*inch))
        header_data = [
            [
                Paragraph(f"<b>Số hóa đơn:</b> {self.order.order_number}", normal_style),
                Paragraph(f"<b>Ngày lập:</b> {self.order.created_at.strftime('%d/%m/%Y %H:%M')}", normal_style),
            ],
            [
                Paragraph(f"<b>Trạng thái:</b> {self._get_status_display()}", normal_style),
                Paragraph(f"<b>Ngày cập nhật:</b> {self.order.updated_at.strftime('%d/%m/%Y %H:%M')}", normal_style),
            ],
            [
                Paragraph(f"<b>Phương thức TT:</b> {self._get_payment_method_display()}", normal_style),
                Paragraph("", normal_style),
            ],
        ]
        
        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>THÔNG TIN KHÁCH HÀNG</b>", heading_style))
        
        customer_name = self._get_customer_name()
        customer_phone = self.user_profile.phone if self.user_profile else 'N/A'
        customer_address = self.user_profile.address if self.user_profile else 'N/A'
        customer_email = self.user.email
        
        customer_data = [
            [Paragraph(f"<b>Tên:</b> {customer_name}", normal_style)],
            [Paragraph(f"<b>Email:</b> {customer_email}", normal_style)],
            [Paragraph(f"<b>Điện thoại:</b> {customer_phone}", normal_style)],
            [Paragraph(f"<b>Địa chỉ:</b> {customer_address}", normal_style)],
        ]
        
        customer_table = Table(customer_data, colWidths=[6.5*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>CHI TIẾT ĐƠN HÀNG</b>", heading_style))
        
        items_data = [
            ['STT', 'Sản phẩm', 'Số lượng', 'Đơn giá', 'Thành tiền']
        ]
        
        for idx, item in enumerate(self.order.items.all(), 1):
            subtotal = item.get_subtotal()
            items_data.append([
                str(idx),
                item.product_title,
                str(item.quantity),
                self._format_currency(item.price),
                self._format_currency(subtotal),
            ])
        items_data.append([
            '', '', '',
            Paragraph("<b>TỔNG CỘNG:</b>", normal_style),
            Paragraph(f"<b>{self._format_currency(self.order.total_amount)}</b>", normal_style),
        ])
        
        items_table = Table(
            items_data,
            colWidths=[0.5*inch, 3.0*inch, 1.0*inch, 1.0*inch, 1.5*inch]
        )
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('FONTNAME', (0, -1), (-1, -1), DEFAULT_FONT_BOLD),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -2), DEFAULT_FONT),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.2*inch))
        
        if self.order.note:
            elements.append(Paragraph("<b>GHI CHÚ:</b>", heading_style))
            elements.append(Paragraph(self.order.note, normal_style))
            elements.append(Spacer(1, 0.2*inch))
        elements.append(Spacer(1, 0.1*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName=DEFAULT_FONT
        )
        elements.append(Paragraph(
            "Cảm ơn bạn đã mua hàng! | Tea Company | Điện thoại: (84) 123-456-789",
            footer_style
        ))
        
        doc.build(elements)
        
        buffer.seek(0)
        return buffer
    
    def _get_customer_name(self):
        if self.user_profile:
            full_name = self.user_profile.get_full_name()
            if full_name:
                return full_name
        return self.user.username
    
    def _get_status_display(self):
        status_dict = {
            'pending': 'Đang xử lý',
            'confirmed': 'Đã xác nhận',
            'shipping': 'Đang giao',
            'delivered': 'Đã giao',
            'completed': 'Hoàn thành',
            'cancelled': 'Đã hủy',
        }
        return status_dict.get(self.order.status, self.order.status)
    
    def _format_currency(self, amount):
        return f"{int(amount):,.0f} ₫".replace(',', '.')

    def _get_payment_method_display(self):
        try:
            payment = self.order.payment
            return payment.get_payment_method_display()
        except Exception:
            return 'N/A'


class QRCodePaymentGenerator:
    def __init__(self, order, payment_method='bank'):
        self.order = order
        self.payment_method = payment_method
        
    def generate(self, size=10):
        qr_text = self._generate_qr_text()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )
        
        qr.add_data(qr_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    
    def generate_with_logo(self, logo_path=None, size=10):
        img = self.generate(size=size)
        
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path)
            qr_size = img.size[0]
            logo_size = qr_size // 5
            logo = logo.resize((logo_size, logo_size))
            logo_bg = Image.new('RGB', (logo_size + 10, logo_size + 10), 'white')
            logo_bg.paste(logo, (5, 5))
            logo_pos = (
                (qr_size - logo_size - 10) // 2,
                (qr_size - logo_size - 10) // 2
            )
            img.paste(logo_bg, logo_pos)
        
        return img
    
    def generate_to_bytes(self, size=10):
        img = self.generate(size=size)
        
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        return img_io
    
    def _generate_qr_text(self):
        if self.payment_method == 'bank':
            return self._generate_vietqr_text()
        elif self.payment_method == 'vietqr':
            return self._generate_vietqr_text()
        else:
            return self._generate_custom_text()
    
    def _generate_vietqr_text(self):
        from django.conf import settings
        import urllib.parse
        bank_config = getattr(settings, 'BANK_ACCOUNT', {
            'code': 'MB',
            'account_number': '0123456789',
            'account_name': 'Tea Company'
        })
        description = f"TeaZen-{self.order.order_number}"
        amount = int(self.order.total_amount)
        vietqr_text = f"{bank_config['code']}|{bank_config['account_number']}|{amount}|{description}|{bank_config['account_name']}"
        
        return vietqr_text
    
    def _generate_bank_transfer_text(self):
        from django.conf import settings
        
        bank_config = getattr(settings, 'BANK_ACCOUNT', {
            'code': 'MB',
            'account_number': '0123456789',
            'account_name': 'Tea Company'
        })
        
        text = (
            f"BANK_TRANSFER\n"
            f"Bank: {bank_config['code']}\n"
            f"Account: {bank_config['account_number']}\n"
            f"Name: {bank_config['account_name']}\n"
            f"Order: {self.order.order_number}\n"
            f"Amount: {int(self.order.total_amount)} VND"
        )
        return text
    
    def _generate_custom_text(self):
        text = (
            f"PAYMENT\n"
            f"Order: {self.order.order_number}\n"
            f"Customer: {self.order.user.username}\n"
            f"Amount: {int(self.order.total_amount)} VND\n"
            f"Date: {self.order.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return text
    
    def get_qr_data(self):
        return self.generate_to_bytes()


class InvoiceWithQRGenerator:
    
    def __init__(self, order, payment_method='bank'):
        self.order = order
        self.payment_method = payment_method
        self.invoice_gen = InvoicePDFGenerator(order)
        self.qr_gen = QRCodePaymentGenerator(order, payment_method)
    
    def generate(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
        )
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=DEFAULT_FONT_BOLD
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            fontName=DEFAULT_FONT_BOLD
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=5,
            fontName=DEFAULT_FONT
        )
        
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7f8c8d'),
            fontName=DEFAULT_FONT
        )
        elements.append(Paragraph("HÓA ĐƠN THANH TOÁN", title_style))
        elements.append(Spacer(1, 0.1*inch))
        header_data = [
            [
                Paragraph(f"<b>Số hóa đơn:</b> {self.order.order_number}", normal_style),
                Paragraph(f"<b>Ngày lập:</b> {self.order.created_at.strftime('%d/%m/%Y')}", normal_style),
            ],
            [
                Paragraph(f"<b>Trạng thái:</b> {self.invoice_gen._get_status_display()}", normal_style),
                Paragraph(f"<b>Phương thức:</b> {self.invoice_gen._get_payment_method_display()}", normal_style),
            ],
        ]
        
        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # ==================== CUSTOMER INFO ====================
        elements.append(Paragraph("<b>THÔNG TIN KHÁCH HÀNG</b>", heading_style))
        
        customer_name = self.invoice_gen._get_customer_name()
        customer_email = self.order.user.email
        
        customer_data = [
            [Paragraph(f"<b>Tên:</b> {customer_name}", normal_style)],
            [Paragraph(f"<b>Email:</b> {customer_email}", normal_style)],
        ]
        
        customer_table = Table(customer_data, colWidths=[6.5*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # ==================== ORDER ITEMS ====================
        elements.append(Paragraph("<b>CHI TIẾT ĐƠN HÀNG</b>", heading_style))
        
        items_data = [
            ['STT', 'Sản phẩm', 'Số lượng', 'Đơn giá', 'Thành tiền']
        ]
        
        for idx, item in enumerate(self.order.items.all(), 1):
            subtotal = item.get_subtotal()
            items_data.append([
                str(idx),
                item.product_title,
                str(item.quantity),
                self.invoice_gen._format_currency(item.price),
                self.invoice_gen._format_currency(subtotal),
            ])
        
        items_data.append([
            '', '', '',
            Paragraph("<b>TỔNG CỘNG:</b>", normal_style),
            Paragraph(f"<b>{self.invoice_gen._format_currency(self.order.total_amount)}</b>", normal_style),
        ])
        
        items_table = Table(
            items_data,
            colWidths=[0.5*inch, 3.0*inch, 1.0*inch, 1.0*inch, 1.5*inch]
        )
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
            ('FONTNAME', (0, -1), (-1, -1), DEFAULT_FONT_BOLD),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.2*inch))

        # Check if payment is COD
        is_cod = False
        try:
            if self.order.payment and self.order.payment.payment_method == 'cod':
                is_cod = True
        except Exception:
            pass

        if is_cod:
            # COD: Show text instead of QR code
            elements.append(Paragraph("<b>PHƯƠNG THỨC THANH TOÁN</b>", heading_style))
            cod_style = ParagraphStyle(
                'CODInfo',
                parent=normal_style,
                fontSize=12,
                textColor=colors.HexColor('#e67e22'),
                fontName=DEFAULT_FONT_BOLD
            )
            elements.append(Paragraph("💵 THANH TOÁN KHI NHẬN HÀNG (COD)", cod_style))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                f"Khách hàng sẽ thanh toán số tiền <b>{self.invoice_gen._format_currency(self.order.total_amount)}</b> "
                f"trực tiếp cho nhân viên giao hàng khi nhận hàng.",
                normal_style
            ))
        else:
            # QR Bank: Show QR code as before
            elements.append(Paragraph("<b>MÃ QR THANH TOÁN</b>", heading_style))
            qr_img = self.qr_gen.generate(size=8)
            qr_bytes = BytesIO()
            qr_img.save(qr_bytes, format='PNG')
            qr_bytes.seek(0)
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            qr_img.save(temp_file.name)
            temp_file.close()
            qr_code_image = RLImage(
                temp_file.name,
                width=2*inch,
                height=2*inch
            )
            
            qr_info_text = (
                f"<b>Hướng dẫn thanh toán:</b><br/>"
                f"1. Sử dụng ứng dụng ngân hàng hoặc ứng dụng quét mã QR<br/>"
                f"2. Quét mã QR bên cạnh<br/>"
                f"3. Kiểm tra thông tin: Số tiền, Người nhận<br/>"
                f"4. Nhập tham chiếu: {self.order.order_number}<br/>"
                f"5. Xác nhận và gửi<br/><br/>"
                f"<b>Thông tin thanh toán:</b><br/>"
                f"Số tiền: {self.invoice_gen._format_currency(self.order.total_amount)}"
            )
            
            qr_section_data = [
                [
                    qr_code_image,
                    Paragraph(qr_info_text, normal_style)
                ]
            ]
            
            qr_section_table = Table(
                qr_section_data,
                colWidths=[2.5*inch, 4.0*inch],
                rowHeights=[2.5*inch]
            )
            qr_section_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(qr_section_table)
        elements.append(Spacer(1, 0.2*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName=DEFAULT_FONT
        )
        elements.append(Paragraph(
            "Cảm ơn bạn đã mua hàng! | Tea Company | Điện thoại: (84) 123-456-789",
            footer_style
        ))
        doc.build(elements)
        os.unlink(temp_file.name)
        buffer.seek(0)
        return buffer
