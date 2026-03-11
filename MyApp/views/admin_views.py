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
from decimal import Decimal
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from MyApp.models import *
from MyApp.forms import *
import requests
import json
from .utils import *

# ==================== ADMIN DASHBOARD ====================

@admin_required
def admin_dashboard(request):
    context = {
        'products_count': Product.objects.count(),
        'storyboard_count': StoryboardItem.objects.count(),
        'raw_count': RawItem.objects.count(),
        'cabinet_count': CabinetItem.objects.count(),
    }
    return render(request, 'admin/dashboard.html', context)


@admin_required
def admin_statistics(request):
    days = int(request.GET.get('days', 30))
    sort_by = request.GET.get('sort', 'revenue')
    category_id = request.GET.get('category')
    stock_filter = request.GET.get('stock') # low, out, slow
    
    # Time threshold
    threshold_date = timezone.now() - timezone.timedelta(days=days)
    valid_status = ['confirmed', 'shipping', 'delivered', 'completed']
    
    # Filters for conditional aggregation
    product_stats_filter = Q(order_items__order__status__in=valid_status, order_items__order__created_at__gte=threshold_date)
    category_stats_filter = Q(products__order_items__order__status__in=valid_status, products__order_items__order__created_at__gte=threshold_date)
    
    # Overall KPIs
    total_stats = Order.objects.filter(status__in=valid_status, created_at__gte=threshold_date).aggregate(
        revenue=Coalesce(Sum('total_amount'), Decimal('0.00')),
        order_count=Count('id')
    )
    
    total_views = Product.objects.aggregate(total=Sum('views_count'))['total'] or 0
    total_p_count = Product.objects.count()
    low_stock_p = Product.objects.filter(stock_quantity__lte=5).count()
    
    total_revenue = total_stats['revenue']
    total_orders = total_stats['order_count']
    aov = total_revenue / total_orders if total_orders > 0 else 0
    conversion_rate = (total_orders / total_views * 100) if total_views > 0 else 0

    # Base Queryset
    product_qs = Product.objects.all()
    if category_id:
        product_qs = product_qs.filter(category_id=category_id)
    if stock_filter == 'low':
        product_qs = product_qs.filter(stock_quantity__lte=5, stock_quantity__gt=0)
    elif stock_filter == 'out':
        product_qs = product_qs.filter(stock_quantity=0)
    elif stock_filter == 'slow':
        # Slow movers: Stock > 10 and no sales in threshold
        product_qs = product_qs.filter(stock_quantity__gt=10).annotate(
            recent_sales=Coalesce(Sum('order_items__quantity', filter=product_stats_filter), 0)
        ).filter(recent_sales=0)

    # Product performance stats with advanced BI fields
    products = product_qs.annotate(
        total_views_num=F('views_count'),
        total_wishlists=Count('wishlisted_by', distinct=True),
        total_sold=Coalesce(Sum('order_items__quantity', filter=product_stats_filter, output_field=IntegerField()), 0),
        total_revenue=Coalesce(Sum(F('order_items__quantity') * F('order_items__price'), filter=product_stats_filter, output_field=DecimalField()), Decimal('0.00')),
    ).order_by(f'-total_{sort_by}' if sort_by != 'created_at' else '-created_at')

    # Post-process for BI insights (Sales velocity, Recommendation scores)
    for p in products:
        p.sales_velocity = Decimal(p.total_sold) / Decimal(days)
        # Restock Score: critical if selling fast but low stock
        if p.stock_quantity > 0:
            p.restock_score = Decimal(p.total_sold) / Decimal(p.stock_quantity)
        else:
            p.restock_score = Decimal(p.total_sold) * 2 # Out of stock but has sales = high priority
            
        # Opportunity products: High views, low sales
        p.is_opportunity = p.total_views_num > 50 and (p.total_sold < 2)
        p.is_best_seller = p.total_sold > 10
        p.is_slow_mover = p.stock_quantity > 20 and p.total_sold == 0

    # Critical Alerts
    alerts = {
        'critical_stock': products.filter(stock_quantity=0)[:5],
        'low_stock': products.filter(stock_quantity__lte=5, stock_quantity__gt=0)[:5],
        'slow_movers': [p for p in products if p.is_slow_mover][:5],
        'opportunities': [p for p in products if p.is_opportunity][:5]
    }

    # Category performance stats
    categories = Category.objects.annotate(
        total_sold=Coalesce(Sum('products__order_items__quantity', filter=category_stats_filter), 0),
        total_revenue=Coalesce(Sum(F('products__order_items__quantity') * F('products__order_items__price'), filter=category_stats_filter, output_field=DecimalField()), Decimal('0.00')),
        product_count=Count('products', distinct=True)
    ).order_by('-total_revenue')

    context = {
        'products': products,
        'categories': categories,
        'all_categories': Category.objects.filter(is_active=True),
        'current_sort': sort_by,
        'current_days': days,
        'current_category': category_id,
        'current_stock': stock_filter,
        'alerts': alerts,
        'kpis': {
            'revenue': total_revenue,
            'orders': total_orders,
            'aov': aov,
            'conversion': conversion_rate,
            'inventory_health': ((total_p_count - low_stock_p) / total_p_count * 100) if total_p_count > 0 else 100
        }
    }
    return render(request, 'admin/statistics.html', context)


