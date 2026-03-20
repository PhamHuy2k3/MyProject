import json
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django_q.tasks import async_task
from django.conf import settings
from .tasks import process_audit_event_task
from .middleware import get_current_request

def async_or_sync_task(func_name, payload):
    sync_mode = getattr(settings, 'Q_CLUSTER', {}).get('sync', False)
    if sync_mode:
        process_audit_event_task(payload)
    else:
        async_task(func_name, payload)
from .models import Order, Product, Category, UserProfile, Coupon, Payment, Invoice, InventoryReceipt, InventoryTransaction, ReturnRequest, StoryboardItem, CabinetItem, RawItem, Review
from django.contrib.auth.models import User

# List of models we want to track CRUD operations for
TRACKED_MODELS = [Order, Product, Category, UserProfile, Coupon, Payment, Invoice, User, InventoryReceipt, InventoryTransaction, ReturnRequest, StoryboardItem, CabinetItem, RawItem, Review]

def get_actor_info():
    """Extracts actor info from current request in thread local"""
    request = get_current_request()
    if not request:
        return {'actor_id': None, 'actor_role': 'system', 'ip_address': None, 'user_agent': 'Background Process'}
    
    user = getattr(request, 'user', None)
    actor_id = getattr(user, 'id', None) if user and user.is_authenticated else None
    
    actor_role = 'customer'
    if user and user.is_authenticated:
        if user.is_superuser:
            actor_role = 'admin'
        elif hasattr(user, 'profile'):
            actor_role = getattr(user.profile, 'role', 'customer')
            
    ip_address = request.META.get('REMOTE_ADDR')
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
        
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    return {
        'actor_id': actor_id,
        'actor_role': actor_role,
        'ip_address': ip_address,
        'user_agent': user_agent[:250]  # truncate to fit in DB field
    }

def serialize_instance(instance):
    """Safely serialize model instance to dict with human-readable labels for FKs and Choices."""
    if not instance:
        return None
    try:
        from django.db.models import ForeignKey
        data = {}
        opts = instance._meta
        
        # We manually build the dict to handle labels better than model_to_dict
        for f in opts.concrete_fields:
            value = f.value_from_object(instance)
            
            # 1. Handle Choices
            if f.choices:
                display_value = getattr(instance, f'get_{f.name}_display')()
                data[f.name] = f"{display_value} ({value})" if value is not None else None
            # 2. Handle Foreign Keys
            elif isinstance(f, ForeignKey):
                related_obj = getattr(instance, f.name)
                if related_obj:
                    data[f.name] = f"{str(related_obj)} [ID: {value}]"
                else:
                    data[f.name] = None
            # 3. Handle normal fields
            else:
                if value is not None and not isinstance(value, (str, int, float, bool, dict, list)):
                    data[f.name] = str(value)
                else:
                    data[f.name] = value
                    
        return data
    except Exception as e:
        return {'id': getattr(instance, 'pk', 'Unknown'), 'error': str(e)}

# ================= AUTH SIGNALS =================

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    actor_info = get_actor_info()
    payload = {
        'event_type': 'AUTH_LOGIN',
        'severity_level': 'INFO',
        **actor_info,
        'resource_type': 'User',
        'resource_id': str(user.id),
        'status': 'SUCCESS',
        'reason': 'User logged in successfully'
    }
    async_or_sync_task('MyApp.tasks.process_audit_event_task', payload)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    actor_info = get_actor_info()
    actor_id = user.id if user else None
    payload = {
        'event_type': 'AUTH_LOGOUT',
        'severity_level': 'INFO',
        **actor_info,
        'actor_id': actor_id,
        'resource_type': 'User',
        'resource_id': str(actor_id) if actor_id else '',
        'status': 'SUCCESS',
        'reason': 'User logged out'
    }
    async_or_sync_task('MyApp.tasks.process_audit_event_task', payload)

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    actor_info = get_actor_info()
    # Mask password
    safe_credentials = {k: v for k, v in credentials.items() if 'password' not in k.lower()}
    
    payload = {
        'event_type': 'AUTH_LOGIN_FAILED',
        'severity_level': 'WARNING',
        **actor_info,
        'actor_id': None,  # Failed login has no user yet
        'resource_type': 'Authentication',
        'resource_id': str(safe_credentials.get('username') or safe_credentials.get('email', '')),
        'before_state': safe_credentials,
        'status': 'FAILED',
        'reason': 'Invalid credentials'
    }
    async_or_sync_task('MyApp.tasks.process_audit_event_task', payload)

# ================= DATA MANIPULATION (CRUD) SIGNALS =================

# Store old state before save to calculate diff
_old_states = {}

@receiver(pre_save)
def capture_old_state(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _old_states[id(instance)] = serialize_instance(old_instance)
        except sender.DoesNotExist:
            _old_states[id(instance)] = None
    else:
        _old_states[id(instance)] = None

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if sender not in TRACKED_MODELS:
        return
        
    actor_info = get_actor_info()
    event_type = 'DATA_CREATE' if created else 'DATA_UPDATE'
    
    after_state = serialize_instance(instance)
    before_state = _old_states.pop(id(instance), None)
    
    if not created and before_state == after_state:
        # No actual change
        return

    payload = {
        'event_type': event_type,
        'severity_level': 'INFO' if event_type == 'DATA_CREATE' else 'WARNING',
        **actor_info,
        'resource_type': sender.__name__,
        'resource_id': str(instance.pk),
        'before_state': before_state if before_state else '',
        'after_state': after_state,
        'status': 'SUCCESS',
        'reason': f'{sender.__name__} was {"created" if created else "updated"}'
    }
    async_or_sync_task('MyApp.tasks.process_audit_event_task', payload)

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return
        
    actor_info = get_actor_info()
    before_state = serialize_instance(instance)
    
    payload = {
        'event_type': 'DATA_DELETE',
        'severity_level': 'CRITICAL',
        **actor_info,
        'resource_type': sender.__name__,
        'resource_id': str(instance.pk),
        'before_state': before_state,
        'after_state': '',
        'status': 'SUCCESS',
        'reason': f'{sender.__name__} was deleted'
    }
    async_or_sync_task('MyApp.tasks.process_audit_event_task', payload)
