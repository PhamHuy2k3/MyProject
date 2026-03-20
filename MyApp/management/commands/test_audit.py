from django.core.management.base import BaseCommand
from MyApp.audit_models import AuditLog
from MyApp.tasks import process_audit_event_task

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        payload = {
            'event_type': 'TEST',
            'severity_level': 'INFO',
            'actor_id': 1,
            'actor_role': 'admin',
            'ip_address': '127.0.0.1',
            'user_agent': 'CMD',
            'resource_type': 'TEST',
            'resource_id': '1',
            'before_state': 'old',
            'after_state': 'new',
            'status': 'SUCCESS',
            'reason': 'Test'
        }
        
        try:
            print("Calling process_audit_event_task...")
            process_audit_event_task(payload)
            print("Counts after:", AuditLog.objects.count())
        except Exception as e:
            print("OUTER EXCEPTION:", e)
