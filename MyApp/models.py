from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


class Category(models.Model):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=120, unique=True)
	description = models.TextField(blank=True)
	image = models.ImageField(upload_to='categories/', blank=True, null=True)
	is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động/Hiển thị")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		verbose_name_plural = 'Categories'

	def __str__(self):
		return self.name


class InventoryManager(models.Manager):
	def with_available_stock(self):
		return self.get_queryset().annotate(
			available_stock_value=F('physical_stock') - F('reserved_stock')
		)

class Product(models.Model):
	category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True)
	excerpt = models.CharField(max_length=300, blank=True)
	image = models.ImageField(upload_to='products/', blank=True, null=True)
	description = models.TextField(blank=True)
	ingredients = models.TextField(blank=True, verbose_name="Thành phần / Thông số")
	brewing_guide = models.TextField(blank=True, verbose_name="Hướng dẫn pha chế")
	price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
	
	physical_stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng tồn vật lý")
	reserved_stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng tạm giữ")
	
	views_count = models.PositiveIntegerField(default=0, verbose_name="Lượt xem")
	created_at = models.DateTimeField(auto_now_add=True)

	objects = InventoryManager()

	@property
	def available_stock(self):
		return self.physical_stock - self.reserved_stock

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('product_detail', args=[self.slug])


class ProductImage(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='products/', verbose_name="Ảnh sản phẩm")
	alt_text = models.CharField(max_length=200, blank=True)
	order = models.PositiveIntegerField(default=0, verbose_name="Thứ tự")

	class Meta:
		ordering = ['order', 'id']
		verbose_name = "Ảnh sản phẩm"
		verbose_name_plural = "Ảnh sản phẩm"

	def __str__(self):
		return f"{self.product.title} - Image {self.order}"


class ProductVariation(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
	title = models.CharField(max_length=100)  # e.g., '50g', '100g'
	price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
	
	physical_stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng tồn vật lý biến thể")
	reserved_stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng tạm giữ biến thể")

	objects = InventoryManager()

	@property
	def available_stock(self):
		return self.physical_stock - self.reserved_stock

	class Meta:
		ordering = ['price']

	def __str__(self):
		return f'{self.product.title} - {self.title}'


class StoryboardItem(models.Model):
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True)
	image = models.ImageField(upload_to='storyboard/', blank=True, null=True)
	excerpt = models.CharField(max_length=300, blank=True)
	content = models.TextField(blank=True, null=True, verbose_name="Nội dung bài viết")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title