@admin_required
def admin_inventory(request):
    products = Product.objects.all().order_by('stock_quantity')
    orders = Order.objects.all().select_related('user').order_by('-created_at')
    return render(request, 'admin/inventory.html', {'products': products, 'orders': orders})


@admin_required
def admin_order_detail_manage(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            order.save()
            messages.success(request, 'Cập nhật trạng thái thành công.')
            # Gửi thông báo cho khách hàng khi trạng thái đơn hàng thay đổi
            if new_status != old_status:
                status_display = dict(Order.STATUS_CHOICES).get(new_status, new_status)
                create_notification(
                    user=order.user,
                    notification_type='order',
                    title=f'Đơn hàng {order.order_number} đã cập nhật',
                    message_text=f'Trạng thái đơn hàng của bạn đã chuyển sang: {status_display}',
                    link=f'/order/{order.order_number}/',
                )
    return render(request, 'admin/order_detail_manage.html', {'order': order, 'status_choices': Order.STATUS_CHOICES})


# ==================== PRODUCT CRUD ====================

@admin_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'admin/product_list.html', {'products': products})


@admin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Thêm Sản Phẩm'})


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form, 'product': product})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'admin/confirm_delete.html', {'object': product})


# ==================== STORYBOARD CRUD ====================

@admin_required
def storyboard_list(request):
    items = StoryboardItem.objects.all()
    return render(request, 'admin/storyboard_list.html', {'items': items})


@admin_required
def storyboard_create(request):
    if request.method == 'POST':
        form = StoryboardItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('storyboard_list')
    else:
        form = StoryboardItemForm()
    return render(request, 'admin/storyboard_form.html', {'form': form})


@admin_required
def storyboard_edit(request, pk):
    item = get_object_or_404(StoryboardItem, pk=pk)
    if request.method == 'POST':
        form = StoryboardItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('storyboard_list')
    else:
        form = StoryboardItemForm(instance=item)
    return render(request, 'admin/storyboard_form.html', {'form': form, 'item': item})


