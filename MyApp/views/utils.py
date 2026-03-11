from django.contrib.auth.decorators import user_passes_test, login_required
from MyApp.models import Notification

def is_admin(user):
    return user.is_superuser or user.is_staff

def admin_required(view_func):
    decorated_view = user_passes_test(
        is_admin,
        login_url='login',
        redirect_field_name='next'
    )(view_func)
    return login_required(login_url='login')(decorated_view)

def create_notification(user, notification_type, title, message_text, link=''):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message_text,
        link=link,
    )
