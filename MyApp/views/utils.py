from django.contrib.auth.decorators import user_passes_test, login_required
from MyApp.models import Notification

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or 
        (hasattr(user, 'profile') and user.profile.role == 'admin')
    )

def is_accountant(user):
    return user.is_authenticated and (
        user.is_superuser or 
        (hasattr(user, 'profile') and user.profile.role in ['admin', 'accountant'])
    )

def is_warehouse(user):
    return user.is_authenticated and (
        user.is_superuser or 
        (hasattr(user, 'profile') and user.profile.role in ['admin', 'warehouse'])
    )

def is_management_staff(user):
    return user.is_authenticated and (
        user.is_superuser or 
        (hasattr(user, 'profile') and user.profile.role in ['admin', 'accountant', 'warehouse'])
    )

def admin_required(view_func):
    decorated_view = user_passes_test(
        is_admin,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)

def accountant_required(view_func):
    decorated_view = user_passes_test(
        is_accountant,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)

def warehouse_required(view_func):
    decorated_view = user_passes_test(
        is_warehouse,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)

def management_required(view_func):
    decorated_view = user_passes_test(
        is_management_staff,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)

def create_notification(user, notification_type, title, message_text, link='', actor=None):
    Notification.objects.create(
        user=user,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message_text,
        link=link,
    )
