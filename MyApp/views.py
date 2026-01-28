from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string

from .models import Product, StoryboardItem, RawItem, CabinetItem, UserProfile, Order, Wishlist, Cart, CartItem
from .forms import ProductForm, StoryboardItemForm, RawItemForm, CabinetItemForm, LoginForm, RegisterForm, UserProfileForm


# ==================== HELPER FUNCTIONS ====================

def is_admin(user):
    """Check if user is admin (superuser or staff)"""
    return user.is_superuser or user.is_staff


def admin_required(view_func):
    """Decorator to require admin access"""
    decorated_view = user_passes_test(
        is_admin,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)


# ==================== AUTH VIEWS ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Chào mừng {user.username}!')
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Đăng ký thành công! Chào mừng bạn đến với TeaZen.')
            return redirect('index')
    else:
        form = RegisterForm()
    
    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Đã đăng xuất thành công.')
    return redirect('index')


def password_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # In production, send email here
            # For now, just show success message
            messages.success(request, f'Link đặt lại mật khẩu đã được gửi đến {email}. (Demo: /reset/{uid}/{token}/)')
        except User.DoesNotExist:
            messages.success(request, 'Nếu email tồn tại, link đặt lại sẽ được gửi.')
        
        return redirect('password_reset')
    
    return render(request, 'auth/password_reset.html')


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        validlink = default_token_generator.check_token(user, token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        validlink = False
    
    if request.method == 'POST' and validlink:
        password1 = request.POST.get('new_password1')
        password2 = request.POST.get('new_password2')
        
        if password1 and password1 == password2:
            user.set_password(password1)
            user.save()
            messages.success(request, 'Mật khẩu đã được đặt lại thành công!')
            return redirect('password_reset_complete')
        else:
            messages.error(request, 'Mật khẩu không khớp.')
    
    return render(request, 'auth/password_reset_confirm.html', {'validlink': validlink})


def password_reset_complete_view(request):
    return render(request, 'auth/password_reset_complete.html')


# ==================== PUBLIC VIEWS ====================

def index(request):
    products = Product.objects.all()[:8]
    storyboard = list(StoryboardItem.objects.all()[:6])
    storyboard_columns = [storyboard[i::3] for i in range(3)]
    raws = RawItem.objects.all()[:12]
    cabinet = CabinetItem.objects.all()[:6]

    context = {
        'products': products,
        'storyboard_items': storyboard,
        'storyboard_columns': storyboard_columns,
        'raw_items': raws,
        'cabinet_items': cabinet,
    }
    return render(request, 'index.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'product_detail.html', {'product': product})


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
    return render(request, 'profile.html', context)


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
    
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})


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


# ==================== CART VIEWS ====================

def get_or_create_cart(request):
    """Lấy hoặc tạo giỏ hàng cho user hoặc guest"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Cho guest users, dùng session
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def cart_view(request):
    """Xem giỏ hàng"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'cart.html', context)


def cart_add(request, product_id):
    """Thêm sản phẩm vào giỏ hàng"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f'Đã tăng số lượng "{product.title}" trong giỏ hàng!')
    else:
        messages.success(request, f'Đã thêm "{product.title}" vào giỏ hàng!')
    
    # Kiểm tra nếu là AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'message': f'Đã thêm "{product.title}" vào giỏ hàng!',
            'cart_total': cart.get_total_items()
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'index'))


def cart_remove(request, product_id):
    """Xóa sản phẩm khỏi giỏ hàng"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    
    CartItem.objects.filter(cart=cart, product=product).delete()
    messages.success(request, f'Đã xóa "{product.title}" khỏi giỏ hàng.')
    
    return redirect('cart')


