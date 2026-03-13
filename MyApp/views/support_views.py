from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from django.db.models import Q
import json, os, time

from MyApp.models import (
    Order, OrderItem, ReturnRequest, ReturnItem, ProductVariation, Product,
    SupportTicket, SupportMessage, SupportAttachment, SupportRating,
    SupportQuickReply, SupportBusinessHours, Notification, User,
)
from .utils import management_required, is_management_staff

# ==================== SUPPORT CHAT WIDGET PAGE ====================

def support_chat_page(request):
    """
    Trang hiển thị widget support chat - mở widget bằng JavaScript.
    """
    from django.shortcuts import render
    return render(request, 'core/support_chat_page.html')

def _is_business_hours():
    now = timezone.localtime()
    day = now.weekday()  # 0=Mon...6=Sun
    try:
        bh = SupportBusinessHours.objects.get(day_of_week=day)
        if not bh.is_open:
            return False
        return bh.open_time <= now.time() <= bh.close_time
    except SupportBusinessHours.DoesNotExist:
        return True


def _count_online_agents():
    from django.contrib.sessions.models import Session
    from django.utils import timezone as tz
    import json as _json

    cutoff = tz.now() - timezone.timedelta(minutes=30)
    active_sessions = Session.objects.filter(expire_date__gte=tz.now())
    online_staff_ids = set()
    for session in active_sessions:
        data = session.get_decoded()
        uid = data.get('_auth_user_id')
        if uid:
            online_staff_ids.add(int(uid))

    if not online_staff_ids:
        return 0
    return User.objects.filter(id__in=online_staff_ids, is_staff=True).count()


def _get_or_create_open_ticket(request):
    if request.user.is_authenticated:
        return SupportTicket.objects.filter(
            user=request.user, status__in=['open', 'waiting', 'assigned']
        ).order_by('-created_at').first()
    else:
        sk = request.session.session_key
        if not sk:
            return None
        return SupportTicket.objects.filter(
            session_key=sk, status__in=['open', 'waiting', 'assigned']
        ).order_by('-created_at').first()


def _verify_ticket_ownership(request, ticket):
    if request.user.is_authenticated:
        return ticket.user == request.user
    return ticket.session_key == request.session.session_key


def _notify_staff_new_ticket(ticket, first_message_content):
    category_display = dict(SupportTicket.CATEGORY_CHOICES).get(ticket.category, ticket.category)
    for staff in User.objects.filter(is_staff=True):
        Notification.objects.create(
            user=staff,
            notification_type='system',
            title=f'🎧 Yêu cầu hỗ trợ mới #{ticket.id} · {category_display}',
            message=f'{ticket.display_name}: {first_message_content[:80]}',
            link=f'/manage/support/{ticket.id}/'
        )


def _notify_staff_return_request(return_req):
    """
    Notify all staff members when a new return/exchange request is submitted.
    """
    from django.urls import reverse
    order = return_req.order
    request_type_display = "Đổi trả" if return_req.request_type == 'refund' else "Đổi hàng"
    
    # Notify all staff (is_staff=True)
    staff_users = User.objects.filter(is_staff=True)
    for staff in staff_users:
        Notification.objects.create(
            user=staff,
            actor=order.user,
            notification_type='order',
            title=f'📦 Yêu cầu {request_type_display} mới: {order.order_number}',
            message=f'Khách hàng {order.user.username} đã gửi yêu cầu cho đơn hàng {order.order_number}.',
            link=f'/manage/returns/' # Direct to the returns management page
        )


def _get_avg_wait_minutes():
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=7)
    # Tính thủ công để tránh lỗi aggregate datetime trên SQLite
    recent = SupportTicket.objects.filter(
        first_response_at__isnull=False,
        created_at__gte=cutoff
    ).values_list('created_at', 'first_response_at')[:50]

    if not recent:
        return 5  # Default 5 phút

    total_secs = sum((fr - cr).total_seconds() for cr, fr in recent)
    avg_secs = total_secs / len(recent)
    return max(1, int(avg_secs / 60))


