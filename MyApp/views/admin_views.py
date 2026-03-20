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
from django.core.paginator import Paginator
from decimal import Decimal
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from MyApp.models import *
from MyApp.forms import *
import requests
import json
from .utils import *

# ==================== ADMIN DASHBOARD ====================

@management_required
def admin_dashboard(request):
    context = {
        'products_count': Product.objects.count(),
        'storyboard_count': StoryboardItem.objects.count(),
        'raw_count': RawItem.objects.count(),
        'cabinet_count': CabinetItem.objects.count(),
    }
    return render(request, 'admin/dashboard.html', context)


@accountant_required
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
    low_stock_p = Product.objects.filter(physical_stock__lte=5).count()
    
    total_revenue = total_stats['revenue']
    total_orders = total_stats['order_count']
    aov = total_revenue / total_orders if total_orders > 0 else 0
    conversion_rate = (total_orders / total_views * 100) if total_views > 0 else 0

    # Base Queryset
    product_qs = Product.objects.all()
    if category_id:
        product_qs = product_qs.filter(category_id=category_id)
    if stock_filter == 'low':
        product_qs = product_qs.filter(physical_stock__lte=5, physical_stock__gt=0)
    elif stock_filter == 'out':
        product_qs = product_qs.filter(physical_stock=0)
    elif stock_filter == 'slow':
        # Slow movers: Stock > 10 and no sales in threshold
        product_qs = product_qs.filter(physical_stock__gt=10).annotate(
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
        if p.physical_stock > 0:
            p.restock_score = Decimal(p.total_sold) / Decimal(p.physical_stock)
        else:
            p.restock_score = Decimal(p.total_sold) * 2 # Out of stock but has sales = high priority
            
        # Opportunity products: High views, low sales
        p.is_opportunity = p.total_views_num > 50 and (p.total_sold < 2)
        p.is_best_seller = p.total_sold > 10
        p.is_slow_mover = p.physical_stock > 20 and p.total_sold == 0

    # Critical Alerts
    alerts = {
        'critical_stock': products.filter(physical_stock=0)[:5],
        'low_stock': products.filter(physical_stock__lte=5, physical_stock__gt=0)[:5],
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


@warehouse_required
def admin_inventory(request):
    product_list = Product.objects.with_available_stock().select_related('category').order_by('available_stock_value')

    q = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    stock_filter = request.GET.get('stock', '').strip()

    if q:
        product_list = product_list.filter(get_smart_search_filter(q, ['title', 'slug', 'excerpt']))
    if category_filter:
        product_list = product_list.filter(category__slug=category_filter)
    if stock_filter == 'low':
        product_list = product_list.filter(available_stock_value__lte=10, available_stock_value__gt=0)
    elif stock_filter == 'out':
        product_list = product_list.filter(available_stock_value__lte=0)
    
    # Pagination
    paginator = Paginator(product_list, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    # Immutable Ledger snapshot (last 10 transactions)
    recent_transactions = InventoryTransaction.objects.select_related('product', 'variation', 'user').order_by('-timestamp')[:10]
    
    # Stats
    total_physical = Product.objects.aggregate(total=Sum('physical_stock'))['total'] or 0
    total_reserved = Product.objects.aggregate(total=Sum('reserved_stock'))['total'] or 0
    low_stock_count = Product.objects.filter(physical_stock__lte=10).count()
    
    context = {
        'products': products,
        'recent_transactions': recent_transactions,
        'categories': Category.objects.filter(is_active=True),
        'current_query': q,
        'current_category': category_filter,
        'current_stock': stock_filter,
        'stats': {
            'total_physical': total_physical,
            'total_reserved': total_reserved,
            'low_stock_count': low_stock_count,
            'total_available': total_physical - total_reserved,
            'health_score': int(((Product.objects.count() - low_stock_count) / Product.objects.count() * 100)) if Product.objects.exists() else 100
        }
    }
    return render(request, 'admin/inventory.html', context)


@accountant_required
def admin_order_list(request):
    orders = Order.objects.select_related('user', 'user__profile').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        orders = orders.filter(get_smart_search_filter(q, [
            'order_number', 'user__username', 'user__email', 
            'user__first_name', 'user__last_name', 'user__profile__phone'
        ]))

    if status and status != 'all':
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/order_list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_status': status or 'all',
        'status_choices': Order.STATUS_CHOICES,
        'total_count': orders.count(),
    })


@accountant_required
def admin_invoice_list(request):
    if request.method == 'POST' and request.POST.get('action') == 'backfill':
        eligible_statuses = ['confirmed', 'processing', 'shipping', 'delivered']
        missing_orders = Order.objects.filter(status__in=eligible_statuses).exclude(invoice__isnull=False)
        created_count = 0
        for order in missing_orders:
            order.ensure_invoice()
            created_count += 1
        if created_count > 0:
            messages.success(request, f"Đã tạo {created_count} hóa đơn.")
        else:
            messages.info(request, "Không có đơn hàng nào cần tạo hóa đơn.")
        return redirect('admin_invoice_list')

    invoices = Invoice.objects.select_related('order', 'order__user', 'order__user__profile').order_by('-generated_at')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        invoices = invoices.filter(get_smart_search_filter(q, [
            'invoice_number', 'order__order_number', 'customer_name', 
            'customer_tax_code', 'order__user__username', 'order__user__email',
            'order__user__first_name', 'order__user__last_name'
        ]))

    if status:
        invoices = invoices.filter(status=status)

    paginator = Paginator(invoices, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/invoice_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_status': status,
        'status_choices': Invoice._meta.get_field('status').choices,
        'total_count': invoices.count(),
    })