class RawItem(models.Model):
	title = models.CharField(max_length=200)
	image = models.ImageField(upload_to='raw/', blank=True, null=True)
	caption = models.CharField(max_length=300, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title


class CabinetItem(models.Model):
	title = models.CharField(max_length=200)
	image = models.ImageField(upload_to='cabinet/', blank=True, null=True)
	note = models.CharField(max_length=300, blank=True)
	link_url = models.CharField(max_length=500, blank=True, null=True, help_text="Đường link khi click vào item này (VD: /product/slug/)")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title


# ==================== USER PROFILE MODELS ====================

class UserProfile(models.Model):
	MEMBERSHIP_LEVELS = [
		('bronze', 'Bronze Leaf'),
		('silver', 'Silver Leaf'),
		('gold', 'Gold Leaf'),
		('platinum', 'Platinum Leaf'),
	]

	ROLE_CHOICES = [
		('customer', 'Khách hàng'),
		('admin', 'Administrator'),
		('accountant', 'Kế toán'),
		('warehouse', 'Nhân viên kho'),
	]
	
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer', verbose_name="Vai trò")
	avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
	bio = models.CharField(max_length=200, blank=True, default='Tea Lover')
	phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
	# Structured address fields
	street_address = models.CharField(max_length=255, blank=True)
	province = models.CharField(max_length=100, blank=True)
	province_code = models.CharField(max_length=10, blank=True)
	district = models.CharField(max_length=100, blank=True)
	district_code = models.CharField(max_length=10, blank=True)
	ward = models.CharField(max_length=100, blank=True)
	ward_code = models.CharField(max_length=10, blank=True)
	member_since = models.DateField(auto_now_add=True)
	membership_level = models.CharField(max_length=20, choices=MEMBERSHIP_LEVELS, default='bronze')
	membership_number = models.CharField(max_length=20, blank=True)
	points = models.PositiveIntegerField(default=0)
	
	def __str__(self):
		return f'{self.user.username} Profile'
	
	def get_full_name(self):
		if self.user.first_name or self.user.last_name:
			return f'{self.user.first_name} {self.user.last_name}'.strip()
		return self.user.username
	
	def get_full_address(self):
		parts = [self.street_address, self.ward, self.district, self.province]
		return ', '.join(p for p in parts if p)

	@property
	def role_name(self):
		"""Returns the display name of the role, prioritizing admin status for superusers."""
		if self.user.is_superuser:
			return "Administrator"
		return self.get_role_display()
	
	def save(self, *args, **kwargs):
		if not self.membership_number:
			import random
			self.membership_number = f'{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}'
		super().save(*args, **kwargs)


# Signal để tự động tạo UserProfile khi User được tạo
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		role = 'admin' if instance.is_superuser else 'customer'
		UserProfile.objects.create(user=instance, role=role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
	if hasattr(instance, 'profile'):
		instance.profile.save()


# ==================== COUPON MODEL ====================

class Coupon(models.Model):
	DISCOUNT_TYPES = [
		('percent', 'Phần trăm (%)'),
		('fixed', 'Số tiền cố định'),
		('freeship', 'Miễn phí vận chuyển')
	]
	
	code = models.CharField(max_length=50, unique=True, verbose_name="Mã giảm giá")
	discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percent')
	discount_value = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Giá trị giảm")
	min_purchase = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Đơn hàng tối thiểu")
	active = models.BooleanField(default=True, verbose_name="Kích hoạt")
	valid_from = models.DateTimeField(verbose_name="Bắt đầu từ")
	valid_to = models.DateTimeField(verbose_name="Kết thúc vào")
	usage_limit = models.PositiveIntegerField(default=100, verbose_name="Số lượt sử dụng tối đa")
	used = models.PositiveIntegerField(default=0, verbose_name="Số lượt đã sử dụng")

	class Meta:
		ordering = ['-valid_to']
		verbose_name = "Mã giảm giá"
		verbose_name_plural = "Mã giảm giá"

	def __str__(self):
		return self.code

	@property
	def is_valid(self):
		from django.utils import timezone
		now = timezone.now()
		return self.active and self.valid_from <= now <= self.valid_to and self.used < self.usage_limit


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'Chờ xác nhận'),
		('confirmed', 'Đã xác nhận (Đã giữ hàng)'),
		('processing', 'Đang đóng gói'),
		('shipping', 'Đang giao'),
		('delivered', 'Thành công (Đã trừ kho)'),
		('completed', 'Hoàn tất'),
		('cancelled', 'Đã hủy'),
		('return_requested', 'Yêu cầu trả hàng'),
		('return_approved', 'Đã duyệt trả hàng'),
		('returned', 'Đã nhận hàng trả'),
		('refunded', 'Đã hoàn tiền'),
		('exchanged', 'Đã đổi hàng'),
	]
	
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
	order_number = models.CharField(max_length=50, unique=True)
	total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
	discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	note = models.TextField(blank=True)
	pdf_generated = models.BooleanField(default=False)  # Track nếu PDF đã được tạo
	
	class Meta:
		ordering = ['-created_at']
	
	def __str__(self):
		return f'Order {self.order_number}'
	
	def save(self, *args, **kwargs):
		if not self.order_number:
			import uuid
			now = timezone.now()
			short_uuid = uuid.uuid4().hex[:6].upper()
			self.order_number = f'ORD-{now.strftime("%Y%m%d")}-{short_uuid}'
		super().save(*args, **kwargs)

	def log_transaction(self, item, transaction_type, quantity, is_physical=True, user=None):
		"""Giao thức ghi sổ cái nội bộ."""
		InventoryTransaction.objects.create(
			product=item.product,
			variation=item.variation,
			transaction_type=transaction_type,
			quantity=quantity,
			is_physical=is_physical,
			reference_id=self.order_number,
			user=user
		)

	def can_confirm(self):
		"""Kiểm tra xem có đủ hàng để xác nhận đơn không."""
		for item in self.items.all():
			target = item.variation if item.variation else item.product
			if target.available_stock < item.quantity:
				return False, f"Sản phẩm {target} không đủ tồn kho khả dụng."
		return True, ""

	def action_confirm(self, user=None):
		"""Xác nhận đơn hàng: Tạm giữ hàng (Reserved)."""
		if self.status in ['confirmed', 'processing', 'shipping', 'delivered', 'completed']:
			return True, "Đơn hàng đã được xác nhận trước đó."
		if self.status in ['cancelled', 'refunded', 'exchanged', 'return_requested', 'return_approved', 'returned']:
			return False, "Đơn hàng đã hủy/hoàn tất, không thể xác nhận lại."

		with transaction.atomic():
			# Lock items in sorted order to prevent deadlock
			items = self.items.select_related('product', 'variation').order_by('product__id', 'variation__id').select_for_update(of=('product', 'variation'))
			
			can_proceed, msg = self.can_confirm()
			if not can_proceed:
				return False, msg

			for item in items:
				target = item.variation if item.variation else item.product
				# Update reserved stock
				target.reserved_stock = F('reserved_stock') + item.quantity
				target.save()
				# Log reservation (Logical)
				self.log_transaction(item, 'RESERVE', item.quantity, is_physical=False, user=user)
			
			self.set_status('confirmed', user=user, note="Xác nhận đơn hàng và giữ kho.")
			self.ensure_invoice()
			return True, "Đơn hàng đã được xác nhận và giữ kho."

	def action_cancel(self, user=None):
		"""Hủy đơn hàng: Giải phóng hàng đã giữ (nếu có)."""
		if self.status == 'cancelled':
			return True, "Đơn hàng đã ở trạng thái hủy."
		if self.status in ['delivered', 'completed', 'return_requested', 'return_approved', 'returned', 'refunded', 'exchanged']:
			return False, "Đơn hàng đã hoàn tất hoặc đang xử lý đổi trả, không thể hủy."
		with transaction.atomic():
			items = self.items.select_related('product', 'variation').order_by('product__id', 'variation__id').select_for_update(of=('product', 'variation'))
			
			if self.status in ['confirmed', 'processing', 'shipping']:
				for item in items:
					target = item.variation if item.variation else item.product
					target.reserved_stock = F('reserved_stock') - item.quantity
					target.save()
					self.log_transaction(item, 'RELEASE', -item.quantity, is_physical=False, user=user)
			
			self.set_status('cancelled', user=user, note="Hủy đơn hàng.")
			try:
				invoice = self.invoice
			except Invoice.DoesNotExist:
				invoice = None
			if invoice and invoice.status != 'cancelled':
				invoice.status = 'cancelled'
				invoice.save(update_fields=['status'])
			return True, "Đơn hàng đã được hủy."

	def action_complete(self, user=None):
		"""Hoàn tất đơn hàng: Trừ kho vật lý và giải phóng kho tạm giữ."""
		if self.status in ['delivered', 'completed']:
			return True, "Đơn hàng đã hoàn tất."
		if self.status in ['cancelled', 'return_requested', 'return_approved', 'returned', 'refunded', 'exchanged']:
			return False, "Trạng thái đơn hàng không hợp lệ để hoàn tất."
		if self.status != 'shipping' and self.status != 'processing' and self.status != 'confirmed':
			return False, "Trạng thái đơn hàng không hợp lệ để hoàn tất."

		with transaction.atomic():
			items = self.items.select_related('product', 'variation').order_by('product__id', 'variation__id').select_for_update(of=('product', 'variation'))
			
			for item in items:
				target = item.variation if item.variation else item.product
				# Physical deduction
				target.physical_stock = F('physical_stock') - item.quantity
				# Release logical reservation
				target.reserved_stock = F('reserved_stock') - item.quantity
				target.save()
				# Log physical move (OUT)
				self.log_transaction(item, 'OUT', -item.quantity, is_physical=True, user=user)
			
			self.set_status('delivered', user=user, note="Giao hàng thành công.")
			return True, "Đơn hàng đã hoàn tất, kho vật lý đã cập nhật."

	def set_status(self, new_status, user=None, note=''):
		if new_status not in dict(Order.STATUS_CHOICES):
			return False, "Trạng thái không hợp lệ."
		self.status = new_status
		self.save(update_fields=['status', 'updated_at'])
		OrderStatusHistory.objects.create(order=self, status=new_status, user=user, note=note)
		return True, "Cập nhật trạng thái thành công."

	def ensure_invoice(self):
		"""Đảm bảo có hóa đơn cho đơn hàng, tạo nếu chưa có."""
		try:
			invoice = self.invoice
		except Invoice.DoesNotExist:
			profile = getattr(self.user, 'profile', None)
			full_name = ''
			if profile and hasattr(profile, 'get_full_name'):
				full_name = profile.get_full_name()
			if not full_name:
				full_name = self.user.get_full_name() or self.user.username

			if profile and hasattr(profile, 'get_full_address'):
				address = profile.get_full_address()
			else:
				address = getattr(profile, 'address', '') if profile else ''

			status = 'issued' if self.status in ['confirmed', 'processing', 'shipping', 'delivered', 'completed'] else 'draft'
			invoice = Invoice.objects.create(
				order=self,
				issue_date=timezone.now().date(),
				status=status,
				total_amount=self.total_amount,
				customer_name=full_name,
				customer_address=address,
			)
		else:
			status = 'issued' if self.status in ['confirmed', 'processing', 'shipping', 'delivered', 'completed'] else 'draft'
			updates = {}
			if invoice.status != status:
				updates['status'] = status
			if invoice.total_amount != self.total_amount:
				updates['total_amount'] = self.total_amount
			if status == 'issued' and not invoice.issue_date:
				updates['issue_date'] = timezone.now().date()
			if updates:
				for field, value in updates.items():
					setattr(invoice, field, value)
				invoice.save(update_fields=list(updates.keys()))

		if not invoice.items.exists():
			total_amount = 0
			for item in self.items.all():
				amount = item.get_subtotal()
				InvoiceItem.objects.create(
					invoice=invoice,
					product_title=item.product_title,
					quantity=item.quantity,
					unit_price=item.price,
					amount=amount,
				)
				total_amount += amount
			# Keep invoice total aligned with order (includes discount).
			invoice.total_amount = self.total_amount or total_amount
			invoice.save(update_fields=['total_amount'])
		return invoice


