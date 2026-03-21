from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.cache import cache
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
from django.db import transaction

from MyApp.models import *
from MyApp.forms import *
import requests
import json
from .utils import *


def get_or_create_cart(request):
    """Lấy hoặc tạo giỏ hàng cho user hoặc guest"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        # Đảm bảo session được đánh dấu là modified để lưu cookie cho guest (cần thiết cho messages)
        request.session.modified = True
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def cart_view(request):
    """Xem giỏ hàng"""
    cart = get_or_create_cart(request)
    # Thêm prefetch_related('product__images') để tránh N+1 khi gọi product.images.first() trong template
    cart_items = cart.items.select_related('product', 'variation').prefetch_related('product__images').all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'shop/cart.html', context)


def cart_add(request, product_id):
    """Thêm sản phẩm vào giỏ hàng - Giữ chỗ kho hàng"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    variation_id = request.POST.get('variation')
    variation = None
    if variation_id:
        variation = get_object_or_404(product.variations.all(), id=variation_id)

    try:
        qty = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        qty = 1
    qty = max(1, qty)

    # Thực hiện giữ chỗ kho hàng (Reservation)
    with transaction.atomic():
        # Lock target to prevent race condition
        if variation:
            target = ProductVariation.objects.select_for_update().get(id=variation.id)
            product = target.product # Refresh product ref
        else:
            target = Product.objects.select_for_update().get(id=product.id)

        # Check availability
        if target.available_stock < qty:
            messages.error(request, f'Sản phẩm "{product.title}" hiện không đủ tồn kho để thêm vào giỏ.')
            return redirect(request.META.get('HTTP_REFERER', 'index'))

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variation=variation,
            defaults={'quantity': qty}
        )
        
        if not created:
            cart_item.quantity += qty
            cart_item.save()

        # Tăng số lượng tạm giữ
        target.reserved_stock = F('reserved_stock') + qty
        target.save()

        # Ghi log giao dịch kho
        InventoryTransaction.objects.create(
            product=product,
            variation=variation,
            transaction_type='RESERVE',
            quantity=qty,
            user=request.user if request.user.is_authenticated else None,
            reference_id=f"CART_{cart.id} | Giữ hàng khi thêm vào giỏ"[:100]
        )

    if request.user.is_authenticated:
        cache.delete(f'user_badges_{request.user.id}')

    messages.success(request, f'Đã thêm "{product.title}" vào giỏ hàng!')
    return redirect(request.META.get('HTTP_REFERER', 'index'))