@admin_required
def storyboard_delete(request, pk):
    item = get_object_or_404(StoryboardItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('storyboard_list')
    return render(request, 'admin/confirm_delete.html', {'object': item})


# ==================== RAW ITEM CRUD ====================

@admin_required
def raw_list(request):
    items = RawItem.objects.all()
    return render(request, 'admin/raw_list.html', {'items': items})


@admin_required
def raw_create(request):
    if request.method == 'POST':
        form = RawItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('raw_list')
    else:
        form = RawItemForm()
    return render(request, 'admin/raw_form.html', {'form': form})


@admin_required
def raw_edit(request, pk):
    item = get_object_or_404(RawItem, pk=pk)
    if request.method == 'POST':
        form = RawItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('raw_list')
    else:
        form = RawItemForm(instance=item)
    return render(request, 'admin/raw_form.html', {'form': form, 'item': item})


@admin_required
def raw_delete(request, pk):
    item = get_object_or_404(RawItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('raw_list')
    return render(request, 'admin/confirm_delete.html', {'object': item})


# ==================== CABINET ITEM CRUD ====================

@admin_required
def cabinet_list(request):
    items = CabinetItem.objects.all()
    return render(request, 'admin/cabinet_list.html', {'items': items})


@admin_required
def cabinet_create(request):
    if request.method == 'POST':
        form = CabinetItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('cabinet_list')
    else:
        form = CabinetItemForm()
    return render(request, 'admin/cabinet_form.html', {'form': form})


@admin_required
def cabinet_edit(request, pk):
    item = get_object_or_404(CabinetItem, pk=pk)
    if request.method == 'POST':
        form = CabinetItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('cabinet_list')
    else:
        form = CabinetItemForm(instance=item)
    return render(request, 'admin/cabinet_form.html', {'form': form, 'item': item})


@admin_required
def cabinet_delete(request, pk):
    item = get_object_or_404(CabinetItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('cabinet_list')
    return render(request, 'admin/confirm_delete.html', {'object': item})


# ==================== CATEGORY CRUD ====================

@admin_required
def category_list(request):
    items = Category.objects.all()
    return render(request, 'admin/category_list.html', {'items': items})


@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'admin/category_form.html', {'form': form})


@admin_required
def category_edit(request, pk):
    item = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=item)
    return render(request, 'admin/category_form.html', {'form': form, 'item': item})


@admin_required
def category_delete(request, pk):
    item = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('category_list')
    return render(request, 'admin/confirm_delete.html', {'object': item})

@admin_required
def category_toggle_active(request, pk):
    item = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        item.is_active = not item.is_active
        item.save()
    return redirect('category_list')


@admin_required
def admin_return_list(request):
    """
    List of all return and exchange requests.
    """
    status_filter = request.GET.get('status', 'pending')
    returns = ReturnRequest.objects.all().order_by('-created_at')
    
    if status_filter != 'all':
        returns = returns.filter(status=status_filter)
        
    return render(request, 'admin/returns/return_list.html', {
        'returns': returns,
        'current_status': status_filter
    })

@admin_required
def admin_return_detail(request, return_id):
    """
    Manage a specific return request.
    """
    return_req = get_object_or_404(ReturnRequest, id=return_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '')
        
        return_req.admin_note = admin_note
        
        if action == 'approve':
            return_req.status = 'approved'
            order = return_req.order
            # Update order status to reflect progress
            order.status = 'return_approved'
            order.save()
            
            create_notification(
                user=order.user,
                notification_type='order',
                title='Yêu cầu hoàn trả đã được chấp nhận',
                message_text=f'Yêu cầu hỗ trợ cho đơn hàng {order.order_number} đã được duyệt. Vui lòng gửi hàng về cho chúng tôi.',
                link=f'/order/{order.order_number}/'
            )
            messages.success(request, 'Đã chấp nhận yêu cầu.')
            
        elif action == 'reject':
            return_req.status = 'rejected'
            order = return_req.order
            # If rejected, revert order status back to delivered (or let admin decide)
            order.status = 'delivered'
            order.save()
            
            create_notification(
                user=order.user,
                notification_type='order',
                title='Yêu cầu hoàn trả bị từ chối',
                message_text=f'Yêu cầu hỗ trợ cho đơn hàng {order.order_number} không được chấp nhận. Lý do: {admin_note}',
                link=f'/order/{order.order_number}/'
            )
            messages.warning(request, 'Đã từ chối yêu cầu.')
            
        elif action == 'complete':
            return_req.status = 'completed'
            order = return_req.order
            
            if return_req.request_type == 'refund':
                order.status = 'refunded'
                # Optional: Restore stock if items were returned safely
                for r_item in return_req.return_items.all():
                    if r_item.order_item.variation:
                        r_item.order_item.variation.stock_quantity += r_item.quantity
                        r_item.order_item.variation.save()
                    elif r_item.order_item.product:
                        r_item.order_item.product.stock_quantity += r_item.quantity
                        r_item.order_item.product.save()
                        
            elif return_req.request_type == 'exchange':
                order.status = 'exchanged'
                # Note: Exchange might require more complex logic for multiple items, 
                # but we'll simplify by completing it here.
            
            order.save()
            
            create_notification(
                user=order.user,
                notification_type='order',
                title='Hoàn tất xử lý đổi trả',
                message_text=f'Yêu cầu hỗ trợ cho đơn hàng {order.order_number} đã được hoàn tất xử lý.',
                link=f'/order/{order.order_number}/'
            )
            messages.success(request, 'Đã hoàn tất xử lý yêu cầu.')
            
        return_req.save()
        return redirect('admin_return_detail', return_id=return_id)

    return render(request, 'admin/returns/return_detail.html', {'return_req': return_req})
