from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Product(models.Model):
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True)
	excerpt = models.CharField(max_length=300, blank=True)
	image = models.ImageField(upload_to='products/', blank=True, null=True)
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('product_detail', args=[self.slug])


class StoryboardItem(models.Model):
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True)
	image = models.ImageField(upload_to='storyboard/', blank=True, null=True)
	excerpt = models.CharField(max_length=300, blank=True)
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


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'Đang xử lý'),
		('confirmed', 'Đã xác nhận'),
		('shipping', 'Đang giao'),
		('delivered', 'Đã giao'),
		('completed', 'Hoàn thành'),
		('cancelled', 'Đã hủy'),
	]
	
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
	order_number = models.CharField(max_length=50, unique=True)
	total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	note = models.TextField(blank=True)
	
	class Meta:
		ordering = ['-created_at']
	
	def __str__(self):
		return f'Order {self.order_number}'
	
	def save(self, *args, **kwargs):
		if not self.order_number:
			import datetime
			import random
			year = datetime.datetime.now().year
			self.order_number = f'ORD-{year}-{random.randint(100,999)}'
		super().save(*args, **kwargs)


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
	product_title = models.CharField(max_length=200)  # Lưu tên sản phẩm phòng trường hợp sản phẩm bị xóa
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=0)
	
	def __str__(self):
		return f'{self.product_title} x {self.quantity}'
	
	def get_subtotal(self):
		return self.price * self.quantity


class Wishlist(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
	added_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		ordering = ['-added_at']
		unique_together = ['user', 'product']
	
	def __str__(self):
		return f'{self.user.username} - {self.product.title}'
