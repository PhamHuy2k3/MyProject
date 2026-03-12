from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Count, Sum, Avg, F, Q, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from MyApp.models import *
from MyApp.forms import *
import requests
import json
from .utils import *

# ==================== INVOICE & PAYMENT VIEWS ====================

@login_required(login_url='login')
def order_list(request):
    orders = request.user.orders.all().order_by('-created_at')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required(login_url='login')
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    try:
        payment = order.payment
    except:
        payment = None
    try:
        invoice = order.invoice
    except:
        invoice = None
    return render(request, 'orders/order_detail.html', {'order': order, 'payment': payment, 'invoice': invoice})


@login_required(login_url='login')
def invoice_pdf(request, order_number):
    from django.http import HttpResponse
    from MyApp.invoices import InvoicePDFGenerator
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    generator = InvoicePDFGenerator(order)
    pdf_buffer = generator.generate()
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="hoa-don-{order.order_number}.pdf"'
    return response


@login_required(login_url='login')
def invoice_pdf_with_qr(request, order_number):
    from django.http import HttpResponse
    from MyApp.invoices import InvoiceWithQRGenerator
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment_method = request.GET.get('method', 'bank')
    generator = InvoiceWithQRGenerator(order, payment_method=payment_method)
    pdf_buffer = generator.generate()
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="hoa-don-{order.order_number}.pdf"'
    return response


@login_required(login_url='login')
def export_order_xml(request, order_number):
    """Xuất thông tin đơn hàng ra file XML cho hệ thống kế toán"""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    from django.http import HttpResponse

    order = get_object_or_404(Order, order_number=order_number)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.is_staff or request.user == order.user):
        messages.error(request, 'Bạn không có quyền truy cập dữ liệu này.')
        return redirect('order_detail', order_number=order_number)

    root = ET.Element("Invoice")
    
    # Company details
    company_info = ET.SubElement(root, "CompanyInfo")
    ET.SubElement(company_info, "Name").text = "TeaZen"
    
    # Order Details
    order_info = ET.SubElement(root, "OrderInfo")
    ET.SubElement(order_info, "OrderNumber").text = str(order.order_number)
    ET.SubElement(order_info, "OrderDate").text = order.created_at.strftime("%Y-%m-%d %H:%M:%S")
    ET.SubElement(order_info, "Status").text = str(order.get_status_display())
    
    # Customer Details
    customer_info = ET.SubElement(root, "CustomerInfo")
    ET.SubElement(customer_info, "CustomerName").text = str(order.user.get_full_name() or order.user.username)
    ET.SubElement(customer_info, "CustomerEmail").text = str(order.user.email)
    
    # Order Items
    items = ET.SubElement(root, "Items")
    for item in order.items.all():
        item_el = ET.SubElement(items, "Item")
        ET.SubElement(item_el, "ProductName").text = str(item.product_title)
        if item.variation:
            ET.SubElement(item_el, "Variation").text = str(item.variation.title)
        ET.SubElement(item_el, "Quantity").text = str(item.quantity)
        ET.SubElement(item_el, "UnitPrice").text = str(item.price)
        ET.SubElement(item_el, "SubTotal").text = str(item.get_subtotal())
        
    # Totals
    totals = ET.SubElement(root, "Totals")
    ET.SubElement(totals, "DiscountAmount").text = str(order.discount_amount)
    ET.SubElement(totals, "TotalAmount").text = str(order.total_amount)
    
    # Convert to formatted string
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    response = HttpResponse(xmlstr, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="hoa_don_xuat_{order.order_number}.xml"'
    return response



@login_required(login_url='login')
@ensure_csrf_cookie
def payment_view(request, order_number):
    from MyApp.vietqr_service import VietQRService
    from MyApp.invoices import QRCodePaymentGenerator
    import base64
    from io import BytesIO
    import logging
    
    logger = logging.getLogger(__name__)
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={'amount': order.total_amount, 'payment_method': 'qr_bank'}
    )
    
    qr_base64 = None
    qr_image_url = None
    vietqr_error = None
    
    try:
        service = VietQRService()
        if service.client_id:
            qr_result = service.generate_qr_code(order, qr_type=0)
            qr_image_url = qr_result.get('qrLink')
    except Exception as e:
        logger.warning(f"VietQR error: {e}")
    
    if not qr_image_url:
        try:
            qr_gen = QRCodePaymentGenerator(order, payment_method='bank')
            qr_img = qr_gen.generate(size=8)
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format='PNG')
            qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        except:
            pass
    
    return render(request, 'orders/payment.html', {
        'order': order,
        'payment': payment,
        'qr_base64': qr_base64,
        'qr_image_url': qr_image_url
    })