@warehouse_required
def admin_inventory_ledger(request):
    transactions = InventoryTransaction.objects.select_related('product', 'variation', 'user').order_by('-timestamp')
    
    # Filter
    q = request.GET.get('q')
    t_type = request.GET.get('type')
    if q:
        transactions = transactions.filter(Q(product__title__icontains=q) | Q(reference_id__icontains=q))
    if t_type:
        transactions = transactions.filter(transaction_type=t_type)
        
    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'admin/inventory_ledger.html', {
        'transactions': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_type': t_type,
        'type_choices': InventoryTransaction.TYPE_CHOICES
    })

@warehouse_required
def admin_inventory_receipt_create(request):
    if request.method == 'POST':
        # Simple implementation for single item receipt for now, can be expanded to formset
        product_id = request.POST.get('product')
        variation_id = request.POST.get('variation')
        quantity = int(request.POST.get('quantity', 0))
        supplier = request.POST.get('supplier', '')
        note = request.POST.get('note', '')
        
        if quantity > 0:
            with transaction.atomic():
                product = get_object_or_404(Product, id=product_id)
                variation = get_object_or_404(ProductVariation, id=variation_id) if variation_id else None
                
                # Create receipt
                receipt = InventoryReceipt.objects.create(
                    supplier=supplier,
                    status='completed',
                    note=note,
                    user=request.user
                )
                InventoryReceiptItem.objects.create(
                    receipt=receipt,
                    product=product,
                    variation=variation,
                    quantity=quantity
                )
                
                # Update stock
                if variation:
                    variation.physical_stock = F('physical_stock') + quantity
                    variation.save()
                else:
                    product.physical_stock = F('physical_stock') + quantity
                    product.save()
                
                # Log transaction
                InventoryTransaction.objects.create(
                    product=product,
                    variation=variation,
                    transaction_type='IN',
                    quantity=quantity,
                    is_physical=True,
                    reference_id=receipt.receipt_number,
                    user=request.user
                )
                
                messages.success(request, f"Đã nhập {quantity} sản phẩm vào kho.")
                return redirect('admin_inventory')
    
    products = Product.objects.all().prefetch_related('variations')
    return render(request, 'admin/inventory_receipt_form.html', {'products': products})


