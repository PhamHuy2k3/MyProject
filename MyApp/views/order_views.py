from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from MyApp.models import Order, OrderItem, Payment, Notification
from .cart_views import get_or_create_cart
from .utils import create_notification, is_accountant


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
    except Exception:
        payment = None
    try:
        invoice = order.invoice
    except Exception:
        invoice = None
    return render(request, 'orders/order_detail.html', {'order': order, 'payment': payment, 'invoice': invoice})


@login_required(login_url='login')
def invoice_pdf(request, order_number):
    from django.http import HttpResponse
    from MyApp.invoices import InvoicePDFGenerator
    order = get_object_or_404(Order, order_number=order_number)
    if not (order.user == request.user or is_accountant(request.user) or request.user.is_staff):
        messages.error(request, 'Bạn không có quyền truy cập hóa đơn này.')
        return redirect('order_list')
    generator = InvoicePDFGenerator(order)
    pdf_buffer = generator.generate()
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="hoa-don-{order.order_number}.pdf"'
    return response


@login_required(login_url='login')
def invoice_pdf_with_qr(request, order_number):
    from django.http import HttpResponse
    from MyApp.invoices import InvoiceWithQRGenerator
    order = get_object_or_404(Order, order_number=order_number)
    if not (order.user == request.user or is_accountant(request.user) or request.user.is_staff):
        messages.error(request, 'Bạn không có quyền truy cập hóa đơn này.')
        return redirect('order_list')
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

    if not (request.user == order.user or is_accountant(request.user) or request.user.is_staff):
        messages.error(request, 'Bạn không có quyền truy cập dữ liệu này.')
        return redirect('order_list')

    root = ET.Element("Invoice")
    company_info = ET.SubElement(root, "CompanyInfo")
    ET.SubElement(company_info, "Name").text = "TeaZen"

    order_info = ET.SubElement(root, "OrderInfo")
    ET.SubElement(order_info, "OrderNumber").text = str(order.order_number)
    ET.SubElement(order_info, "OrderDate").text = order.created_at.strftime("%Y-%m-%d %H:%M:%S")
    ET.SubElement(order_info, "Status").text = str(order.get_status_display())

    customer_info = ET.SubElement(root, "CustomerInfo")
    ET.SubElement(customer_info, "CustomerName").text = str(order.user.get_full_name() or order.user.username)
    ET.SubElement(customer_info, "CustomerEmail").text = str(order.user.email)

    items = ET.SubElement(root, "Items")
    for item in order.items.all():
        item_el = ET.SubElement(items, "Item")
        ET.SubElement(item_el, "ProductName").text = str(item.product_title)
        if item.variation:
            ET.SubElement(item_el, "Variation").text = str(item.variation.title)
        ET.SubElement(item_el, "Quantity").text = str(item.quantity)
        ET.SubElement(item_el, "UnitPrice").text = str(item.price)
        ET.SubElement(item_el, "SubTotal").text = str(item.get_subtotal())

    totals = ET.SubElement(root, "Totals")
    ET.SubElement(totals, "DiscountAmount").text = str(order.discount_amount)
    ET.SubElement(totals, "TotalAmount").text = str(order.total_amount)

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    response = HttpResponse(xml_str, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="order-{order.order_number}.xml"'
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
        except Exception:
            pass

    return render(request, 'orders/payment.html', {
        'order': order,
        'payment': payment,
        'qr_base64': qr_base64,
        'qr_image_url': qr_image_url
    })


@login_required(login_url='login')
def payment_qr_image(request, order_number):
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
    from django.http import JsonResponse

    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if request.method == 'POST':
        try:
            payment = order.payment
        except Exception:
            return JsonResponse({'success': False, 'message': 'Không tìm thấy thông tin thanh toán.'}, status=400)
        if payment.payment_status in ('pending_verification', 'completed'):
            return JsonResponse({'success': True, 'message': 'Đã ghi nhận yêu cầu xác nhận thanh toán.'})
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
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'variation').all()

    if not cart_items.exists():
        messages.warning(request, 'Giỏ hàng của bạn đang trống!')
        return redirect('cart')

    # Get user profile info for form defaults
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
        note = request.POST.get('note', '').strip()
        total_amount = cart.get_total_price()
        discount_amount = cart.get_discount_amount()

        for item in cart_items:
            target = item.variation if item.variation else item.product
            if target and target.available_stock < item.quantity:
                messages.error(request, f"Sản phẩm {target} không đủ tồn kho khả dụng.")
                return redirect('cart')

        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            status='pending',
            note=note,
            coupon=cart.coupon,
            discount_amount=discount_amount
        )

        for item in cart_items:
            item_price = item.variation.price if (item.variation and item.variation.price) else item.product.price
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variation=item.variation,
                product_title=item.product.title,
                quantity=item.quantity,
                price=item_price or 0
            )

        order.set_status('pending', user=request.user, note="Tạo đơn hàng.")

        # Notify staff about new order
        staff_users = User.objects.filter(is_staff=True)
        for staff_user in staff_users:
            create_notification(
                user=staff_user,
                notification_type='order',
                title=f'Đơn hàng mới {order.order_number}',
                message_text=f'{request.user.username} đã đặt {order.items.count()} sản phẩm.',
                link=f'/manage/orders/{order.order_number}/manage/'
            )

        Payment.objects.create(order=order, amount=total_amount, payment_method='qr_bank')

        cart_items.delete()
        cart.coupon = None
        cart.save()
        if request.user.is_authenticated:
            cache.delete(f'user_badges_{request.user.id}')

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
    """
    from django.http import JsonResponse
    from django.conf import settings
    import logging
    import re

    logger = logging.getLogger(__name__)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    casso_apikey = getattr(settings, 'CASSO_APIKEY', '')
    if casso_apikey:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Apikey ') or auth_header[7:] != casso_apikey:
            logger.warning("Casso webhook: Invalid API Key")
            return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = request.body.decode('utf-8')
    except Exception:
        payload = ''

    try:
        data = request.json if hasattr(request, 'json') else None
    except Exception:
        data = None

    if data is None:
        try:
            import json as _json
            data = _json.loads(payload)
        except Exception:
            data = {}

    transactions = data.get('data', [])
    matched_count = 0

    for t in transactions:
        description = str(t.get('description', '')).upper()
        amount = t.get('amount', 0)
        if not description:
            continue

        match = re.search(r'ORD-\d{8}-[A-Z0-9]{6}', description)
        if not match:
            continue

        order_number = match.group(0)
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            logger.warning(f"Casso: order not found for {order_number}")
            continue

        expected = int(order.total_amount)
        received = int(amount)
        if abs(received - expected) > 1000:
            logger.warning(
                f"Casso: amount mismatch for {order.order_number}: "
                f"expected {expected}, received {received}"
            )
            continue

        try:
            payment = order.payment
        except Exception:
            logger.warning(f"Casso: no payment record for order {order.order_number}")
            continue

        if payment.payment_status == 'completed':
            logger.info(f"Casso: order {order.order_number} already completed, skipping")
            continue

        if order.status in ['cancelled', 'refunded', 'exchanged', 'return_requested', 'return_approved', 'returned']:
            logger.warning(f"Casso: order {order.order_number} is not eligible for payment confirm")
            continue

        if order.status == 'pending':
            success, message = order.action_confirm()  # Reserve stock
            if not success:
                logger.error(f"Casso: stock reservation failed for order {order.order_number}: {message}")
                from datetime import datetime
                payment.payment_status = 'completed'
                payment.payment_date = datetime.now()
                payment.notes = f"Payment received but stock reservation failed: {message}"
                payment.save()
                order.set_status('pending', note="Đã nhận thanh toán nhưng thiếu tồn kho.")
                create_notification(
                    user=order.user,
                    notification_type='order',
                    title=f'Đã nhận thanh toán cho đơn {order.order_number}',
                    message_text='Tuy nhiên kho đang thiếu hàng cho một số sản phẩm. Chúng tôi sẽ liên hệ để xử lý.',
                    link=f'/order/{order.order_number}/',
                )
                continue
        else:
            order.ensure_invoice()

        from datetime import datetime
        payment.payment_status = 'completed'
        payment.payment_date = datetime.now()
        payment.save()

        try:
            invoice = order.invoice
        except Exception:
            invoice = None
        if invoice and invoice.status != 'paid':
            invoice.status = 'paid'
            invoice.save(update_fields=['status'])

        create_notification(
            user=order.user,
            notification_type='order',
            title=f'Thanh toán đơn {order.order_number} thành công!',
            message_text=f'Hệ thống đã xác nhận giao dịch {received:,}đ từ tài khoản của bạn.',
            link=f'/order/{order.order_number}/',
        )

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