@login_required(login_url='login')
def payment_qr_image(request, order_number):
    """API endpoint để lấy QR code dưới dạng hình ảnh"""
    from django.http import HttpResponse
    from MyApp.invoices import QRCodePaymentGenerator
    from io import BytesIO
    
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    qr_gen = QRCodePaymentGenerator(order, payment_method='bank')
    qr_img = qr_gen.generate(size=8)
    
    img_buffer = BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    response = HttpResponse(img_buffer, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_{order.order_number}.png"'
    return response


@login_required(login_url='login')
def payment_confirm(request, order_number):
    """User reports they have transferred money — mark as pending_verification for admin review"""
    from django.http import JsonResponse
    from datetime import datetime

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if request.method == 'POST':
        try:
            payment = order.payment
        except Exception:
            return JsonResponse({'success': False, 'message': 'Không tìm thấy thông tin thanh toán.'}, status=400)

        # Prevent re-submission if already submitted or completed
        if payment.payment_status in ('pending_verification', 'completed'):
            return JsonResponse({'success': True, 'message': 'Đã ghi nhận yêu cầu xác nhận thanh toán.'})

        # Mark as pending verification — admin will confirm manually
        payment.payment_status = 'pending_verification'
        payment.save()

        create_notification(
            user=order.user,
            notification_type='order',
            title=f'Đã nhận yêu cầu xác nhận đơn hàng {order.order_number}',
            message_text='Chúng tôi sẽ kiểm tra giao dịch và xác nhận trong vòng 1–24h.',
            link=f'/order/{order.order_number}/',
        )

        return JsonResponse({'success': True, 'message': 'Yêu cầu đã được ghi nhận. Vui lòng chờ xác nhận.'})

    return redirect('payment', order_number=order_number)


@login_required(login_url='login')
def checkout(request):
    """Trang checkout - tạo đơn hàng từ giỏ hàng"""
    from .cart_views import get_or_create_cart
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'variation').all()
    
    if not cart_items.exists():
        messages.warning(request, 'Giỏ hàng của bạn đang trống!')
        return redirect('cart')
    
    # Get user profile info
    try:
        profile = request.user.profile
        full_name = profile.get_full_name()
        phone = profile.phone or ''
        address = profile.get_full_address() or profile.address or ''
    except Exception:
        full_name = request.user.username
        phone = ''
        address = ''
        profile = None
    
    if request.method == 'POST':
        note = request.POST.get('note', '')
        total_amount = cart.get_total_price()
        
        # Check stock
        insufficient = []
        for item in cart_items:
            stock = item.variation.stock_quantity if item.variation else item.product.stock_quantity
            if stock < item.quantity:
                insufficient.append(item.product.title)
        
        if insufficient:
            messages.error(request, f"Không đủ hàng cho: {', '.join(insufficient)}")
            return redirect('cart')

        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            status='pending',
            note=note,
            coupon=cart.coupon
        )
        
        for item in cart_items:
            # Determine item price (variation price or product price)
            item_price = item.variation.price if (item.variation and item.variation.price) else item.product.price
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variation=item.variation,
                product_title=item.product.title,
                quantity=item.quantity,
                price=item_price or 0
            )
        
        Payment.objects.create(order=order, amount=total_amount, payment_method='qr_bank')
        cart_items.delete()
        cart.coupon = None
        cart.save()
        
        # Send order confirmation email
        if request.user.email:
            items_text = '\n'.join(
                f'  - {item.product.title} x{item.quantity}'
                for item in order.items.all()
            )
            send_mail(
                f'Xác nhận đơn hàng {order.order_number} - TeaZen',
                f'Xin chào {request.user.get_full_name() or request.user.username},\n\n'
                f'Đơn hàng của bạn đã được tạo thành công!\n\n'
                f'Mã đơn: {order.order_number}\n'
                f'Sản phẩm:\n{items_text}\n\n'
                f'Tổng tiền: {total_amount:,.0f}đ\n\n'
                f'Vui lòng thanh toán để chúng tôi xử lý đơn hàng.\n\n'
                f'Trân trọng,\nTeaZen',
                None,
                [request.user.email],
                fail_silently=True,
            )

        messages.success(request, 'Đơn hàng đã được tạo!')
        return redirect('payment', order_number=order.order_number)
    
    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': cart.get_total_price(),
        'full_name': full_name,
        'phone': phone,
        'address': address,
        'profile': profile,
    })


# ==================== CASSO WEBHOOK (AUTO PAYMENT CONFIRM) ====================