@accountant_required
def admin_order_detail_manage(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == 'POST':
        action = request.POST.get('action')
        success = False
        msg = "Hành động không hợp lệ."
        
        if action == 'confirm':
            success, msg = order.action_confirm(user=request.user)
        elif action == 'cancel':
            success, msg = order.action_cancel(user=request.user)
        elif action == 'complete':
            success, msg = order.action_complete(user=request.user)
        elif action == 'confirm_payment':
            try:
                payment = order.payment
            except Exception:
                success, msg = False, "Không tìm thấy thông tin thanh toán."
            else:
                if payment.payment_status == 'completed':
                    success, msg = True, "Thanh toán đã được xác nhận trước đó."
                else:
                    if order.status == 'pending':
                        confirm_success, confirm_msg = order.action_confirm(user=request.user)
                        if not confirm_success:
                            payment.payment_status = 'completed'
                            payment.payment_date = timezone.now()
                            payment.notes = f"Payment confirmed but stock reservation failed: {confirm_msg}"
                            payment.save()
                            order.set_status('pending', user=request.user, note="Đã xác nhận thanh toán nhưng thiếu tồn kho.")
                            success, msg = True, "Đã xác nhận thanh toán nhưng thiếu tồn kho. Cần xử lý thủ công."
                        else:
                            payment.payment_status = 'completed'
                            payment.payment_date = timezone.now()
                            payment.save()
                            invoice = order.ensure_invoice()
                            if invoice and invoice.status != 'paid':
                                invoice.status = 'paid'
                                invoice.save(update_fields=['status'])
                            success, msg = True, "Đã xác nhận thanh toán."
                    else:
                        payment.payment_status = 'completed'
                        payment.payment_date = timezone.now()
                        payment.save()
                        invoice = order.ensure_invoice()
                        if invoice and invoice.status != 'paid':
                            invoice.status = 'paid'
                            invoice.save(update_fields=['status'])
                        success, msg = True, "Đã xác nhận thanh toán."
        elif action == 'update_status':
            # Manual status updates with safety for inventory-related transitions
            new_status = request.POST.get('status')
            if new_status in dict(Order.STATUS_CHOICES):
                if new_status == 'confirmed':
                    success, msg = order.action_confirm(user=request.user)
                elif new_status == 'cancelled':
                    success, msg = order.action_cancel(user=request.user)
                elif new_status == 'delivered':
                    success, msg = order.action_complete(user=request.user)
                else:
                    success, msg = order.set_status(new_status, user=request.user, note="Cập nhật thủ công.")
                    if success and new_status in ['processing', 'shipping']:
                        order.ensure_invoice()
        
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
            
    # Timeline data
    status_history = order.status_history.all()
    inventory_logs = InventoryTransaction.objects.filter(reference_id=order.order_number).order_by('-timestamp')
            
    return render(request, 'admin/order_detail_manage.html', {
        'order': order, 
        'status_choices': Order.STATUS_CHOICES,
        'status_history': status_history,
        'inventory_logs': inventory_logs
    })


# ==================== PRODUCT CRUD ====================

@warehouse_required
def product_list(request):
    products = Product.objects.select_related('category').all().order_by('-created_at')
    q = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')
    if q:
        products = products.filter(Q(title__icontains=q) | Q(slug__icontains=q) | Q(excerpt__icontains=q))
    if category_filter:
        products = products.filter(category__slug=category_filter)
    if stock_filter == 'low':
        products = products.filter(physical_stock__lte=5, physical_stock__gt=0)
    elif stock_filter == 'out':
        products = products.filter(physical_stock=0)
    total_count = products.count()
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin/product_list.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'total_count': total_count,
        'current_query': q,
        'current_category': category_filter,
        'current_stock': stock_filter,
        'categories': categories,
    })


@warehouse_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Thêm Sản Phẩm'})


@warehouse_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form, 'product': product, 'title': 'Chỉnh Sửa Sản Phẩm'})


@warehouse_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'admin/confirm_delete.html', {'object': product})


# ==================== STORYBOARD CRUD ====================