# ==================== CUSTOMER APIs ====================

@csrf_exempt
def api_support_status(request):
    """
    GET /api/support/status/
    Trả về trạng thái hỗ trợ: có agent online, giờ làm việc, ticket đang mở.
    Widget gọi khi bubble được click.
    """
    if not request.session.session_key:
        request.session.create()

    open_ticket = _get_or_create_open_ticket(request)
    agents_online = _count_online_agents()
    is_bh = _is_business_hours()

    return JsonResponse({
        'is_business_hours': is_bh,
        'agents_online': agents_online,
        'estimated_wait_minutes': _get_avg_wait_minutes() if agents_online > 0 and is_bh else None,
        'has_open_ticket': open_ticket is not None,
        'ticket_id': open_ticket.id if open_ticket else None,
        'ticket_status': open_ticket.status if open_ticket else None,
    })


@csrf_exempt
def api_support_create_ticket(request):
    """
    POST /api/support/tickets/
    Tạo ticket mới từ widget. Hỗ trợ cả login và vãng lai.
    Body: {name?, email?, category, message}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Validate
    message_content = body.get('message', '').strip()
    category = body.get('category', 'other')
    if not message_content or len(message_content) < 5:
        return JsonResponse({'error': 'Tin nhắn quá ngắn (tối thiểu 5 ký tự)'}, status=400)
    if len(message_content) > 2000:
        return JsonResponse({'error': 'Tin nhắn quá dài (tối đa 2000 ký tự)'}, status=400)
    if category not in dict(SupportTicket.CATEGORY_CHOICES):
        category = 'other'

    # Ensure session
    if not request.session.session_key:
        request.session.create()

    # Check existing open ticket
    existing = _get_or_create_open_ticket(request)
    if existing:
        return JsonResponse({'error': 'Bạn đang có một yêu cầu hỗ trợ đang mở.', 'ticket_id': existing.id}, status=409)

    # Auto-priority by category
    priority_map = {'order': 'high', 'payment': 'high', 'return': 'medium', 'product': 'low', 'shipping': 'medium', 'account': 'medium', 'other': 'low'}
    priority = priority_map.get(category, 'medium')

    category_display = dict(SupportTicket.CATEGORY_CHOICES).get(category, 'Hỗ trợ chung')

    # Build ticket fields
    ticket_data = {
        'category': category,
        'subject': category_display,
        'priority': priority,
        'status': 'open',
        'source': 'widget',
    }

    if request.user.is_authenticated:
        ticket_data['user'] = request.user
    else:
        name = body.get('name', '').strip()[:100]
        email = body.get('email', '').strip()[:254]
        if not name:
            return JsonResponse({'error': 'Vui lòng cung cấp tên của bạn'}, status=400)
        if not email:
            return JsonResponse({'error': 'Vui lòng cung cấp email của bạn'}, status=400)
        ticket_data['session_key'] = request.session.session_key
        ticket_data['guest_name'] = name
        ticket_data['guest_email'] = email

    ticket = SupportTicket.objects.create(**ticket_data)

    # Customer's first message
    client_msg_id = body.get('client_msg_id', '')
    customer_msg = SupportMessage.objects.create(
        ticket=ticket,
        sender_type='customer',
        sender=request.user if request.user.is_authenticated else None,
        content=message_content,
        client_msg_id=client_msg_id,
    )

    # Auto-reply from bot (3 second delay is handled frontend-side via UX)
    auto_reply_content = (
        f"Cảm ơn bạn đã liên hệ TeaZen! 🍃\n\n"
        f"Yêu cầu hỗ trợ của bạn đã được ghi nhận (Ticket #{ticket.id}). "
        f"Nhân viên của chúng tôi sẽ phản hồi trong vài phút. "
        f"Trong khi chờ, bạn có thể mô tả thêm chi tiết vấn đề nhé."
    )
    bot_msg = SupportMessage.objects.create(
        ticket=ticket,
        sender_type='bot',
        content=auto_reply_content,
        is_read=True,
    )

    # Update status → waiting
    ticket.status = 'waiting'
    ticket.save(update_fields=['status', 'updated_at'])

    # Notify staff
    _notify_staff_new_ticket(ticket, message_content)

    return JsonResponse({
        'ticket_id': ticket.id,
        'status': ticket.status,
        'messages': [customer_msg.to_dict(), bot_msg.to_dict()],
    }, status=201)


@csrf_exempt
def api_support_messages_get(request, ticket_id):
    """
    GET /api/support/tickets/{id}/messages/?after=ISO_TIMESTAMP
    Lấy tin nhắn (full history hoặc sau timestamp nhất định).
    Không trả về internal notes.
    """
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Ticket không tồn tại'}, status=404)

    if not _verify_ticket_ownership(request, ticket):
        return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)

    after_param = request.GET.get('after')
    qs = ticket.messages.filter(is_internal=False)

    if after_param:
        dt = parse_datetime(after_param)
        if dt:
            qs = qs.filter(created_at__gt=dt)

    qs = qs.order_by('created_at').prefetch_related('attachments')

    # Mark agent/bot messages as read
    qs.filter(sender_type__in=['agent', 'bot', 'system'], is_read=False).update(is_read=True)

    # Agent info
    agent_info = None
    if ticket.assigned_to:
        ag = ticket.assigned_to
        agent_info = {
            'name': ag.get_full_name() or ag.username,
            'avatar': ag.profile.avatar.url if hasattr(ag, 'profile') and ag.profile.avatar else None,
        }

    # Check if agent is "typing" — simple approach: check agent activity in last 5s
    agent_typing = False  # Will be updated by agent typing API

    return JsonResponse({
        'messages': [m.to_dict() for m in qs],
        'ticket_status': ticket.status,
        'agent_info': agent_info,
        'agent_typing': agent_typing,
    })


@csrf_exempt
def api_support_messages_send(request, ticket_id):
    """
    POST /api/support/tickets/{id}/messages/
    Khách gửi tin nhắn vào ticket.
    Body: {content, client_msg_id?}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Ticket không tồn tại'}, status=404)

    if not _verify_ticket_ownership(request, ticket):
        return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)

    if ticket.status in ['resolved', 'closed']:
        return JsonResponse({'error': 'Cuộc trò chuyện đã kết thúc'}, status=400)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    content = body.get('content', '').strip()
    client_msg_id = body.get('client_msg_id', '')

    if not content or len(content) < 1:
        return JsonResponse({'error': 'Nội dung không được trống'}, status=400)
    if len(content) > 2000:
        return JsonResponse({'error': 'Tin nhắn quá dài (tối đa 2000 ký tự)'}, status=400)

    # Idempotency: nếu client_msg_id đã tồn tại → return existing message
    if client_msg_id:
        existing = SupportMessage.objects.filter(client_msg_id=client_msg_id, ticket=ticket).first()
        if existing:
            return JsonResponse({'message': existing.to_dict()})

    msg = SupportMessage.objects.create(
        ticket=ticket,
        sender_type='customer',
        sender=request.user if request.user.is_authenticated else None,
        content=content,
        client_msg_id=client_msg_id or '',
    )

    # Notify assigned agent
    if ticket.assigned_to:
        Notification.objects.create(
            user=ticket.assigned_to,
            notification_type='message',
            title=f'Tin nhắn mới · Ticket #{ticket.id}',
            message=content[:100],
            link=f'/manage/support/{ticket.id}/',
        )

    # Update ticket updated_at
    SupportTicket.objects.filter(id=ticket_id).update(updated_at=timezone.now())

    return JsonResponse({'message': msg.to_dict()})


