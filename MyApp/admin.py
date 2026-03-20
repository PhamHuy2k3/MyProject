from django.contrib import admin
from django.utils import timezone
from .models import (Product, StoryboardItem, RawItem, CabinetItem, Category, 
	Order, OrderItem, UserProfile, Payment, PaymentQRCode, Invoice, InvoiceItem,
	Review, Comment, Conversation, Message, Notification, ProductVariation, OrderStatusHistory, Coupon,
	ReturnRequest, ReturnItem,
	SupportTicket, SupportMessage, SupportAttachment, SupportRating,
	SupportQuickReply, SupportBusinessHours)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug', 'created_at')
	prepopulated_fields = {'slug': ('name',)}
	search_fields = ('name',)


class ProductVariationInline(admin.TabularInline):
	model = ProductVariation
	extra = 1
	fields = ('title', 'price', 'physical_stock', 'reserved_stock')


from .models import ProductImage

class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 3
	fields = ('image', 'alt_text', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'category', 'price', 'physical_stock', 'reserved_stock', 'created_at')
	list_filter = ('category',)
	prepopulated_fields = {'slug': ('title',)}
	inlines = [ProductVariationInline, ProductImageInline]


@admin.register(StoryboardItem)
class StoryboardAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'created_at')
	prepopulated_fields = {'slug': ('title',)}


@admin.register(RawItem)
class RawItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_at')


@admin.register(CabinetItem)
class CabinetItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
	list_display = ('code', 'discount_type', 'discount_value', 'min_purchase', 'active', 'valid_from', 'valid_to', 'used', 'usage_limit')
	list_filter = ('active', 'discount_type', 'valid_from', 'valid_to')
	search_fields = ('code',)


# ==================== ORDER & PAYMENT ADMIN ====================

class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	fields = ('product_title', 'quantity', 'price')
	readonly_fields = ('product_title', 'quantity', 'price')