@admin_required
def storyboard_list(request):
    items = StoryboardItem.objects.all().order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(Q(title__icontains=q) | Q(excerpt__icontains=q))
    total_count = items.count()
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/storyboard_list.html', {'items': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q})


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
    items = RawItem.objects.all().order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(Q(title__icontains=q) | Q(caption__icontains=q))
    total_count = items.count()
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/raw_list.html', {'items': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q})


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
    items = CabinetItem.objects.all().order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(Q(title__icontains=q) | Q(note__icontains=q))
    total_count = items.count()
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/cabinet_list.html', {'items': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q})


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

@warehouse_required
def category_list(request):
    items = Category.objects.annotate(product_count=Count('products')).all().order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    total_count = items.count()
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/category_list.html', {'items': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q})


@warehouse_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'admin/category_form.html', {'form': form})


@warehouse_required
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


@warehouse_required
def category_delete(request, pk):
    item = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('category_list')
    return render(request, 'admin/confirm_delete.html', {'object': item})

@warehouse_required
def category_toggle_active(request, pk):
    item = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        item.is_active = not item.is_active
        item.save()
    return redirect('category_list')


@accountant_required
def admin_return_list(request):
    """
    List of all return and exchange requests.
    """
    status_filter = request.GET.get('status', 'pending')
    returns = ReturnRequest.objects.all().order_by('-created_at')
    
    if status_filter != 'all':
        returns = returns.filter(status=status_filter)
    
    paginator = Paginator(returns, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/returns/return_list.html', {
        'returns': page_obj,
        'page_obj': page_obj,
        'current_status': status_filter
    })


@accountant_required
def admin_return_detail(request, return_id):
    return_req = get_object_or_404(ReturnRequest, id=return_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '')
        
        return_req.admin_note = admin_note
        
        if action == 'approve':
            return_req.status = 'approved'
            order = return_req.order
            # Update order status to reflect progress
            order.set_status('return_approved', user=request.user, note="Duyệt yêu cầu đổi/trả.")
            
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
            order.set_status('delivered', user=request.user, note="Từ chối yêu cầu đổi/trả.")
            
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
            
            if return_req.request_type in ['refund', 'cancel']:
                order.set_status('refunded', user=request.user, note="Hoàn tiền/huỷ sau thanh toán.")
                # Restore stock when items are returned
                for r_item in return_req.return_items.select_related('order_item__product', 'order_item__variation'):
                    if r_item.order_item.variation:
                        r_item.order_item.variation.physical_stock = F('physical_stock') + r_item.quantity
                        r_item.order_item.variation.save()
                    elif r_item.order_item.product:
                        r_item.order_item.product.physical_stock = F('physical_stock') + r_item.quantity
                        r_item.order_item.product.save()
                    order.log_transaction(r_item.order_item, 'IN', r_item.quantity, is_physical=True, user=request.user)
            elif return_req.request_type == 'exchange':
                order.set_status('exchanged', user=request.user, note="Đổi hàng.")
            else:
                order.set_status('returned', user=request.user, note="Đã nhận hàng trả.")
            
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


# ==================== COUPON CRUD ====================

