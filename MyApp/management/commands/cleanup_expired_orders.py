from django.core.management.base import BaseCommand
from django.utils import timezone
from MyApp.models import Order
from datetime import timedelta

class Command(BaseCommand):
    help = 'Hủy các đơn hàng quá hạn thanh toán để giải phóng kho hàng'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Số giờ tối đa cho phép đơn hàng ở trạng thái chờ trước khi hủy'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        threshold = timezone.now() - timedelta(hours=hours)
        
        # Tìm các đơn hàng đã xác nhận (giữ kho) nhưng chưa thanh toán/xử lý
        # Thường là các đơn qr_bank/transfer bị bỏ quên
        expired_orders = Order.objects.filter(
            status__in=['pending', 'confirmed'],
            created_at__lt=threshold
        ).exclude(payment__payment_method='cod') # Không tự động hủy đơn COD vì khách thanh toán sau

        count = expired_orders.count()
        self.stdout.write(self.style.NOTICE(f'Tìm thấy {count} đơn hàng quá hạn ({hours} giờ)...'))

        cancelled_count = 0
        for order in expired_orders:
            # Kiểm tra xem có payment completed chưa (phòng hờ)
            try:
                if hasattr(order, 'payment') and order.payment.payment_status == 'completed':
                    continue
            except:
                pass

            success, msg = order.action_cancel(note=f"Hủy tự động hệ thống do quá hạn {hours} giờ.")
            if success:
                cancelled_count += 1
                self.stdout.write(self.style.SUCCESS(f'Đã hủy đơn: {order.order_number}'))
            else:
                self.stdout.write(self.style.ERROR(f'Lỗi khi hủy đơn {order.order_number}: {msg}'))

        self.stdout.write(self.style.SUCCESS(f'Hoàn tất! Đã giải phóng kho cho {cancelled_count} đơn hàng.'))