@csrf_exempt
def api_support_close(request, ticket_id):
    """
    POST /api/support/tickets/{id}/close/
    Khách tự đóng ticket.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Ticket không tồn tại'}, status=404)

    if not _verify_ticket_ownership(request, ticket):
        return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)

    if ticket.status == 'closed':
        return JsonResponse({'status': 'closed'})

    # Create system message
    SupportMessage.objects.create(
        ticket=ticket,
        sender_type='system',
        content='Khách hàng đã đóng cuộc trò chuyện.',
    )

    ticket.status = 'closed'
    if ticket.status not in ['resolved']:
        ticket.resolved_at = timezone.now()
    ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])

    return JsonResponse({'status': 'closed'})


@csrf_exempt
def api_support_rate(request, ticket_id):
    """
    POST /api/support/tickets/{id}/rate/
    Khách đánh giá phiên hỗ trợ.
    Body: {rating: 1-5, comment?: str}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Ticket không tồn tại'}, status=404)

    if not _verify_ticket_ownership(request, ticket):
        return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)

    if ticket.status not in ['resolved', 'closed']:
        return JsonResponse({'error': 'Chỉ đánh giá được sau khi ticket được giải quyết'}, status=400)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    rating = body.get('rating')
    comment = body.get('comment', '').strip()[:1000]

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Đánh giá phải là số từ 1 đến 5'}, status=400)

    SupportRating.objects.update_or_create(
        ticket=ticket,
        defaults={'rating': rating, 'comment': comment}
    )

    # Close ticket after rating
    ticket.status = 'closed'
    ticket.save(update_fields=['status', 'updated_at'])

    return JsonResponse({'success': True, 'rating': rating})


