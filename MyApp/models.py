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
	stock_quantity = models.PositiveIntegerField(default=0, verbose_name="Số lượng tồn kho")
	views_count = models.PositiveIntegerField(default=0, verbose_name="Lượt xem")
	created_at = models.DateTimeField(auto_now_add=True)

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
	stock_quantity = models.PositiveIntegerField(default=0, verbose_name="Số lượng tồn kho biến thể")

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
	
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
	bio = models.CharField(max_length=200, blank=True, default='Tea Lover')
	phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
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
	
	def save(self, *args, **kwargs):
		if not self.membership_number:
			import random
			self.membership_number = f'{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}'
		super().save(*args, **kwargs)


# Signal để tự động tạo UserProfile khi User được tạo
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)


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
		('processing', 'Đang đóng gói'),
		('shipping', 'Đang giao'),
		('delivered', 'Thành công'),
		('return_requested', 'Yêu cầu trả hàng'),
		('return_approved', 'Đã duyệt trả hàng'),
		('returned', 'Đã nhận hàng trả'),
		('refunded', 'Đã hoàn tiền'),
		('exchanged', 'Đã đổi hàng'),
		('cancelled', 'Đã hủy'),
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


class OrderStatusHistory(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
	status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
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


def get_insufficient_stock(order):
	insufficient_items = []
	for order_item in order.items.select_related('product', 'variation').all():
		if order_item.product is None:
			continue
		
		# Check variation stock if variation exists, else product stock
		stock = order_item.variation.stock_quantity if order_item.variation else order_item.product.stock_quantity
		title = f"{order_item.product.title} ({order_item.variation.title})" if order_item.variation else order_item.product.title
		
		if stock < order_item.quantity:
			insufficient_items.append({
				'product': title,
				'required': order_item.quantity,
				'available': stock
			})
	return insufficient_items


def check_and_deduct_stock(order):
	with transaction.atomic():
		items = order.items.select_related('product', 'variation').select_for_update()
		insufficient_items = []
		for order_item in items:
			if order_item.product is None:
				continue
			
			stock = order_item.variation.stock_quantity if order_item.variation else order_item.product.stock_quantity
			title = f"{order_item.product.title} ({order_item.variation.title})" if order_item.variation else order_item.product.title
			
			if stock < order_item.quantity:
				insufficient_items.append({
					'product': title,
					'required': order_item.quantity,
					'available': stock
				})
				
		if insufficient_items:
			return False, insufficient_items

		for order_item in items:
			if order_item.product is None:
				continue
				
			if order_item.variation:
				ProductVariation.objects.filter(pk=order_item.variation.pk).update(
					stock_quantity=F('stock_quantity') - order_item.quantity
				)
			else:
				Product.objects.filter(pk=order_item.product.pk).update(
					stock_quantity=F('stock_quantity') - order_item.quantity
				)

	return True, []


@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
	if instance.pk:
		try:
			previous = Payment.objects.get(pk=instance.pk)
			instance._previous_payment_status = previous.payment_status
			instance._previous_stock_deducted = previous.stock_deducted
		except Payment.DoesNotExist:
			instance._previous_payment_status = None
			instance._previous_stock_deducted = False
	else:
		instance._previous_payment_status = None
		instance._previous_stock_deducted = False


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
	previous_status = getattr(instance, '_previous_payment_status', None)
	previous_stock_deducted = getattr(instance, '_previous_stock_deducted', False)

	if instance.payment_status != 'completed':
		return
	if instance.stock_deducted:
		return
	if (not created) and previous_status == 'completed' and previous_stock_deducted:
		return

	ok, _ = check_and_deduct_stock(instance.order)
	if ok:
		Payment.objects.filter(pk=instance.pk).update(stock_deducted=True)
	else:
		Payment.objects.filter(pk=instance.pk).update(payment_status='failed')


@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance, **kwargs):
	if instance.pk:
		try:
			previous = Order.objects.get(pk=instance.pk)
			instance._previous_status = previous.status
		except Order.DoesNotExist:
			instance._previous_status = None
	else:
		instance._previous_status = None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
	previous_status = getattr(instance, '_previous_status', None)
	
	# Create status history
	if created or instance.status != previous_status:
		OrderStatusHistory.objects.create(
			order=instance,
			status=instance.status
		)
		
	# Check and deduct stock if status is processing
	if instance.status != 'processing':
		return
	if previous_status == 'processing':
		return

	try:
		payment = instance.payment
	except Payment.DoesNotExist:
		payment = None

	if payment and payment.stock_deducted:
		return

	ok, _ = check_and_deduct_stock(instance)
	if ok and payment:
		Payment.objects.filter(pk=payment.pk).update(
			stock_deducted=True,
			payment_date=payment.payment_date or timezone.now(),
		)


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