class OrderStatusHistory(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
	status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
	note = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.order.order_number} - {self.get_status_display()}'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
	variation = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, null=True, blank=True)
	product_title = models.CharField(max_length=200)  # Lưu tên sản phẩm phòng trường hợp sản phẩm bị xóa
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=0)
	
	def __str__(self):
		variant_info = f" ({self.variation.title})" if self.variation else ""
		return f'{self.product_title}{variant_info} x {self.quantity}'
	
	def get_subtotal(self):
		return self.price * self.quantity


class ReturnRequest(models.Model):
	RETURN_TYPES = [
		('refund', 'Hoàn tiền'),
		('exchange', 'Đổi hàng'),
		('cancel', 'Hủy đơn (Sau khi thanh toán)')
	]
	
	REQUEST_STATUS = [
		('pending', 'Chờ xử lý'),
		('approved', 'Đã chấp nhận'),
		('rejected', 'Từ chối'),
		('completed', 'Hoàn tất')
	]

	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
	request_type = models.CharField(max_length=20, choices=RETURN_TYPES, default='refund')
	status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='pending')
	reason = models.TextField(verbose_name="Lý do")
	admin_note = models.TextField(blank=True, verbose_name="Ghi chú của Admin")
	image = models.ImageField(upload_to='returns/', null=True, blank=True, verbose_name="Ảnh minh chứng")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = "Yêu cầu đổi trả"
		verbose_name_plural = "Yêu cầu đổi trả"

	def __str__(self):
		return f'Return {self.id} - Order {self.order.order_number}'