@csrf_exempt
def api_support_upload(request, ticket_id):
    """
    POST /api/support/tickets/{id}/upload/
    Upload file đính kèm vào tin nhắn gần nhất của khách.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return JsonResponse({'error': 'Ticket không tồn tại'}, status=404)

    if not _verify_ticket_ownership(request, ticket):
        return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)

    if ticket.status in ['resolved', 'closed']:
        return JsonResponse({'error': 'Cuộc trò chuyện đã kết thúc'}, status=400)

    uploaded_file = request.FILES.get('file')
    message_id = request.POST.get('message_id')

    if not uploaded_file:
        return JsonResponse({'error': 'Không có file được gửi'}, status=400)

    # Validate file type
    name = uploaded_file.name.lower()
    allowed_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf'}
    ext = os.path.splitext(name)[1]
    if ext not in allowed_exts:
        return JsonResponse({'error': f'Định dạng file không hỗ trợ. Chỉ chấp nhận: {", ".join(allowed_exts)}'}, status=400)

    # Validate size
    max_size = 5 * 1024 * 1024 if ext != '.pdf' else 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        limit_mb = max_size // (1024 * 1024)
        return JsonResponse({'error': f'File quá lớn (tối đa {limit_mb}MB)'}, status=400)

    file_type = 'document' if ext == '.pdf' else 'image'

    # If message_id provided, attach to that message
    if message_id:
        try:
            msg = SupportMessage.objects.get(id=message_id, ticket=ticket)
        except SupportMessage.DoesNotExist:
            msg = None
    else:
        msg = None

    if not msg:
        msg = SupportMessage.objects.create(
            ticket=ticket, sender_type='customer',
            sender=request.user if request.user.is_authenticated else None,
            content='',
        )

    attachment = SupportAttachment.objects.create(
        message=msg,
        file=uploaded_file,
        file_name=uploaded_file.name,
        file_type=file_type,
        file_size=uploaded_file.size,
    )

    return JsonResponse({
        'message_id': msg.id,
        'attachment': {
            'id': attachment.id,
            'file_url': attachment.file.url,
            'file_name': attachment.file_name,
            'file_type': attachment.file_type,
            'file_size': attachment.file_size,
        }
    })


# ==================== AGENT / ADMIN APIs ====================

def _is_staff(user):
    return user.is_authenticated and user.is_staff


@management_required
def admin_support_dashboard(request):
    """
    GET /manage/support/
    Admin: Trang dashboard hỗ trợ khách hàng.
    """
    status_filter = request.GET.get('status', 'active')
    category_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '').strip()

    if status_filter == 'active':
        tickets = SupportTicket.objects.filter(status__in=['open', 'waiting', 'assigned'])
    elif status_filter == 'waiting':
        tickets = SupportTicket.objects.filter(status='waiting')
    elif status_filter == 'assigned':
        tickets = SupportTicket.objects.filter(status='assigned')
    elif status_filter == 'resolved':
        tickets = SupportTicket.objects.filter(status__in=['resolved', 'closed'])
    else:
        tickets = SupportTicket.objects.all()

    if category_filter:
        tickets = tickets.filter(category=category_filter)

    if search_q:
        tickets = tickets.filter(
            Q(user__username__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(guest_name__icontains=search_q) |
            Q(guest_email__icontains=search_q) |
            Q(subject__icontains=search_q) |
            Q(id__icontains=search_q)
        )

    tickets = tickets.select_related('user', 'assigned_to').order_by('-updated_at')[:50]

    # Selected ticket
    selected_id = request.GET.get('ticket')
    selected_ticket = None
    ticket_messages = []
    quick_replies = []
    customer_orders = []

    if selected_id:
        try:
            selected_ticket = SupportTicket.objects.select_related(
                'user', 'assigned_to', 'user__profile'
            ).get(id=selected_id)
            ticket_messages = selected_ticket.messages.prefetch_related('attachments').order_by('created_at')
            quick_replies = SupportQuickReply.objects.filter(is_active=True).order_by('category', 'order')
            if selected_ticket.user:
                customer_orders = selected_ticket.user.orders.order_by('-created_at')[:5]
            
            # Mark all customer messages as read
            selected_ticket.messages.filter(sender_type='customer', is_read=False).update(is_read=True)
        except SupportTicket.DoesNotExist:
            pass

    # Counts for sidebar badges
    counts = {
        'open': SupportTicket.objects.filter(status='open').count(),
        'waiting': SupportTicket.objects.filter(status='waiting').count(),
        'assigned': SupportTicket.objects.filter(status='assigned').count(),
        'resolved': SupportTicket.objects.filter(status__in=['resolved', 'closed']).count(),
    }

    context = {
        'tickets': tickets,
        'selected_ticket': selected_ticket,
        'ticket_messages': ticket_messages,
        'quick_replies': quick_replies,
        'customer_orders': customer_orders,
        'counts': counts,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_q': search_q,
        'categories': SupportTicket.CATEGORY_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    }
    return render(request, 'admin/support/dashboard.html', context)


@management_required
def admin_support_ticket_detail(request, ticket_id):
    """
    GET /manage/support/<ticket_id>/
    Admin: Xem chi tiết ticket hỗ trợ.
    """
    # Get the ticket
    selected_ticket = get_object_or_404(
        SupportTicket.objects.select_related('user', 'assigned_to', 'user__profile'),
        id=ticket_id
    )
    
    # Get ticket messages
    ticket_messages = selected_ticket.messages.prefetch_related('attachments').order_by('created_at')
    
    # Get quick replies
    quick_replies = SupportQuickReply.objects.filter(is_active=True).order_by('category', 'order')
    
    # Get customer orders if user exists
    customer_orders = []
    if selected_ticket.user:
        customer_orders = selected_ticket.user.orders.order_by('-created_at')[:5]
    
    # Mark all customer messages as read
    selected_ticket.messages.filter(sender_type='customer', is_read=False).update(is_read=True)
    
    # Get all tickets for the sidebar list
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'active':
        tickets = SupportTicket.objects.filter(status__in=['open', 'waiting', 'assigned'])
    elif status_filter == 'resolved':
        tickets = SupportTicket.objects.filter(status__in=['resolved', 'closed'])
    else:
        tickets = SupportTicket.objects.all()
    tickets = tickets.select_related('user', 'assigned_to').order_by('-updated_at')[:50]
    
    # Counts for sidebar badges
    counts = {
        'open': SupportTicket.objects.filter(status='open').count(),
        'waiting': SupportTicket.objects.filter(status='waiting').count(),
        'assigned': SupportTicket.objects.filter(status='assigned').count(),
        'resolved': SupportTicket.objects.filter(status='resolved').count(),
    }
    
    context = {
        'tickets': tickets,
        'selected_ticket': selected_ticket,
        'ticket_messages': ticket_messages,
        'quick_replies': quick_replies,
        'customer_orders': customer_orders,
        'counts': counts,
        'status_filter': status_filter,
        'categories': SupportTicket.CATEGORY_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    }
    return render(request, 'admin/support/dashboard.html', context)


@management_required
def api_agent_reply(request, ticket_id):
    """
    POST /manage/support/tickets/{id}/reply/
    Agent gửi tin nhắn vào ticket.
    Body: {content, is_internal: bool}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    content = body.get('content', '').strip()
    is_internal = bool(body.get('is_internal', False))

    if not content:
        return JsonResponse({'error': 'Nội dung không được trống'}, status=400)

    # Assign to this agent if not yet assigned
    if ticket.status in ['open', 'waiting'] and not ticket.assigned_to:
        ticket.assigned_to = request.user
        ticket.status = 'assigned'
        if not ticket.first_response_at:
            ticket.first_response_at = timezone.now()
        ticket.save(update_fields=['assigned_to', 'status', 'first_response_at', 'updated_at'])

        # System message: agent joined
        if not is_internal:
            SupportMessage.objects.create(
                ticket=ticket,
                sender_type='system',
                content=f'✓ {request.user.get_full_name() or request.user.username} đã tham gia hỗ trợ bạn.',
            )

    msg = SupportMessage.objects.create(
        ticket=ticket,
        sender_type='agent',
        sender=request.user,
        content=content,
        is_internal=is_internal,
    )

    # first_response tracking
    if not ticket.first_response_at and not is_internal:
        SupportTicket.objects.filter(id=ticket_id).update(first_response_at=timezone.now())

    # Notify customer (only if logged in user)
    if not is_internal and ticket.user:
        Notification.objects.create(
            user=ticket.user,
            notification_type='message',
            title=f'Nhân viên hỗ trợ đã phản hồi · Ticket #{ticket.id}',
            message=content[:100],
            link='/support-chat/',
        )

    return JsonResponse({'message': msg.to_dict()})


