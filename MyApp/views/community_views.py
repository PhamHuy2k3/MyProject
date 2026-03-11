from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Count, Sum, Avg, F, Q, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Prefetch
from decimal import Decimal
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse

from MyApp.models import *
from MyApp.forms import *
import requests
import json
from .utils import *

# ==================== REVIEW & COMMENT VIEWS ====================

@login_required(login_url='login')
def review_create(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        rating = request.POST.get('rating', 5)
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        review, created = Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating, 'title': title, 'content': content}
        )
        
        if created:
            messages.success(request, 'Đã gửi đánh giá!')
            for admin_user in User.objects.filter(is_staff=True):
                create_notification(
                    admin_user, 'review',
                    f'Đánh giá mới cho {product.title}',
                    f'{request.user.username} rated {rating}★',
                    link=f'/product/{slug}/'
                )
    return redirect('product_detail', slug=slug)


@login_required(login_url='login')
def comment_create(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')
        
        if not content and not request.FILES.getlist('media'):
            return JsonResponse({'success': False, 'error': 'Nội dung bình luận không được để trống.'})

        parent = None
        if parent_id:
            parent = Comment.objects.filter(id=parent_id, product=product).first()
            if parent and parent.parent:
                # Level 2 limit: reply to a reply -> attach to top level parent and tag user
                content = f"@{parent.user.username} {content}"
                parent = parent.parent
        
        comment = Comment.objects.create(product=product, user=request.user, parent=parent, content=content)
        
        # Handle media
        files = request.FILES.getlist('media')
        for file in files:
            size_mb = file.size / (1024 * 1024)
            file_type = 'image'
            if file.content_type.startswith('video'):
                file_type = 'video'
                if size_mb > 20: continue
            else:
                if size_mb > 5: continue
            CommentMedia.objects.create(comment=comment, file=file, file_type=file_type)
        
        if parent and parent.user != request.user:
            create_notification(
                parent.user, 'reply',
                f'{request.user.username} đã trả lời bình luận',
                f'Trả lời bình luận tại sản phẩm {product.title}',
                link=f'/product/{slug}/#comment-{comment.id}'
            )
            
        html = render_to_string('shop/partials/comment_item_single.html', {
            'comment': comment,
            'user': request.user,
            'product': product,
            'is_reply': bool(comment.parent_id),
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html,
            'parent_id': comment.parent_id,
            'total_count': product.comments.count(),
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def comments_ajax_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    sort = request.GET.get('sort', 'newest')
    
    replies_qs = Comment.objects.select_related('user', 'user__profile').prefetch_related('media', 'interactions').order_by('created_at')

    comments_qs = Comment.objects.filter(product=product, parent=None).annotate(
        like_count=Count('interactions', filter=Q(interactions__is_like=True)),
        dislike_count=Count('interactions', filter=Q(interactions__is_like=False)),
        reply_count=Count('replies')
    ).select_related('user', 'user__profile').prefetch_related('media', 'interactions', Prefetch('replies', queryset=replies_qs))
    
    if sort == 'newest':
        comments_qs = comments_qs.order_by('-created_at')
    elif sort == 'oldest':
        comments_qs = comments_qs.order_by('created_at')
    elif sort == 'popular':
        comments_qs = comments_qs.annotate(
            popularity=F('like_count') + F('reply_count') * 2
        ).order_by('-popularity', '-created_at')
        
    from django.core.paginator import Paginator
    page_number = request.GET.get('page', 1)
    paginator = Paginator(comments_qs, 4)
    page_obj = paginator.get_page(page_number)
    
    html = render_to_string('shop/partials/comment_list.html', {
        'comments': page_obj,
        'user': request.user if request.user.is_authenticated else None,
        'product': product,
    }, request=request)
    
    return JsonResponse({
        'html': html,
        'has_next': page_obj.has_next(),
        'top_level_count': paginator.count,
        'total_count': product.comments.count(),
    })


@login_required(login_url='login')
def comment_interact_api(request, comment_id):
    if request.method == 'POST':
        comment = get_object_or_404(Comment, id=comment_id)
        action = request.POST.get('action')
        is_like = action == 'like'
        
        interaction, created = CommentInteraction.objects.get_or_create(
            comment=comment,
            user=request.user,
            defaults={'is_like': is_like}
        )
        
        if not created:
            if interaction.is_like == is_like:
                interaction.delete()
                state = 'none'
            else:
                interaction.is_like = is_like
                interaction.save()
                state = action
        else:
            state = action
            
        likes_count = comment.interactions.filter(is_like=True).count()
        dislikes_count = comment.interactions.filter(is_like=False).count()
        
        return JsonResponse({
            'success': True,
            'state': state,
            'likes': likes_count,
            'dislikes': dislikes_count
        })
    return JsonResponse({'success': False})


@login_required(login_url='login')
def comment_delete_api(request, comment_id):
    if request.method == 'POST':
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user == request.user or request.user.is_staff:
            product = comment.product
            parent_id = comment.parent_id
            comment.delete()
            return JsonResponse({
                'success': True,
                'parent_id': parent_id,
                'total_count': product.comments.count(),
            })
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    return JsonResponse({'success': False})


# ==================== MESSAGING VIEWS ====================

@login_required(login_url='login')
def message_inbox(request):
    conversations = request.user.conversations.all()
    conv_data = []
    total_unread = 0
    for conv in conversations:
        other = conv.get_other_user(request.user)
        last_msg = conv.last_message()
        unread = conv.unread_count(request.user)
        total_unread += unread
        conv_data.append({
            'conv': conv,
            'other': other,
            'last_msg': last_msg,
            'unread': unread,
        })
    return render(request, 'messages/inbox.html', {'conv_data': conv_data, 'total_unread': total_unread})


@login_required(login_url='login')
def message_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_user = conversation.get_other_user(request.user)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(conversation=conversation, sender=request.user, content=content)
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            if other_user:
                create_notification(other_user, 'message', f'Tin nhắn mới từ {request.user.username}', content[:50], link=f'/messages/{conversation.id}/')
            return redirect('message_detail', conversation_id=conversation.id)
    
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(request, 'messages/detail.html', {
        'conversation': conversation,
        'other_user': other_user,
        'messages_list': conversation.messages.all(),
    })


@login_required(login_url='login')
def message_new(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect('message_inbox')
    existing = Conversation.objects.filter(participants=request.user).filter(participants=other_user)
    if existing.exists():
        return redirect('message_detail', conversation_id=existing.first().id)
    conv = Conversation.objects.create()
    conv.participants.add(request.user, other_user)
    return redirect('message_detail', conversation_id=conv.id)


@login_required(login_url='login')
def message_search_users(request):
    from django.http import JsonResponse
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'users': []})
    users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:10]
    return JsonResponse({'users': [{'id': u.id, 'username': u.username} for u in users]})


# ==================== NOTIFICATION VIEWS ====================

@login_required(login_url='login')
def notification_list(request):
    notifications = request.user.notifications.all()[:50]
    unread_count = request.user.notifications.filter(is_read=False).count()
    # Tự động đánh dấu đã đọc khi người dùng xem trang thông báo
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifications, 'unread_count': unread_count})


@login_required(login_url='login')
def notification_mark_read(request):
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            request.user.notifications.filter(id=notification_id).update(is_read=True)
        else:
            request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notification_list')


def notification_count_api(request):
    from django.http import JsonResponse
    if request.user.is_authenticated:
        notif_count = request.user.notifications.filter(is_read=False).count()
        msg_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return JsonResponse({'notification_count': notif_count, 'message_count': msg_count})
    return JsonResponse({'notification_count': 0, 'message_count': 0})