class OrderStatusHistoryInline(admin.TabularInline):
	model = OrderStatusHistory
	extra = 0
	readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_number', 'user', 'total_amount', 'status', 'created_at')
	list_filter = ('status', 'created_at', 'updated_at')
	search_fields = ('order_number', 'user__username', 'user__email')
	readonly_fields = ('order_number', 'created_at', 'updated_at')
	inlines = [OrderItemInline, OrderStatusHistoryInline]
	
	fieldsets = (
		('Thông tin đơn hàng', {
			'fields': ('order_number', 'user', 'total_amount', 'status')
		}),
		('Ghi chú', {
			'fields': ('note',)
		}),
		('Thời gian', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ('product_title', 'order', 'quantity', 'price')
	list_filter = ('order__created_at',)
	search_fields = ('product_title', 'order__order_number')
	readonly_fields = ('order', 'product_title')


class ReturnItemInline(admin.TabularInline):
	model = ReturnItem
	extra = 0


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
	list_display = ('id', 'order', 'request_type', 'status', 'created_at')
	list_filter = ('status', 'request_type', 'created_at')
	search_fields = ('order__order_number', 'reason')
	inlines = [ReturnItemInline]
	
	fieldsets = (
		('Thông tin yêu cầu', {
			'fields': ('order', 'request_type', 'status', 'reason', 'image')
		}),
		('Xử lý của Admin', {
			'fields': ('admin_note',)
		}),
	)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ('order', 'amount', 'payment_method', 'payment_status', 'created_at')
	list_filter = ('payment_method', 'payment_status', 'created_at')
	search_fields = ('order__order_number', 'transaction_id', 'reference_code')
	readonly_fields = ('order', 'created_at', 'updated_at', 'reference_code')
	
	fieldsets = (
		('Đơn hàng & Số tiền', {
			'fields': ('order', 'amount')
		}),
		('Thông tin thanh toán', {
			'fields': ('payment_method', 'payment_status', 'transaction_id', 'reference_code')
		}),
		('Ghi chú & Thời gian', {
			'fields': ('notes', 'payment_date', 'created_at', 'updated_at'),
		}),
	)
	
	actions = ['mark_completed', 'mark_pending', 'mark_failed']
	
	def mark_completed(self, request, queryset):
		updated = 0
		for payment in queryset:
			payment.payment_status = 'completed'
			if not payment.payment_date:
				payment.payment_date = timezone.now()
			payment.save()
			updated += 1
		self.message_user(request, f'{updated} thanh toán đã được đánh dấu là hoàn thành.')
	mark_completed.short_description = 'Đánh dấu là đã thanh toán'
	
	def mark_pending(self, request, queryset):
		updated = 0
		for payment in queryset:
			payment.payment_status = 'pending'
			payment.save()
			updated += 1
		self.message_user(request, f'{updated} thanh toán đã được đánh dấu là chờ.')
	mark_pending.short_description = 'Đánh dấu là chờ thanh toán'
	
	def mark_failed(self, request, queryset):
		updated = 0
		for payment in queryset:
			payment.payment_status = 'failed'
			payment.save()
			updated += 1
		self.message_user(request, f'{updated} thanh toán đã được đánh dấu là thất bại.')
	mark_failed.short_description = 'Đánh dấu là thất bại'


@admin.register(PaymentQRCode)
class PaymentQRCodeAdmin(admin.ModelAdmin):
	list_display = ('payment', 'payment_method', 'created_at')
	list_filter = ('payment_method', 'created_at')
	search_fields = ('payment__order__order_number',)
	readonly_fields = ('payment', 'qr_data', 'created_at', 'qr_image_preview')
	
	fieldsets = (
		('Thông tin QR', {
			'fields': ('payment', 'payment_method', 'created_at')
		}),
		('Hình ảnh QR', {
			'fields': ('qr_image', 'qr_image_preview')
		}),
		('Dữ liệu QR', {
			'fields': ('qr_data',),
			'classes': ('collapse',)
		}),
	)
	
	def qr_image_preview(self, obj):
		if obj.qr_image:
			from django.utils.html import format_html
			return format_html('<img src="{}" width="200" height="200" />', obj.qr_image.url)
		return 'Không có hình ảnh'
	qr_image_preview.short_description = 'Xem trước QR Code'


class InvoiceItemInline(admin.TabularInline):
	model = InvoiceItem
	extra = 0
	fields = ('product_title', 'quantity', 'unit_price', 'amount', 'description')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ('invoice_number', 'order', 'customer_name', 'total_amount', 'status', 'issue_date')
	list_filter = ('status', 'issue_date', 'generated_at')
	search_fields = ('invoice_number', 'order__order_number', 'customer_name')
	readonly_fields = ('order', 'invoice_number', 'generated_at')
	inlines = [InvoiceItemInline]
	
	fieldsets = (
		('Thông tin hóa đơn', {
			'fields': ('invoice_number', 'order', 'status', 'issue_date', 'due_date')
		}),
		('Khách hàng & Thanh toán', {
			'fields': ('customer_name', 'customer_address', 'customer_tax_code', 'total_amount', 'tax_amount')
		}),
		('File & Thời gian', {
			'fields': ('pdf_file', 'generated_at', 'sent_at'),
		}),
	)
	
	actions = ['download_pdf']
	
	def download_pdf(self, request, queryset):
		# Có thể thêm logic để download multiple PDFs
		self.message_user(request, 'Download thành công!')
	download_pdf.short_description = 'Tải PDF'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
	list_display = ('product', 'user', 'rating', 'title', 'created_at')
	list_filter = ('rating', 'created_at')
	search_fields = ('title', 'content', 'user__username', 'product__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
	list_display = ('product', 'user', 'content_short', 'parent', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('content', 'user__username')

	def content_short(self, obj):
		return obj.content[:60]
	content_short.short_description = 'Nội dung'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
	list_display = ('id', 'created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ('conversation', 'sender', 'content_short', 'is_read', 'created_at')
	list_filter = ('is_read', 'created_at')

	def content_short(self, obj):
		return obj.content[:60]
	content_short.short_description = 'Nội dung'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
	list_filter = ('notification_type', 'is_read', 'created_at')
	search_fields = ('title', 'message')


# ==================== SUPPORT CHAT ADMIN ====================

class SupportMessageInline(admin.TabularInline):
	model = SupportMessage
	extra = 0
	readonly_fields = ('sender_type', 'sender', 'content', 'is_read', 'is_internal', 'created_at')
	fields = ('sender_type', 'sender', 'content', 'is_internal', 'is_read', 'created_at')
	ordering = ('created_at',)
	can_delete = False


class SupportRatingInline(admin.StackedInline):
	model = SupportRating
	extra = 0
	readonly_fields = ('rating', 'comment', 'created_at')
	can_delete = False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
	list_display = (
		'id', 'display_name', 'display_email', 'category', 'status',
		'priority', 'assigned_to', 'response_time_display', 'created_at'
	)
	list_filter = ('status', 'category', 'priority', 'assigned_to', 'created_at')
	search_fields = ('user__username', 'user__email', 'guest_name', 'guest_email', 'subject')
	readonly_fields = ('created_at', 'updated_at', 'first_response_at', 'resolved_at')
	inlines = [SupportMessageInline, SupportRatingInline]
	list_per_page = 20

	fieldsets = (
		('Thông tin ticket', {
			'fields': ('subject', 'category', 'status', 'priority', 'source')
		}),
		('Khách hàng', {
			'fields': ('user', 'session_key', 'guest_name', 'guest_email')
		}),
		('Nhân viên', {
			'fields': ('assigned_to',)
		}),
		('Thời gian', {
			'fields': ('created_at', 'updated_at', 'first_response_at', 'resolved_at'),
			'classes': ('collapse',)
		}),
	)

	def response_time_display(self, obj):
		mins = obj.response_time_minutes
		if mins is None:
			return '—'
		if mins < 60:
			return f'{mins} phút'
		return f'{mins // 60}h {mins % 60}p'
	response_time_display.short_description = 'TG phản hồi'

	def display_name(self, obj):
		return obj.display_name
	display_name.short_description = 'Tên khách'

	def display_email(self, obj):
		return obj.display_email
	display_email.short_description = 'Email'


@admin.register(SupportQuickReply)
class SupportQuickReplyAdmin(admin.ModelAdmin):
	list_display = ('label', 'category', 'order', 'is_active')
	list_filter = ('category', 'is_active')
	ordering = ('category', 'order')
	list_editable = ('order', 'is_active')


@admin.register(SupportBusinessHours)
class SupportBusinessHoursAdmin(admin.ModelAdmin):
	list_display = ('day_of_week', 'open_time', 'close_time', 'is_open')
	list_editable = ('open_time', 'close_time', 'is_open')
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'role', 'membership_level', 'points', 'member_since')
	list_filter = ('role', 'membership_level', 'member_since')
	search_fields = ('user__username', 'user__email', 'membership_number')
	
	fieldsets = (
		('Người dùng', {
			'fields': ('user', 'role', 'avatar', 'bio')
		}),
		('Liên hệ', {
			'fields': ('phone', 'address', 'street_address', 'ward', 'district', 'province')
		}),
		('Thành viên', {
			'fields': ('membership_level', 'membership_number', 'points')
		}),
	)

from .audit_models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'event_type', 'actor_role', 'actor_id', 'resource_type', 'resource_id', 'status', 'severity_level_html')
    list_filter = ('event_type', 'severity_level', 'status', 'actor_role', 'resource_type', 'timestamp')
    search_fields = ('event_type', 'actor_id', 'ip_address', 'resource_id', 'reason', 'log_id')
    readonly_fields = ('log_id', 'timestamp', 'event_type', 'severity_level', 'actor_id', 'actor_role', 
                       'ip_address', 'user_agent', 'resource_type', 'resource_id', 'status', 'reason', 
                       'previous_hash', 'current_hash', 'diff_view')
    
    # Do not allow adding or changing (Append-only)
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
        
    list_per_page = 20
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('log_id', 'timestamp', 'event_type', 'severity_level', 'status', 'reason')
        }),
        ('Chủ thể thực hiện (Actor)', {
            'fields': ('actor_id', 'actor_role', 'ip_address', 'user_agent')
        }),
        ('Tài nguyên bị tác động (Resource)', {
            'fields': ('resource_type', 'resource_id')
        }),
        ('Dữ liệu thay đổi (Payload Delta)', {
            'fields': ('diff_view',)
        }),
        ('Tính toàn vẹn (Integrity)', {
            'fields': ('previous_hash', 'current_hash'),
            'classes': ('collapse',)
        }),
    )

    def severity_level_html(self, obj):
        from django.utils.html import format_html
        colors = {
            'INFO': 'blue',
            'WARNING': 'orange',
            'ERROR': 'red',
            'CRITICAL': 'darkred'
        }
        color = colors.get(obj.severity_level, 'gray')
        # Using obj.get_severity_level_display() for translated/friendly name.
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_severity_level_display())
    severity_level_html.short_description = 'Mức độ'

    def diff_view(self, obj):
        from django.utils.html import format_html
        import json
        
        try:
            # Parse dicts if they are serialized json strings
            before = obj.before_state
            if isinstance(before, str) and before:
                try: before = json.loads(before)
                except: pass
            
            after = obj.after_state
            if isinstance(after, str) and after:
                try: after = json.loads(after)
                except: pass

            before_str = json.dumps(before, indent=2, ensure_ascii=False) if before else 'None'
            after_str = json.dumps(after, indent=2, ensure_ascii=False) if after else 'None'
            
            html = f"""
            <div style="display: flex; gap: 20px;">
                <div style="flex: 1; border: 1px solid #ffcccc; background-color: #fff0f0; padding: 10px; border-radius: 4px;">
                    <h4 style="margin-top: 0; color: #cc0000;">Dữ liệu cũ (Before)</h4>
                    <pre style="white-space: pre-wrap; font-size: 12px; margin: 0;">{before_str}</pre>
                </div>
                <div style="flex: 1; border: 1px solid #ccffcc; background-color: #f0fff0; padding: 10px; border-radius: 4px;">
                    <h4 style="margin-top: 0; color: #008800;">Dữ liệu mới (After)</h4>
                    <pre style="white-space: pre-wrap; font-size: 12px; margin: 0;">{after_str}</pre>
                </div>
            </div>
            """
            return format_html(html)
        except Exception as e:
            return str(e)
            
    diff_view.short_description = 'So sánh Dữ liệu'