@accountant_required
def coupon_list(request):
    coupons = Coupon.objects.all().order_by('-valid_to')
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    if q:
        coupons = coupons.filter(Q(code__icontains=q))
    if status_filter == 'active':
        coupons = coupons.filter(active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
    elif status_filter == 'inactive':
        coupons = coupons.filter(active=False)
    elif status_filter == 'expired':
        coupons = coupons.filter(valid_to__lt=timezone.now())
    total_count = coupons.count()
    paginator = Paginator(coupons, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/coupon_list.html', {'coupons': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q, 'current_status': status_filter})


@accountant_required
def coupon_create(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã tạo mã giảm giá mới.')
            return redirect('coupon_list')
    else:
        form = CouponForm()
    return render(request, 'admin/coupon_form.html', {'form': form, 'title': 'Thêm Mã Giảm Giá'})


@accountant_required
def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật mã giảm giá.')
            return redirect('coupon_list')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'admin/coupon_form.html', {'form': form, 'coupon': coupon, 'title': 'Chỉnh Sửa Mã Giảm Giá'})


@accountant_required
def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, 'Đã xóa mã giảm giá.')
        return redirect('coupon_list')
    return render(request, 'admin/confirm_delete.html', {
        'object': coupon,
        'object_name': f'mã giảm giá "{coupon.code}"',
        'cancel_url': 'coupon_list',
        'title': 'Xóa Mã Giảm Giá'
    })


@accountant_required
def coupon_toggle(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    coupon.active = not coupon.active
    coupon.save()
    status = 'kích hoạt' if coupon.active else 'tắt'
    messages.success(request, f'Đã {status} mã {coupon.code}.')
    return redirect('coupon_list')


# ==================== REVIEW & COMMENT MODERATION ====================

@admin_required
def admin_review_list(request):
    reviews = Review.objects.select_related('product', 'user').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    rating_filter = request.GET.get('rating')
    if q:
        reviews = reviews.filter(Q(title__icontains=q) | Q(content__icontains=q) | Q(user__username__icontains=q) | Q(product__title__icontains=q))
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)
    total_count = reviews.count()
    paginator = Paginator(reviews, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/review_list.html', {'reviews': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_rating': rating_filter, 'current_query': q})


@admin_required
def admin_review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Đã xóa đánh giá.')
        return redirect('admin_review_list')
    return render(request, 'admin/confirm_delete.html', {
        'object': review,
        'object_name': f'đánh giá của {review.user.username} cho "{review.product.title}"',
        'cancel_url': 'admin_review_list',
        'title': 'Xóa Đánh Giá'
    })


@admin_required
def admin_comment_list(request):
    comments = Comment.objects.select_related('product', 'user').filter(parent__isnull=True).order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        comments = comments.filter(Q(content__icontains=q) | Q(user__username__icontains=q) | Q(product__title__icontains=q))
    total_count = comments.count()
    paginator = Paginator(comments, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin/comment_list.html', {'comments': page_obj, 'page_obj': page_obj, 'total_count': total_count, 'current_query': q})


@admin_required
def admin_comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Đã xóa bình luận.')
        return redirect('admin_comment_list')
    return render(request, 'admin/confirm_delete.html', {
        'object': comment,
        'object_name': f'bình luận của {comment.user.username}: "{comment.content[:50]}..."',
        'cancel_url': 'admin_comment_list',
        'title': 'Xóa Bình Luận'
    })
@admin_required
def admin_user_list(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if role_filter:
        users = users.filter(profile__role=role_filter)
        
    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'admin/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_role': role_filter,
        'role_choices': UserProfile.ROLE_CHOICES
    })

@admin_required
def admin_user_update_role(request, user_id):
    if request.method == 'POST':
        user_to_update = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        if new_role in dict(UserProfile.ROLE_CHOICES):
            user_to_update.profile.role = new_role
            user_to_update.profile.save()
            messages.success(request, f'Đã cập nhật vai trò cho {user_to_update.username} thành {dict(UserProfile.ROLE_CHOICES)[new_role]}.')
        else:
            messages.error(request, 'Vai trò không hợp lệ.')
    return redirect('admin_user_list')

@admin_required
def admin_user_create(request):
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Đã tạo người dùng {user.username} thành công.')
            return redirect('admin_user_list')
    else:
        form = AdminUserForm()
    return render(request, 'admin/user_form.html', {'form': form, 'title': 'Thêm Người Dùng'})

@admin_required
def admin_user_edit(request, user_id):
    user_to_edit = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật người dùng {user_to_edit.username}.')
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'admin/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_role': role_filter,
        'role_choices': UserProfile.ROLE_CHOICES
    })

@admin_required
def admin_user_update_role(request, user_id):
    if request.method == 'POST':
        user_to_update = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        if new_role in dict(UserProfile.ROLE_CHOICES):
            user_to_update.profile.role = new_role
            user_to_update.profile.save()
            messages.success(request, f'Đã cập nhật vai trò cho {user_to_update.username} thành {dict(UserProfile.ROLE_CHOICES)[new_role]}.')
        else:
            messages.error(request, 'Vai trò không hợp lệ.')
    return redirect('admin_user_list')