class ReturnItem(models.Model):
	return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='return_items')
	order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=1)
	reason_detail = models.CharField(max_length=255, blank=True)

	def __str__(self):
		return f'{self.order_item.product_title} x {self.quantity}'


class Wishlist(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
	added_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		ordering = ['-added_at']
		unique_together = ['user', 'product']
	
	def __str__(self):
		return f'{self.user.username} - {self.product.title}'


# ==================== CART MODELS ====================

class Cart(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
	session_key = models.CharField(max_length=40, null=True, blank=True)  # Cho guest users
	coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	def __str__(self):
		if self.user:
			return f'Cart của {self.user.username}'
		return f'Cart (session: {self.session_key[:8]}...)'
	
	def get_total_items(self):
		return sum(item.quantity for item in self.items.all())
	
	def get_subtotal(self):
		return sum(item.get_subtotal() for item in self.items.all())
	
	def get_discount_amount(self):
		if not self.coupon or not self.coupon.is_valid:
			return 0
		subtotal = self.get_subtotal()
		if subtotal < self.coupon.min_purchase:
			return 0
			
		if self.coupon.discount_type == 'percent':
			return (subtotal * self.coupon.discount_value) / 100
		elif self.coupon.discount_type == 'fixed':
			return self.coupon.discount_value
		return 0 # freeship handles shipping cost, not subtotal deduction directly typically, but we can return 0 here
	
	def get_total_price(self):
		subtotal = self.get_subtotal()
		discount = self.get_discount_amount()
		return max(0, subtotal - discount)


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, null=True, blank=True)
	quantity = models.PositiveIntegerField(default=1)
	added_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		unique_together = ['cart', 'product', 'variation']
	
	def __str__(self):
		variant_info = f" ({self.variation.title})" if self.variation else ""
		return f'{self.product.title}{variant_info} x {self.quantity}'
	
	def get_subtotal(self):
		price = self.variation.price if self.variation and self.variation.price else self.product.price
		if price:
			return price * self.quantity
		return 0


# Signal để tự động tạo Cart khi User được tạo
@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
	if created:
		Cart.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_cart(sender, instance, **kwargs):
	if hasattr(instance, 'cart'):
		instance.cart.save()

# ==================== INVENTORY LEDGER MODELS ====================

class InventoryTransaction(models.Model):
	TYPE_CHOICES = [
		('IN', 'Nhập kho'),
		('OUT', 'Xuất kho'),
		('ADJUST', 'Điều chỉnh (Kiểm kê)'),
		('RESERVE', 'Tạm giữ (Đặt hàng)'),
		('RELEASE', 'Giải phóng (Hủy đơn)'),
	]
	
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_transactions', null=True, blank=True)
	variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='inventory_transactions', null=True, blank=True)
	transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
	quantity = models.IntegerField(verbose_name="Số lượng thay đổi")
	is_physical = models.BooleanField(default=True, verbose_name="Biến động vật lý")
	reference_id = models.CharField(max_length=100, blank=True, verbose_name="Mã tham chiếu (Đơn hàng/Phiếu nhập)")
	timestamp = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

	class Meta:
		ordering = ['-timestamp']

	def __str__(self):
		target = f"{self.product.title}" if self.product else "N/A"
		if self.variation:
			target += f" ({self.variation.title})"
		return f"{self.get_transaction_type_display()} - {target} - {self.quantity}"

