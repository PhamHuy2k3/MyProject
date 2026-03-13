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

# ==================== AUTH VIEWS ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
            
            reset_link = request.build_absolute_uri(f'/reset/{uid}/{token}/')
            send_mail(
                'Đặt lại mật khẩu - TeaZen',
                f'Xin chào {user.get_full_name() or user.username},\n\n'
                f'Bạn đã yêu cầu đặt lại mật khẩu. Nhấn vào link sau để tiếp tục:\n\n'
                f'{reset_link}\n\n'
                f'Nếu bạn không yêu cầu, hãy bỏ qua email này.\n\n'
                f'Trân trọng,\nTeaZen',
                None,
                [email],
                fail_silently=False,
            )
            messages.success(request, f'Link đặt lại mật khẩu đã được gửi đến {email}.')
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