def cart_update(request, product_id):
    """Cập nhật số lượng sản phẩm trong giỏ hàng"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Đã cập nhật số lượng.')
            else:
                cart_item.delete()
                messages.success(request, f'Đã xóa "{product.title}" khỏi giỏ hàng.')
        except CartItem.DoesNotExist:
            pass
    
    return redirect('cart')


# ==================== ADMIN DASHBOARD ====================

@admin_required
def admin_dashboard(request):
    """Trang quản lý chính - Chỉ admin mới truy cập được"""
    context = {
        'products_count': Product.objects.count(),
        'storyboard_count': StoryboardItem.objects.count(),
        'raw_count': RawItem.objects.count(),
        'cabinet_count': CabinetItem.objects.count(),
        'products': Product.objects.all()[:5],
        'storyboard_items': StoryboardItem.objects.all()[:5],
        'raw_items': RawItem.objects.all()[:5],
        'cabinet_items': CabinetItem.objects.all()[:5],
    }
    return render(request, 'admin/dashboard.html', context)


# ==================== PRODUCT CRUD ====================

@admin_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'admin/product_list.html', {'products': products})


@admin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm sản phẩm thành công!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Thêm Sản Phẩm'})


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật sản phẩm thành công!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Sửa Sản Phẩm', 'product': product})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Xóa sản phẩm thành công!')
        return redirect('product_list')
    return render(request, 'admin/confirm_delete.html', {'object': product, 'type': 'sản phẩm'})


# ==================== STORYBOARD CRUD ====================

@admin_required
def storyboard_list(request):
    items = StoryboardItem.objects.all()
    return render(request, 'admin/storyboard_list.html', {'items': items})


@admin_required
def storyboard_create(request):
    if request.method == 'POST':
        form = StoryboardItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm storyboard thành công!')
            return redirect('storyboard_list')
    else:
        form = StoryboardItemForm()
    return render(request, 'admin/storyboard_form.html', {'form': form, 'title': 'Thêm Storyboard'})


@admin_required
def storyboard_edit(request, pk):
    item = get_object_or_404(StoryboardItem, pk=pk)
    if request.method == 'POST':
        form = StoryboardItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật storyboard thành công!')
            return redirect('storyboard_list')
    else:
        form = StoryboardItemForm(instance=item)
    return render(request, 'admin/storyboard_form.html', {'form': form, 'title': 'Sửa Storyboard', 'item': item})


@admin_required
def storyboard_delete(request, pk):
    item = get_object_or_404(StoryboardItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Xóa storyboard thành công!')
        return redirect('storyboard_list')
    return render(request, 'admin/confirm_delete.html', {'object': item, 'type': 'storyboard'})


# ==================== RAW ITEM CRUD ====================

@admin_required
def raw_list(request):
    items = RawItem.objects.all()
    return render(request, 'admin/raw_list.html', {'items': items})


@admin_required
def raw_create(request):
    if request.method == 'POST':
        form = RawItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm raw item thành công!')
            return redirect('raw_list')
    else:
        form = RawItemForm()
    return render(request, 'admin/raw_form.html', {'form': form, 'title': 'Thêm Raw Item'})


@admin_required
def raw_edit(request, pk):
    item = get_object_or_404(RawItem, pk=pk)
    if request.method == 'POST':
        form = RawItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật raw item thành công!')
            return redirect('raw_list')
    else:
        form = RawItemForm(instance=item)
    return render(request, 'admin/raw_form.html', {'form': form, 'title': 'Sửa Raw Item', 'item': item})


@admin_required
def raw_delete(request, pk):
    item = get_object_or_404(RawItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Xóa raw item thành công!')
        return redirect('raw_list')
    return render(request, 'admin/confirm_delete.html', {'object': item, 'type': 'raw item'})


# ==================== CABINET ITEM CRUD ====================

@admin_required
def cabinet_list(request):
    items = CabinetItem.objects.all()
    return render(request, 'admin/cabinet_list.html', {'items': items})


@admin_required
def cabinet_create(request):
    if request.method == 'POST':
        form = CabinetItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm cabinet item thành công!')
            return redirect('cabinet_list')
    else:
        form = CabinetItemForm()
    return render(request, 'admin/cabinet_form.html', {'form': form, 'title': 'Thêm Cabinet Item'})


@admin_required
def cabinet_edit(request, pk):
    item = get_object_or_404(CabinetItem, pk=pk)
    if request.method == 'POST':
        form = CabinetItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật cabinet item thành công!')
            return redirect('cabinet_list')
    else:
        form = CabinetItemForm(instance=item)
    return render(request, 'admin/cabinet_form.html', {'form': form, 'title': 'Sửa Cabinet Item', 'item': item})


@admin_required
def cabinet_delete(request, pk):
    item = get_object_or_404(CabinetItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Xóa cabinet item thành công!')
        return redirect('cabinet_list')
    return render(request, 'admin/confirm_delete.html', {'object': item, 'type': 'cabinet item'})
