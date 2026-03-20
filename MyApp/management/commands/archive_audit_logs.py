import os
import json
import gzip
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from MyApp.audit_models import AuditLog
from MyApp.tasks import process_audit_event_task

class Command(BaseCommand):
    help = 'Archives audit logs older than a specified number of days to compressed JSON and deletes them.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to keep hot logs in the database (default: 90)',
        )

    def handle(self, *args, **options):
        days = options['days']
        threshold_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"Archiving audit logs older than {threshold_date}...")
        
        old_logs = AuditLog.objects.filter(timestamp__lt=threshold_date).order_by('timestamp')
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No logs to archive.'))
            return

        archive_dir = os.path.join(settings.BASE_DIR, 'cold_storage', 'audit_logs')
        os.makedirs(archive_dir, exist_ok=True)
        
        filename = f"audit_archive_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{count}_records.json.gz"
        filepath = os.path.join(archive_dir, filename)
        
        # Serialize to JSON
        logs_data = []
        for log in old_logs:
            logs_data.append({
                'log_id': str(log.log_id),
                'timestamp': log.timestamp.isoformat(),
                'event_type': log.event_type,
                'severity_level': log.severity_level,
                'actor_id': log.actor_id,
                'actor_role': log.actor_role,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                # In archive, we might store them still encrypted or decrypt them.
                # Decrypting them here to store plain text JSON in secure cold storage is usually preferred.
                'before_state': log.before_state,
                'after_state': log.after_state,
                'status': log.status,
                'reason': log.reason,
                'previous_hash': log.previous_hash,
                'current_hash': log.current_hash
            })
            
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=2)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully exported {count} logs to {filepath}"))
        
        # We use queryset.delete() which bypasses the model's delete() restriction
        # to actually purge from the database.
        old_logs.delete()
        
        self.stdout.write(self.style.SUCCESS(f"Purged {count} logs from database."))
        
        # Log this archiving action
        process_audit_event_task({
            'event_type': 'SYSTEM_ARCHIVE_LOGS',
            'severity_level': 'WARNING',
            'actor_id': None,
            'actor_role': 'system',
            'ip_address': '127.0.0.1',
            'user_agent': 'Django Management Command',
            'resource_type': 'AuditLog',
            'resource_id': 'batch',
            'before_state': '',
            'after_state': f"Archived {count} records to {filename}",
            'status': 'SUCCESS',
            'reason': 'Scheduled Data Purging'
        })
