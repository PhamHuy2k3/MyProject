"""
Management command: auto-close stale resolved support tickets.
Chạy: python manage.py close_stale_tickets
Cấu hình cron: mỗi giờ, hoặc mỗi 6 giờ.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from MyApp.models import SupportTicket, SupportMessage


class Command(BaseCommand):
    help = 'Tự động đóng các ticket đã resolved sau 24 giờ không được đánh giá'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=24,
            help='Số giờ sau khi resolved để auto-close (mặc định 24h)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Chỉ hiển thị, không thực hiện thay đổi'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(hours=hours)

        # Tickets resolved nhưng chưa closed và đã qua cutoff
        stale_tickets = SupportTicket.objects.filter(
            status='resolved',
            resolved_at__lte=cutoff,
        )

        count = stale_tickets.count()

        if dry_run:
            self.stdout.write(f'[DRY RUN] Sẽ đóng {count} ticket đã resolved quá {hours}h')
            for t in stale_tickets[:10]:
                self.stdout.write(f'  - Ticket #{t.id} | {t.display_name} | resolved: {t.resolved_at}')
            return

        closed_count = 0
        for ticket in stale_tickets:
            # Create system message
            SupportMessage.objects.create(
                ticket=ticket,
                sender_type='system',
                content=f'Ticket đã tự động đóng sau {hours} giờ.',
            )
            ticket.status = 'closed'
            ticket.save(update_fields=['status', 'updated_at'])
            closed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'✓ Đã đóng {closed_count} ticket stale (resolved > {hours}h)')
        )