@management_required
def api_agent_assign(request, ticket_id):
    """POST /manage/support/tickets/{id}/assign/ — Nhận ticket."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    try:
        body = json.loads(request.body)
        agent_id = body.get('agent_id')
    except (json.JSONDecodeError, ValueError):
        agent_id = None

    if agent_id:
        agent = get_object_or_404(User, id=agent_id, is_staff=True)
    else:
        agent = request.user

    old_agent = ticket.assigned_to
    ticket.assigned_to = agent
    ticket.status = 'assigned'
    if not ticket.first_response_at:
        ticket.first_response_at = timezone.now()
    ticket.save(update_fields=['assigned_to', 'status', 'first_response_at', 'updated_at'])

    # System message
    if old_agent and old_agent != agent:
        msg_content = f'Ticket đã được chuyển từ {old_agent.get_full_name() or old_agent.username} sang {agent.get_full_name() or agent.username}.'
    else:
        msg_content = f'✓ {agent.get_full_name() or agent.username} đã nhận hỗ trợ bạn.'

    SupportMessage.objects.create(ticket=ticket, sender_type='system', content=msg_content)

    return JsonResponse({'success': True, 'agent': agent.get_full_name() or agent.username})


@management_required
def api_agent_resolve(request, ticket_id):
    """POST /manage/support/tickets/{id}/resolve/ — Đánh dấu đã giải quyết."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    ticket = get_object_or_404(SupportTicket, id=ticket_id)

    try:
        body = json.loads(request.body)
        note = body.get('note', '').strip()
    except (json.JSONDecodeError, ValueError):
        note = ''

    ticket.status = 'resolved'
    ticket.resolved_at = timezone.now()
    ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])

    # System message
    resolution_msg = 'Cuộc trò chuyện đã kết thúc. Cảm ơn bạn đã liên hệ TeaZen! 🍵'
    if note:
        resolution_msg += f'\n\n📝 Ghi chú: {note}'

    SupportMessage.objects.create(
        ticket=ticket, sender_type='system', content=resolution_msg
    )

    return JsonResponse({'success': True, 'status': 'resolved'})