class InventoryReceipt(models.Model):
	STATUS_CHOICES = [('draft', 'Nháp'), ('completed', 'Hoàn tất')]
	
	receipt_number = models.CharField(max_length=50, unique=True)
	supplier = models.CharField(max_length=200, blank=True, verbose_name="Nhà cung cấp")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	note = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.receipt_number

	def save(self, *args, **kwargs):
		if not self.receipt_number:
			now = timezone.now()
			import random
			self.receipt_number = f'RCPT-{now.strftime("%Y%m%d")}-{random.randint(1000, 9999)}'
		super().save(*args, **kwargs)

class InventoryReceiptItem(models.Model):
	receipt = models.ForeignKey(InventoryReceipt, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, null=True, blank=True)
	quantity = models.PositiveIntegerField()
	unit_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)

	def __str__(self):
		return f"{self.product.title} - {self.quantity}"

@receiver(post_save, sender=User)
def save_user_cart(sender, instance, **kwargs):
	if hasattr(instance, 'cart'):
		instance.cart.save()

# ==================== PAYMENT MODELS ====================

class Payment(models.Model):
	PAYMENT_METHOD_CHOICES = [
		('qr_bank', 'QR Code - Ngân hàng'),
		('transfer', 'Chuyển khoản'),
		('cash', 'Thanh toán tại chỗ'),
		('wallet', 'Ví điện tử'),
		('other', 'Khác'),
	]
	
	PAYMENT_STATUS_CHOICES = [
		('pending', 'Chờ thanh toán'),
		('pending_verification', 'Chờ xác nhận'),
		('processing', 'Đang xử lý'),
		('completed', 'Hoàn thành'),
		('failed', 'Thất bại'),
		('cancelled', 'Đã hủy'),
	]
	
	order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='qr_bank')
	payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
	amount = models.DecimalField(max_digits=12, decimal_places=0)  # Số tiền thanh toán
	transaction_id = models.CharField(max_length=100, blank=True)  # ID giao dịch từ ngân hàng/gateway
	reference_code = models.CharField(max_length=100, blank=True)  # Mã tham chiếu
	payment_date = models.DateTimeField(null=True, blank=True)  # Ngày thanh toán thực tế
	notes = models.TextField(blank=True)  # Ghi chú từ gateway hoặc admin
	stock_deducted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		ordering = ['-created_at']
	
	def __str__(self):
		return f'Payment for {self.order.order_number} - {self.get_payment_status_display()}'
	
	def save(self, *args, **kwargs):
		if not self.reference_code:
			import random
			import string
			self.reference_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
		super().save(*args, **kwargs)


class PaymentQRCode(models.Model):
	payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='qr_code')
	qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)  # Lưu file hình QR
	qr_data = models.TextField()  # Dữ liệu được encode trong QR (JSON hoặc text)
	payment_method = models.CharField(max_length=20, default='bank')  # bank, vietqr, etc
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		ordering = ['-created_at']
	
	def __str__(self):
		return f'QR Code for {self.payment.order.order_number}'


class Invoice(models.Model):
	order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
	invoice_number = models.CharField(max_length=50, unique=True)
	pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
	issue_date = models.DateField(null=True, blank=True, verbose_name="Ngày phát hành")
	due_date = models.DateField(null=True, blank=True, verbose_name="Hạn thanh toán")
	status = models.CharField(max_length=20, choices=[('draft', 'Nháp'), ('issued', 'Đã phát hành'), ('paid', 'Đã thanh toán'), ('cancelled', 'Đã hủy')], default='draft', verbose_name="Trạng thái")
	total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Tổng tiền")
	tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Thuế (VAT)")
	customer_name = models.CharField(max_length=200, blank=True, verbose_name="Tên khách hàng")
	customer_address = models.TextField(blank=True, verbose_name="Địa chỉ")
	customer_tax_code = models.CharField(max_length=50, blank=True, verbose_name="Mã số thuế")
	generated_at = models.DateTimeField(auto_now_add=True)
	sent_at = models.DateTimeField(null=True, blank=True)
	
	class Meta:
		ordering = ['-generated_at']
		verbose_name = "Hóa đơn"
		verbose_name_plural = "Danh sách hóa đơn"
	
	def __str__(self):
		return f'Invoice {self.invoice_number}'
	
	def save(self, *args, **kwargs):
		if not self.invoice_number:
			import uuid
			now = timezone.now()
			short_uuid = uuid.uuid4().hex[:6].upper()
			self.invoice_number = f'INV-{now.strftime("%Y%m%d")}-{short_uuid}'
		super().save(*args, **kwargs)


