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
    """Thêm sản phẩm vào giỏ hàng"""
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

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variation=variation,
        defaults={'quantity': qty}
    )
    
    if not created:
        cart_item.quantity += qty
        cart_item.save()

    # Optionally remove from wishlist (when adding from wishlist page)
    remove_from_wishlist = (
        request.POST.get('remove_from_wishlist') == '1'
        or request.GET.get('remove_from_wishlist') == '1'
    )
    if remove_from_wishlist and request.user.is_authenticated:
        Wishlist.objects.filter(user=request.user, product=product).delete()

    if request.user.is_authenticated:
        cache.delete(f'user_badges_{request.user.id}')

    messages.success(request, f'Đã thêm "{product.title}" vào giỏ hàng!')
    return redirect(request.META.get('HTTP_REFERER', 'index'))


def cart_remove(request, item_id):
    """Xóa sản phẩm khỏi giỏ hàng"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    title = cart_item.product.title
    cart_item.delete()
    if request.user.is_authenticated:
        cache.delete(f'user_badges_{request.user.id}')
    messages.success(request, f'Đã xóa "{title}" khỏi giỏ hàng.')
    return redirect('cart')


def cart_update(request, item_id):
    """Cập nhật số lượng sản phẩm trong giỏ hàng"""
    if request.method == 'POST':
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            return redirect('cart')
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
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
                # Nếu có rồi thì cộng dồn số lượng
                user_item.quantity += g_item.quantity
                user_item.save()
                g_item.delete() # Xóa item ở giỏ guest
            else:
                # Nếu chưa có thì chuyển item sang giỏ user
                g_item.cart = user_cart
                g_item.save()

        # Áp dụng coupon từ giỏ guest sang giỏ user nếu user chưa có coupon
        if guest_cart.coupon and not user_cart.coupon:
            if guest_cart.coupon.is_valid:
                user_cart.coupon = guest_cart.coupon
                user_cart.save()

        # Xóa giỏ hàng vãng lai sau khi đã merge
        guest_cart.delete()
        
        # Xóa cache badges nếu có
        cache.delete(f'user_badges_{user.id}')
        
    except Cart.DoesNotExist:
        # Không có giỏ hàng vãng lai thì thôi
        pass
    except Exception as e:
        # Tránh làm crash flow login nếu có lỗi merge
        print(f"Error merging cart: {e}")