@csrf_exempt
@login_required(login_url='login')
@user_passes_test(_is_staff)
def api_agent_set_priority(request, ticket_id):
    """POST /manage/support/tickets/{id}/priority/ — Đổi priority."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    try:
        body = json.loads(request.body)
        priority = body.get('priority', 'medium')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if priority not in dict(SupportTicket.PRIORITY_CHOICES):
        return JsonResponse({'error': 'Priority không hợp lệ'}, status=400)

    ticket.priority = priority
    ticket.save(update_fields=['priority', 'updated_at'])
    return JsonResponse({'success': True, 'priority': priority})

@login_required(login_url='login')
def request_return(request, order_number):
    """
    User requests a return or exchange for a delivered order.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Validation: Only delivered orders can be returned
    if order.status != 'delivered':
        messages.error(request, 'Bạn chỉ có thể yêu cầu trả hàng cho các đơn hàng đã giao thành công.')
        return redirect('order_detail', order_number=order_number)
    
    # Check if a return request already exists
    if order.return_requests.exclude(status='rejected').exists():
        messages.warning(request, 'Đơn hàng này đang có yêu cầu đổi trả đang được xử lý.')
        return redirect('order_detail', order_number=order_number)

    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        reason = request.POST.get('reason')
        image = request.FILES.get('image')
        
        # Create the ReturnRequest
        return_req = ReturnRequest.objects.create(
            order=order,
            request_type=request_type,
            reason=reason,
            image=image,
            status='pending'
        )
        
        # Process items
        item_ids = request.POST.getlist('items')
        for item_id in item_ids:
            quantity = int(request.POST.get(f'quantity_{item_id}', 0))
            if quantity > 0:
                order_item = get_object_or_404(OrderItem, id=item_id, order=order)
                # Check quantity validity
                if quantity <= order_item.quantity:
                    ReturnItem.objects.create(
                        return_request=return_req,
                        order_item=order_item,
                        quantity=quantity
                    )
        
        # If no items were selected, delete the request and error out
        if not return_req.return_items.exists():
            return_req.delete()
            messages.error(request, 'Vui lòng chọn ít nhất một sản phẩm để đổi trả.')
            return redirect('request_return', order_number=order_number)
        
        # Update order status
        order.set_status('return_requested', user=request.user, note="Khách gửi yêu cầu đổi/trả.")
        
        # Notify all staff members
        try:
            _notify_staff_return_request(return_req)
        except Exception:
            pass # Don't block the user if notification fails
        
        messages.success(request, 'Yêu cầu đổi trả của bạn đã được gửi. Chúng tôi sẽ phản hồi sớm nhất.')
        return redirect('order_detail', order_number=order_number)

    return render(request, 'support/request_return.html', {'order': order})

@login_required(login_url='login')
def cancel_order(request, order_number):
    """
    Cancel an order if it's still pending.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Use the new OMS action to cancel (this handles reserved stock release and logging)
    success, message = order.action_cancel(user=request.user)
    
    if not success:
        messages.error(request, f"Không thể hủy đơn hàng: {message}")
        return redirect('order_detail', order_number=order_number)
    
    messages.success(request, f'Đơn hàng {order_number} đã được hủy thành công.')
    return redirect('order_list')
