from django.core.management.base import BaseCommand
from django.utils import timezone
from MyApp.models import Cart, CartItem, InventoryTransaction, Product, ProductVariation
from datetime import timedelta
from django.db import transaction
from django.db.models import F

class Command(BaseCommand):
    help = 'Giải phóng kho hàng cho các giỏ hàng đã hết hạn (không hoạt động quá 60 phút)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=60,
            help='Số phút tối đa cho phép giỏ hàng không hoạt động trước khi giải phóng kho'
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        threshold = timezone.now() - timedelta(minutes=minutes)
        
        # Tìm các giỏ hàng không được cập nhật sau thời gian threshold
        expired_carts = Cart.objects.filter(updated_at__lt=threshold)
        
        total_released = 0
        cart_count = expired_carts.count()
        
        self.stdout.write(self.style.NOTICE(f"Đang kiểm tra {cart_count} giỏ hàng quá hạn..."))

        for cart in expired_carts:
            items = cart.items.all()
            if not items.exists():
                # Xóa giỏ trống quá hạn giúp dọn dẹp DB
                cart.delete()
                continue
                
            with transaction.atomic():
                for item in items:
                    try:
                        target = item.variation if item.variation else item.product
                        if not target:
                            continue
                            
                        # Lock target để tránh race condition khi hoàn trả
                        target = type(target).objects.select_for_update().get(id=target.id)
                        
                        # Giải phóng stock - đảm bảo không bị âm (Safe Release)
                        release_qty = min(item.quantity, target.reserved_stock)
                        if release_qty > 0:
                            target.reserved_stock = F('reserved_stock') - release_qty
                            target.save()
                            
                            # Ghi log giải phóng thực tế
                            InventoryTransaction.objects.create(
                                product=item.product,
                                variation=item.variation,
                                transaction_type='RELEASE',
                                quantity=release_qty,
                                is_physical=False,
                                reference_id=f"CART_EXP_{cart.id} | Tự động giải phóng {release_qty}"[:100]
                            )
                            total_released += release_qty
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Lỗi khi xử lý item {item.id} trong giỏ {cart.id}: {e}"))
                
                # Sau khi giải phóng kho xong cho tất cả items, xóa giỏ hàng
                cart_id = cart.id
                cart.delete()
                self.stdout.write(self.style.SUCCESS(f"Đã giải phóng kho và xóa giỏ hàng ID: {cart_id}"))

        self.stdout.write(self.style.SUCCESS(f"Hoàn tất! Đã giải phóng {total_released} sản phẩm từ các giỏ hàng hết hạn."))