@admin_required
def admin_user_create(request):
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Đã tạo người dùng {user.username} thành công.')
            return redirect('admin_user_list')
    else:
        form = AdminUserForm()
    return render(request, 'admin/user_form.html', {'form': form, 'title': 'Thêm Người Dùng'})

@admin_required
def admin_user_edit(request, user_id):
    user_to_edit = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật người dùng {user_to_edit.username}.')
            return redirect('admin_user_list')
    else:
        form = AdminUserForm(instance=user_to_edit)
    return render(request, 'admin/user_form.html', {'form': form, 'user_to_edit': user_to_edit, 'title': 'Chỉnh Sửa Người Dùng'})

@admin_required
def admin_user_delete(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)
    if user_to_delete == request.user:
        messages.error(request, 'Bạn không thể tự xóa chính mình.')
        return redirect('admin_user_list')
    if user_to_delete.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Bạn không thể xóa Superuser.')
        return redirect('admin_user_list')
        
    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, f'Đã xóa người dùng {user_to_delete.username}.')
        return redirect('admin_user_list')
    return render(request, 'admin/confirm_delete.html', {
        'object': user_to_delete,
        'object_name': f'người dùng "{user_to_delete.username}"',
        'cancel_url': 'admin_user_list'
    })

@admin_required
def admin_user_password_reset(request, user_id):
    user_to_reset = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if new_password:
            user_to_reset.set_password(new_password)
            user_to_reset.save()
            messages.success(request, f'Đã đổi mật khẩu cho {user_to_reset.username} thành công.')
            return redirect('admin_user_list')
        else:
            messages.error(request, 'Vui lòng nhập mật khẩu mới.')
    return render(request, 'admin/user_password_reset.html', {'user_to_reset': user_to_reset})

# ==================== AUDIT LOG (SYSTEM EVENTS) ====================

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and getattr(u.profile, 'role', '') == 'admin'))
def admin_audit_log_list(request):
    from MyApp.audit_models import AuditLog
    import json
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Filters
    q = request.GET.get('q', '').strip()
    event_type = request.GET.get('event_type', '')
    severity = request.GET.get('severity', '')
    actor_role = request.GET.get('actor_role', '')
    
    if q:
        logs = logs.filter(Q(actor_id__icontains=q) | Q(ip_address__icontains=q) | Q(reason__icontains=q) | Q(resource_id__icontains=q) | Q(log_id__icontains=q))
    if event_type:
        logs = logs.filter(event_type=event_type)
    if severity:
        logs = logs.filter(severity_level=severity)
    if actor_role:
        logs = logs.filter(actor_role=actor_role)
        
    # Get distinct options for dropdowns
    event_types = AuditLog.objects.values_list('event_type', flat=True).distinct()
    roles = AuditLog.objects.exclude(actor_role__isnull=True).exclude(actor_role='').values_list('actor_role', flat=True).distinct()
    
    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Process JSON for visualization in template
    for log in page_obj:
        try:
            log.before_parsed = json.loads(log.before_state) if log.before_state else None
        except:
            log.before_parsed = log.before_state
        try:
            log.after_parsed = json.loads(log.after_state) if log.after_state else None
        except:
            log.after_parsed = log.after_state
            
        log.before_formatted = json.dumps(log.before_parsed, indent=2, ensure_ascii=False) if log.before_parsed else 'None'
        log.after_formatted = json.dumps(log.after_parsed, indent=2, ensure_ascii=False) if log.after_parsed else 'None'
    
    return render(request, 'admin/audit_log_list.html', {
        'logs': page_obj,
        'page_obj': page_obj,
        'current_query': q,
        'current_event_type': event_type,
        'current_severity': severity,
        'current_role': actor_role,
        'event_types': event_types,
        'actor_roles': roles,
        'severity_choices': AuditLog.SEVERITY_CHOICES
    })