@csrf_exempt
def casso_webhook(request):
    """
    Webhook endpoint for Casso (casso.vn) - auto-confirms payment when
    Casso detects an incoming bank transfer matching an order code.
    
    Setup guide:
    1. Register at casso.vn and link your bank account
    2. Set webhook URL to: https://yourdomain.com/api/webhook/casso/
    3. Set CASSO_APIKEY in settings.py (get from Casso dashboard)
    
    Casso sends a POST request like:
    {
        "data": [{
            "id": 123456,
            "tid": "TXN_ID",
            "description": "TeaZen55D953 chuyen khoan",
            "amount": 450000,
            "when": "2026-03-10 20:00:00",
            "bank_name": "MB Bank",
            "account_name": "NGUYEN VAN A"
        }]
    }
    """
    from django.http import JsonResponse
    from django.conf import settings
    import logging
    import re

    logger = logging.getLogger(__name__)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Verify Casso API Key from Authorization header
    casso_apikey = getattr(settings, 'CASSO_APIKEY', '')
    if casso_apikey:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Apikey ') or auth_header[7:] != casso_apikey:
            logger.warning("Casso webhook: Invalid API Key")
            return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    transactions = body.get('data', [])
    if not transactions:
        return JsonResponse({'status': 'ok', 'matched': 0})

    matched_count = 0

    for txn in transactions:
        description = txn.get('description', '') or ''
        amount = txn.get('amount', 0)

        logger.info(f"Casso webhook received: amount={amount}, desc={description[:60]}")

        # Look for order code pattern "TeaZen" + 6 chars in the description
        # We encode it as "TeaZenXXXXXX" in VietQR addInfo
        pattern = re.compile(r'TeaZen([A-Z0-9]{6})', re.IGNORECASE)
        match = pattern.search(description)
        if not match:
            # Also try matching full order number pattern ORD-YYYYMMDD-XXXXXX
            pattern2 = re.compile(r'ORD-\d{8}-[A-Z0-9]{6}', re.IGNORECASE)
            match2 = pattern2.search(description)
            if match2:
                order_number_partial = match2.group(0).upper()
                try:
                    order = Order.objects.get(order_number=order_number_partial)
                except Order.DoesNotExist:
                    continue
            else:
                logger.debug(f"Casso: no order code found in: {description[:60]}")
                continue
        else:
            order_suffix = match.group(1).upper()
            # Find the order by last 6 chars of order_number
            try:
                order = Order.objects.get(order_number__endswith=order_suffix)
            except Order.DoesNotExist:
                logger.warning(f"Casso: order with suffix '{order_suffix}' not found")
                continue
            except Order.MultipleObjectsReturned:
                logger.warning(f"Casso: multiple orders found with suffix '{order_suffix}', skipping")
                continue

        # Validate that amount matches (allow minor rounding tolerance of 1000đ)
        expected = int(order.total_amount)
        received = int(amount)
        if abs(received - expected) > 1000:
            logger.warning(
                f"Casso: amount mismatch for {order.order_number}: "
                f"expected {expected}, received {received}"
            )
            continue

        # Get payment record
        try:
            payment = order.payment
        except Exception:
            logger.warning(f"Casso: no payment record for order {order.order_number}")
            continue

        # Skip if already confirmed
        if payment.payment_status == 'completed':
            logger.info(f"Casso: order {order.order_number} already completed, skipping")
            continue

        # AUTO-CONFIRM ✅
        from MyApp.models import check_and_deduct_stock

        ok, insufficient = check_and_deduct_stock(order)
        if not ok:
            logger.error(f"Casso: stock insufficient for order {order.order_number}: {insufficient}")
            continue

        from datetime import datetime
        payment.payment_status = 'completed'
        payment.stock_deducted = True
        payment.payment_date = datetime.now()
        payment.save()

        order.status = 'confirmed'
        order.save()

        create_notification(
            user=order.user,
            notification_type='order',
            title=f'Thanh toán đơn {order.order_number} thành công! 🎉',
            message_text=f'Hệ thống đã xác nhận giao dịch {received:,}đ từ tài khoản của bạn.',
            link=f'/order/{order.order_number}/',
        )

        # Send payment confirmation email
        if order.user.email:
            send_mail(
                f'Thanh toán đơn {order.order_number} thành công! - TeaZen',
                f'Xin chào {order.user.get_full_name() or order.user.username},\n\n'
                f'Chúng tôi đã xác nhận thanh toán {received:,}đ cho đơn hàng {order.order_number}.\n\n'
                f'Đơn hàng của bạn đang được xử lý.\n\n'
                f'Trân trọng,\nTeaZen',
                None,
                [order.user.email],
                fail_silently=True,
            )

        logger.info(f"✅ Casso auto-confirmed payment for order {order.order_number}")
        matched_count += 1

    return JsonResponse({'status': 'ok', 'matched': matched_count})
