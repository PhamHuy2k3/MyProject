from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from MyApp.models import Order, Invoice, Payment
from MyApp.invoices import InvoicePDFGenerator, InvoiceWithQRGenerator
import os


class Command(BaseCommand):
    help = 'Generate invoices từ orders'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--order-ids',
            type=str,
            help='Comma-separated list của order IDs (VD: 1,2,3)',
        )
        
        parser.add_argument(
            '--with-qr',
            action='store_true',
            help='Generate invoices với QR code thanh toán',
        )
        
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Gửi invoice qua email cho khách hàng',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate tất cả invoices (ghi đè file cũ)',
        )
        
        parser.add_argument(
            '--status',
            type=str,
            default='confirmed',
            help='Chỉ generate invoices cho orders có status này (default: confirmed)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Bắt đầu generate invoices...'))
        
        # Xác định orders để generate
        if options['order_ids']:
            order_ids = [int(id.strip()) for id in options['order_ids'].split(',')]
            orders = Order.objects.filter(id__in=order_ids)
        else:
            orders = Order.objects.filter(status=options['status'])
        
        # Nếu không force, chỉ select orders chưa có invoice
        if not options['force']:
            orders = orders.exclude(invoice__isnull=False)
        
        total = orders.count()
        self.stdout.write(f"📦 Tìm thấy {total} orders")
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️  Không có orders để generate'))
            return
        
        # Generate invoices
        success_count = 0
        error_count = 0
        
        for idx, order in enumerate(orders, 1):
            try:
                self.stdout.write(f"\n[{idx}/{total}] Generating {order.order_number}...", ending='')
                
                # Xóa invoice cũ nếu force
                if options['force']:
                    try:
                        order.invoice.delete()
                    except:
                        pass
                
                # Tạo PDF
                if options['with_qr']:
                    generator = InvoiceWithQRGenerator(order, payment_method='bank')
                else:
                    generator = InvoicePDFGenerator(order)
                
                pdf_buffer = generator.generate()
                pdf_bytes = pdf_buffer.getvalue()
                
                # Lưu vào database
                invoice = Invoice.objects.create(
                    order=order,
                    pdf_file=ContentFile(pdf_bytes, name=f'invoice_{order.order_number}.pdf'),
                )
                
                self.stdout.write(self.style.SUCCESS(' ✅'))
                
                # Gửi email nếu yêu cầu
                if options['send_email']:
                    try:
                        self._send_invoice_email(order, pdf_bytes)
                        self.stdout.write(self.style.SUCCESS('   └─ 📧 Email sent'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'   └─ ⚠️  Email failed: {str(e)}'))
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f' ❌ {str(e)}'))
                error_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'✅ Success: {success_count}/{total}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {error_count}/{total}'))
        self.stdout.write('='*70)
    
    def _send_invoice_email(self, order, pdf_bytes):
        """
        Gửi invoice email
        """
        if not order.user.email:
            raise Exception("User không có email")
        
        # Tạo email
        email = EmailMessage(
            subject=f'Hóa đơn {order.order_number} - Tea Company',
            body=f'''
Xin chào {order.user.first_name or order.user.username},

Hóa đơn của bạn đã được tạo thành công.

📋 Chi tiết đơn hàng:
- Số hóa đơn: {order.order_number}
- Tổng tiền: {int(order.total_amount):,} ₫
- Ngày tạo: {order.created_at.strftime('%d/%m/%Y %H:%M')}
- Trạng thái: {order.get_status_display()}

Vui lòng xem hóa đơn đính kèm.

Cảm ơn bạn đã mua hàng!

---
Tea Company
Điện thoại: (84) 123-456-789
Email: admin@teacompany.com
            ''',
            from_email='admin@teacompany.com',
            to=[order.user.email],
        )
        
        # Đính kèm PDF
        email.attach(
            f'invoice_{order.order_number}.pdf',
            pdf_bytes,
            'application/pdf'
        )
        
        # Gửi
        email.send()
        
        # Cập nhật sent_at
        try:
            invoice = order.invoice
            invoice.sent_at = timezone.now()
            invoice.save()
        except:
            pass


# Để chạy command:
# python manage.py generate_invoices
# python manage.py generate_invoices --with-qr --send-email
# python manage.py generate_invoices --order-ids 1,2,3 --force