class InvoiceItem(models.Model):
	invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
	product_title = models.CharField(max_length=200, verbose_name="Tên sản phẩm")
	quantity = models.PositiveIntegerField(default=1, verbose_name="Số lượng")
	unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Đơn giá")
	amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Thành tiền")
	description = models.CharField(max_length=255, blank=True, verbose_name="Mô tả")

	def __str__(self):
		return f"{self.product_title} - {self.amount}"


# ==================== REVIEW & COMMENT ====================

from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
	rating = models.PositiveIntegerField(
		validators=[MinValueValidator(1), MaxValueValidator(5)],
		verbose_name="Đánh giá"
	)
	title = models.CharField(max_length=100, verbose_name="Tiêu đề")
	content = models.TextField(verbose_name="Nội dung")
	helpful_votes = models.PositiveIntegerField(default=0, verbose_name="Lượt hữu ích")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('product', 'user')
		ordering = ['-created_at']
		verbose_name = "Đánh giá"
		verbose_name_plural = "Đánh giá"

	def __str__(self):
		return f"{self.user.username} - {self.product.title} ({self.rating}★)"


class ReviewImage(models.Model):
	review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='reviews/', verbose_name="Ảnh đánh giá")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"Image for Review {self.review.id}"


class Comment(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
	parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
	content = models.TextField(verbose_name="Bình luận")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['created_at']
		verbose_name = "Bình luận"
		verbose_name_plural = "Bình luận"

	def __str__(self):
		return f"{self.user.username}: {self.content[:50]}"


class CommentMedia(models.Model):
	FILE_TYPES = [
		('image', 'Hình ảnh'),
		('video', 'Video'),
	]
	comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='media')
	file = models.FileField(upload_to='comments/media/', verbose_name="Tệp đính kèm")
	file_type = models.CharField(max_length=10, choices=FILE_TYPES, default='image')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"Media ({self.file_type}) for Comment {self.comment.id}"


class CommentInteraction(models.Model):
	comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='interactions')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_interactions')
	is_like = models.BooleanField(default=True, verbose_name="Là Thích (True) hoặc Không thích (False)")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('comment', 'user')
		ordering = ['-created_at']

	def __str__(self):
		action = "Like" if self.is_like else "Dislike"
		return f"{self.user.username} {action}s Comment {self.comment.id}"


# ==================== AI CHATBOT ====================

