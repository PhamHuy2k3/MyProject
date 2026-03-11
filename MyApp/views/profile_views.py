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

# ==================== USER PROFILE VIEWS ====================

@login_required(login_url='login')
def profile_view(request):
    """Trang cá nhân của người dùng"""
    user = request.user
    
    # Đảm bảo user có profile
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    profile = user.profile
    orders = Order.objects.filter(user=user)[:5]
    wishlists = Wishlist.objects.filter(user=user).select_related('product')[:4]
    total_orders = Order.objects.filter(user=user).count()
    
    context = {
        'profile': profile,
        'orders': orders,
        'wishlists': wishlists,
        'total_orders': total_orders,
    }
    return render(request, 'users/profile.html', context)


@login_required(login_url='login')
def profile_edit(request):
    """Chỉnh sửa thông tin cá nhân"""
    user = request.user
    
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    profile = user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if form.is_valid():
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            form.save()
            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'users/profile_edit.html', {'form': form, 'profile': profile})


@login_required(login_url='login')
def wishlist_add(request, product_id):
    """Thêm sản phẩm vào wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    
    if created:
        messages.success(request, f'Đã thêm "{product.title}" vào danh sách yêu thích!')
    else:
        messages.info(request, f'"{product.title}" đã có trong danh sách yêu thích.')
    
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required(login_url='login')
def wishlist_remove(request, product_id):
    """Xóa sản phẩm khỏi wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'Đã xóa "{product.title}" khỏi danh sách yêu thích.')
    return redirect(request.META.get('HTTP_REFERER', 'profile'))


@login_required(login_url='login')
def wishlist_view(request):
    """Xem danh sách yêu thích"""
    wishlists = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'shop/wishlist.html', {'wishlists': wishlists})


@login_required(login_url='login')
def profile_quick_update(request):
    """AJAX endpoint: quickly update phone and address from checkout page"""
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)

    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()

    if not phone:
        return JsonResponse({'success': False, 'message': 'Số điện thoại không được để trống.'})
    if not address:
        return JsonResponse({'success': False, 'message': 'Địa chỉ không được để trống.'})

    # Get or create profile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.phone = phone
    profile.address = address
    profile.save()

    return JsonResponse({'success': True, 'message': 'Cập nhật thành công!'})
