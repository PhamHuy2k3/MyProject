from django.contrib.auth.decorators import user_passes_test, login_required
from MyApp.models import Notification
from django.db.models import Q
import re

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

def get_smart_search_filter(query, fields):
    """
    Returns a Q object that cleans the search query and ensures all words
    are present across the specified fields.
    """
    if not query:
        return Q()

    # Clean query: Remove punctuation and special characters
    # Keep alphanumeric (including Vietnamese chars) and spaces
    # \w in Python 3 includes Unicode word characters by default
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    words = clean_query.split()

    if not words:
        return Q()

    # Combine words with AND logic
    # Each word must appear in at least one of the specified fields
    combined_q = Q()
    for word in words:
        word_q = Q()
        for field in fields:
            # We use icontains for partial matching of each word
            word_q |= Q(**{f"{field}__icontains": word})
        
        if combined_q:
            combined_q &= word_q
        else:
            combined_q = word_q

    return combined_q