class AIChatSession(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_sessions', null=True, blank=True)
	session_key = models.CharField(max_length=40, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		if self.user:
			return f"AI Chat Session for {self.user.username}"
		return f"AI Chat Session (Guest: {self.session_key})"

class AIChatMessage(models.Model):
	SENDER_CHOICES = [
		('user', 'User'),
		('ai', 'AI'),
	]
	session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
	sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"{self.sender} - {self.content[:50]}"

# ==================== MESSAGING ====================

class Conversation(models.Model):
	participants = models.ManyToManyField(User, related_name='conversations')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f"Conversation {self.id}"

	def get_other_user(self, current_user):
		return self.participants.exclude(id=current_user.id).first()

	def last_message(self):
		return self.messages.order_by('-created_at').first()

	def unread_count(self, user):
		return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
	conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
	content = models.TextField(verbose_name="Nội dung")
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"{self.sender.username}: {self.content[:50]}"


# ==================== NOTIFICATIONS ====================

class Notification(models.Model):
	NOTIFICATION_TYPES = [
		('review', 'Đánh giá mới'),
		('comment', 'Bình luận mới'),
		('reply', 'Phản hồi bình luận'),
		('message', 'Tin nhắn mới'),
		('order', 'Cập nhật đơn hàng'),
		('system', 'Hệ thống'),
		('promotion', 'Khuyến mãi'),
		('wishlist', 'Sản phẩm yêu thích'),
		('stock', 'Cập nhật tồn kho'),
	]

	CATEGORY_MAP = {
		'order': 'transactional',
		'stock': 'transactional',
		'review': 'interactive',
		'comment': 'interactive',
		'reply': 'interactive',
		'message': 'interactive',
		'system': 'system',
		'wishlist': 'promotional',
		'promotion': 'promotional',
	}

	CATEGORY_ICONS = {
		'transactional': {'icon': 'package', 'bg': 'bg-purple-100', 'text': 'text-purple-600'},
		'interactive': {'icon': 'message-circle', 'bg': 'bg-blue-100', 'text': 'text-blue-600'},
		'system': {'icon': 'shield', 'bg': 'bg-stone-100', 'text': 'text-stone-600'},
		'promotional': {'icon': 'tag', 'bg': 'bg-amber-100', 'text': 'text-amber-600'},
	}

	TYPE_ICONS = {
		'review': 'star',
		'comment': 'message-circle',
		'reply': 'corner-down-right',
		'message': 'mail',
		'order': 'package',
		'system': 'shield',
		'promotion': 'tag',
		'wishlist': 'heart',
		'stock': 'archive',
	}

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
	actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='triggered_notifications')
	notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
	title = models.CharField(max_length=200)
	message = models.TextField()
	link = models.CharField(max_length=500, blank=True)
	is_read = models.BooleanField(default=False)
	read_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = "Thông báo"
		verbose_name_plural = "Thông báo"
		indexes = [
			models.Index(fields=['user', 'is_read', '-created_at']),
		]

	@property
	def category(self):
		return self.CATEGORY_MAP.get(self.notification_type, 'system')

	@property
	def icon(self):
		return self.TYPE_ICONS.get(self.notification_type, 'bell')

	@property
	def category_style(self):
		return self.CATEGORY_ICONS.get(self.category, self.CATEGORY_ICONS['system'])

	def __str__(self):
		return f"[{self.notification_type}] {self.title}"


# ==================== SUPPORT CHAT ====================

class SupportBusinessHours(models.Model):
	"""Giờ làm việc hỗ trợ theo từng ngày trong tuần."""

	DAY_CHOICES = [
		(0, 'Thứ Hai'),
		(1, 'Thứ Ba'),
		(2, 'Thứ Tư'),
		(3, 'Thứ Năm'),
		(4, 'Thứ Sáu'),
		(5, 'Thứ Bảy'),
		(6, 'Chủ Nhật'),
	]

	day_of_week = models.IntegerField(choices=DAY_CHOICES, unique=True)
	open_time = models.TimeField(default='08:00')
	close_time = models.TimeField(default='22:00')
	is_open = models.BooleanField(default=True)

	class Meta:
		ordering = ['day_of_week']
		verbose_name = "Giờ hỗ trợ"
		verbose_name_plural = "Giờ hỗ trợ theo ngày"

	def __str__(self):
		return f"{self.get_day_of_week_display()} · {'Mở' if self.is_open else 'Đóng'} {self.open_time}-{self.close_time}"


class SupportQuickReply(models.Model):
	"""Template tin nhắn nhanh cho agent."""

	CATEGORY_CHOICES = [
		('greeting', 'Chào hỏi'),
		('inquiry', 'Hỏi thông tin'),
		('resolution', 'Giải quyết vấn đề'),
		('closing', 'Kết thúc'),
		('other', 'Khác'),
	]

	label = models.CharField(max_length=50, verbose_name="Nhãn nút")
	content = models.TextField(verbose_name="Nội dung template")
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
	order = models.PositiveIntegerField(default=0, verbose_name="Thứ tự")
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['category', 'order']
		verbose_name = "Quick Reply"
		verbose_name_plural = "Quick Replies"

	def __str__(self):
		return f"[{self.get_category_display()}] {self.label}"


class SupportTicket(models.Model):
	"""
	Một ticket = một phiên hội thoại hỗ trợ trực tiếp.
	Hỗ trợ cả khách đã login (user) và khách vãng lai (session_key + guest_info).
	"""

	CATEGORY_CHOICES = [
		('order', 'Đơn hàng'),
		('payment', 'Thanh toán'),
		('return', 'Đổi trả / Hoàn hàng'),
		('product', 'Thông tin sản phẩm'),
		('shipping', 'Vận chuyển'),
		('account', 'Tài khoản'),
		('other', 'Khác'),
	]

	STATUS_CHOICES = [
		('open', 'Khởi tạo'),
		('waiting', 'Đang chờ nhân viên'),
		('assigned', 'Đang hỗ trợ'),
		('resolved', 'Đã giải quyết'),
		('closed', 'Đã đóng'),
	]

	PRIORITY_CHOICES = [
		('low', 'Thấp'),
		('medium', 'Trung bình'),
		('high', 'Cao'),
		('urgent', 'Khẩn cấp'),
	]

	# Ownership
	user = models.ForeignKey(
		User, on_delete=models.CASCADE,
		related_name='support_tickets', null=True, blank=True,
		verbose_name="Khách hàng (đã login)"
	)
	session_key = models.CharField(
		max_length=40, null=True, blank=True, db_index=True,
		verbose_name="Session key (khách vãng lai)"
	)
	guest_name = models.CharField(max_length=100, blank=True, verbose_name="Tên khách vãng lai")
	guest_email = models.EmailField(blank=True, verbose_name="Email khách vãng lai")

	# Assignment
	assigned_to = models.ForeignKey(
		User, on_delete=models.SET_NULL, null=True, blank=True,
		related_name='assigned_support_tickets', verbose_name="Nhân viên phụ trách"
	)

	# Classification
	subject = models.CharField(max_length=200, default='Hỗ trợ chung', verbose_name="Tiêu đề")
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="Chủ đề")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name="Trạng thái")
	priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="Ưu tiên")
	source = models.CharField(max_length=20, default='widget', verbose_name="Kênh liên hệ")

	# SLA & Timing
	first_response_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm phản hồi đầu tiên")
	resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm giải quyết")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		verbose_name = "Ticket hỗ trợ"
		verbose_name_plural = "Ticket hỗ trợ"
		indexes = [
			models.Index(fields=['status', '-updated_at'], name='support_ticket_status_updated'),
			models.Index(fields=['user', 'status'], name='support_ticket_user_status'),
			models.Index(fields=['session_key', 'status'], name='support_ticket_session_status'),
			models.Index(fields=['assigned_to', 'status'], name='support_ticket_agent_status'),
		]

	def __str__(self):
		identity = self.user.username if self.user else self.guest_name or 'Anonymous'
		return f"Ticket #{self.id} · {identity} · {self.get_status_display()}"

	@property
	def display_name(self):
		"""Tên hiển thị của khách hàng."""
		if self.user:
			return self.user.get_full_name() or self.user.username
		return self.guest_name or 'Khách vãng lai'

	@property
	def display_email(self):
		"""Email hiển thị."""
		if self.user:
			return self.user.email
		return self.guest_email

	@property
	def response_time_minutes(self):
		"""Thời gian phản hồi đầu tiên tính bằng phút."""
		if self.first_response_at and self.created_at:
			delta = self.first_response_at - self.created_at
			return int(delta.total_seconds() / 60)
		return None

	@property
	def category_icon_map(self):
		icons = {
			'order': 'package', 'payment': 'credit-card',
			'return': 'rotate-ccw', 'product': 'leaf',
			'shipping': 'truck', 'account': 'user', 'other': 'help-circle',
		}
		return icons.get(self.category, 'help-circle')