def cart_remove(request, item_id):
    """Xóa sản phẩm khỏi giỏ hàng - Giải phóng kho an toàn"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    title = cart_item.product.title
    qty = cart_item.quantity
    product = cart_item.product
    variation = cart_item.variation

    with transaction.atomic():
        # Lấy bản ghi và khóa để cập nhật
        if variation:
            target = ProductVariation.objects.select_for_update().get(id=variation.id)
        else:
            target = Product.objects.select_for_update().get(id=product.id)

        # Đảm bảo không trừ âm - Fallback cho các item cũ chưa được giữ chỗ
        release_qty = min(qty, target.reserved_stock)
        if release_qty > 0:
            target.reserved_stock = F('reserved_stock') - release_qty
            target.save()

            # Ghi log giải phóng kho thực tế
            InventoryTransaction.objects.create(
                product=product,
                variation=variation,
                transaction_type='RELEASE',
                quantity=release_qty,
                user=request.user if request.user.is_authenticated else None,
                reference_id=f"CART_{cart.id} | Giải phóng {release_qty} khi xóa"[:100]
            )

        cart_item.delete()

    if request.user.is_authenticated:
        cache.delete(f'user_badges_{request.user.id}')
    messages.success(request, f'Đã xóa "{title}" khỏi giỏ hàng.')
    return redirect('cart')


def cart_update(request, item_id):
    """Cập nhật số lượng sản phẩm trong giỏ hàng - Điều chỉnh giữ chỗ an toàn"""
    if request.method == 'POST':
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        try:
            new_quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            return redirect('cart')
        
        old_quantity = cart_item.quantity
        delta = new_quantity - old_quantity

        if new_quantity <= 0:
            return cart_remove(request, item_id)

        if delta == 0:
            return redirect('cart')

        product = cart_item.product
        variation = cart_item.variation

        with transaction.atomic():
            if variation:
                target = ProductVariation.objects.select_for_update().get(id=variation.id)
            else:
                target = Product.objects.select_for_update().get(id=product.id)
            
            if delta > 0:
                # Tăng số lượng - Kiểm tra kho
                if target.available_stock < delta:
                    messages.error(request, f'Không đủ hàng để tăng số lượng cho "{product.title}".')
                    return redirect('cart')
                target.reserved_stock = F('reserved_stock') + delta
                trans_type = 'RESERVE'
                actual_delta = delta
                note = f"Tăng số lượng trong giỏ (Cart ID: {cart.id})"
            else:
                # Giảm số lượng - Giải phóng an toàn
                release_qty = min(abs(delta), target.reserved_stock)
                actual_delta = release_qty
                if release_qty > 0:
                    target.reserved_stock = F('reserved_stock') - release_qty
                trans_type = 'RELEASE'
                note = f"Giảm số lượng trong giỏ (Cart ID: {cart.id})"

            target.save()
            cart_item.quantity = new_quantity
            cart_item.save()

            # Ghi log nếu có thay đổi stock thực tế
            if actual_delta > 0:
                InventoryTransaction.objects.create(
                    product=product,
                    variation=variation,
                    transaction_type=trans_type,
                    quantity=actual_delta,
                    user=request.user if request.user.is_authenticated else None,
                    reference_id=f"CART_{cart.id} | {trans_type} {actual_delta}"[:100]
                )

        if request.user.is_authenticated:
            cache.delete(f'user_badges_{request.user.id}')
    return redirect('cart')


def apply_coupon(request):
    """Áp dụng mã giảm giá"""
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip()
        cart = get_or_create_cart(request)
        if not code:
            cart.coupon = None
            cart.save()
            return redirect('cart')
        try:
            coupon = Coupon.objects.get(code__iexact=code)
            if coupon.is_valid:
                cart.coupon = coupon
                cart.save()
                messages.success(request, 'Áp dụng mã giảm giá thành công!')
            else:
                messages.error(request, 'Mã giảm giá không hợp lệ.')
        except Coupon.DoesNotExist:
            messages.error(request, 'Mã giảm giá không tồn tại.')
    return redirect('cart')


def merge_cart_items(user, session_key):
    """
    Chuyển các sản phẩm từ giỏ hàng vãng lai (guest) sang giỏ hàng của user sau khi đăng nhập.
    """
    if not session_key:
        return

    try:
        # Lấy giỏ hàng vãng lai
        guest_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
        # Lấy hoặc tạo giỏ hàng của user
        user_cart, created = Cart.objects.get_or_create(user=user)

        guest_items = guest_cart.items.all()
        for g_item in guest_items:
            # Kiểm tra xem sản phẩm (+ biến thể) đã có trong giỏ hàng user chưa
            user_item = user_cart.items.filter(
                product=g_item.product,
                variation=g_item.variation
            ).first()

            if user_item:
                # Nếu có rồi thì cộng dồn số lượng. 
                # Lưu ý: g_item đã thực hiện giữ chỗ rồi, nên khi gộp vào user_item 
                # thì TỔNG reserved_stock trên toàn hệ thống không đổi.
                user_item.quantity += g_item.quantity
                user_item.save()
                g_item.delete() # Xóa item ở giỏ guest (không release vì đã merge sang user_item)
            else:
                # Nếu chưa có thì chuyển item sang giỏ user
                g_item.cart = user_cart
                g_item.save()

        # Áp dụng coupon từ giỏ guest sang giỏ user nếu user chưa có coupon
        if guest_cart.coupon and not user_cart.coupon:
            if guest_cart.coupon.is_valid:
                user_cart.coupon = guest_cart.coupon
                user_cart.save()

        # Xóa giỏ hàng vãng lai sau khi đã merge. 
        # Cực kỳ quan trọng: Phải bảo lưu reserved_stock vì item đã được chuyển.
        guest_cart.delete()
        
        # Xóa cache badges nếu có
        cache.delete(f'user_badges_{user.id}')
        
    except Cart.DoesNotExist:
        # Không có giỏ hàng vãng lai thì thôi
        pass
    except Exception as e:
        # Tránh làm crash flow login nếu có lỗi merge
        print(f"Error merging cart: {e}")
