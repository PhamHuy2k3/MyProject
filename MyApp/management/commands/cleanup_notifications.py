from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from MyApp.models import Notification


class Command(BaseCommand):
    help = 'Delete read notifications older than 30 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=30,
            help='Delete read notifications older than this many days (default: 30)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show count without deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        qs = Notification.objects.filter(is_read=True, created_at__lt=cutoff)
        count = qs.count()

        if options['dry_run']:
            self.stdout.write(f'Would delete {count} read notifications older than {days} days.')
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Deleted {deleted} read notifications older than {days} days.'
        ))