class SupportMessage(models.Model):
	"""
	Một tin nhắn trong ticket hỗ trợ.
	sender_type: customer | agent | bot | system
	is_internal: True = ghi chú nội bộ, khách không thấy
	"""

	SENDER_TYPE_CHOICES = [
		('customer', 'Khách hàng'),
		('agent', 'Nhân viên'),
		('bot', 'Bot tự động'),
		('system', 'Hệ thống'),
	]

	ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
	sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)
	sender = models.ForeignKey(
		User, on_delete=models.SET_NULL, null=True, blank=True,
		related_name='sent_support_messages'
	)
	content = models.TextField(verbose_name="Nội dung")
	is_read = models.BooleanField(default=False)
	is_internal = models.BooleanField(default=False, verbose_name="Ghi chú nội bộ (agent only)")
	# Client-side ID for deduplication khi mạng yếu
	client_msg_id = models.CharField(max_length=64, blank=True, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']
		verbose_name = "Tin nhắn hỗ trợ"
		verbose_name_plural = "Tin nhắn hỗ trợ"

	def __str__(self):
		return f"[{self.sender_type}] Ticket #{self.ticket_id}: {self.content[:60]}"

	def to_dict(self):
		"""Serialize cho JSON API."""
		return {
			'id': self.id,
			'sender_type': self.sender_type,
			'sender_name': (
				self.sender.get_full_name() or self.sender.username
				if self.sender else
				('Bot TeaZen' if self.sender_type == 'bot' else 'Hệ thống')
			),
			'sender_avatar': (
				self.sender.profile.avatar.url
				if self.sender and hasattr(self.sender, 'profile') and self.sender.profile.avatar
				else None
			),
			'content': self.content,
			'is_read': self.is_read,
			'is_internal': self.is_internal,
			'created_at': self.created_at.isoformat(),
			'attachments': [
				{
					'id': a.id,
					'file_url': a.file.url,
					'file_name': a.file_name,
					'file_type': a.file_type,
					'file_size': a.file_size,
				}
				for a in self.attachments.all()
			],
		}


class SupportAttachment(models.Model):
	"""File đính kèm trong tin nhắn hỗ trợ."""

	FILE_TYPE_CHOICES = [
		('image', 'Hình ảnh'),
		('document', 'Tài liệu'),
	]

	message = models.ForeignKey(
		SupportMessage, on_delete=models.CASCADE, related_name='attachments'
	)
	file = models.FileField(upload_to='support_attachments/%Y/%m/', verbose_name="File")
	file_name = models.CharField(max_length=255, verbose_name="Tên file gốc")
	file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')
	file_size = models.PositiveIntegerField(default=0, verbose_name="Kích thước (bytes)")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']
		verbose_name = "File đính kèm"
		verbose_name_plural = "File đính kèm"

	def __str__(self):
		return f"{self.file_name} ({self.file_type})"


class SupportRating(models.Model):
	"""Đánh giá của khách sau khi ticket được giải quyết (1-5 sao)."""

	ticket = models.OneToOneField(
		SupportTicket, on_delete=models.CASCADE, related_name='rating'
	)
	rating = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(1), MaxValueValidator(5)],
		verbose_name="Đánh giá (1-5 sao)"
	)
	comment = models.TextField(blank=True, verbose_name="Nhận xét (tùy chọn)")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Đánh giá hỗ trợ"
		verbose_name_plural = "Đánh giá hỗ trợ"

	def __str__(self):
		return f"Ticket #{self.ticket_id} · {self.rating}★"
