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
import random
from django.utils.text import slugify
from django.http import HttpResponse

def seed_categories_view(request):
    """
    Temporary view to seed categories and assign them to products.
    """
    categories_data = [
        {'name': 'Trà Xanh', 'description': 'Các loại trà xanh truyền thống và hiện đại.'},
        {'name': 'Trà Đen', 'description': 'Trà đen đậm đà, lên men hoàn toàn.'},
        {'name': 'Ô Long', 'description': 'Dòng trà ô long cao cấp với hương vị đa dạng.'},
        {'name': 'Trà Thảo Mộc', 'description': 'Các loại trà từ hoa, quả và thảo mộc tự nhiên.'},
        {'name': 'Phụ Kiện Pha Trà', 'description': 'Ấm chén, dụng cụ pha trà tinh tế.'},
    ]

    created_categories = []
    for item in categories_data:
        category, created = Category.objects.get_or_create(
            slug=slugify(item['name']),
            defaults={'name': item['name'], 'description': item['description']}
        )
        created_categories.append(category)

    # Assign random categories to products that don't have one
    products_without_category = Product.objects.filter(category__isnull=True)
    count = 0
    if created_categories:
        for product in products_without_category:
            product.category = random.choice(created_categories)
            product.save()
            count += 1

    return HttpResponse(f"Successfully created/verified categories and updated {count} products. <a href='/'>Go Home</a>")

# ==================== PUBLIC VIEWS ====================

def index(request):
    active_filter = Q(category__isnull=True) | Q(category__is_active=True)
    # Thêm prefetch_related('images') để tránh N+1 query khi hiển thị ảnh phụ
    products = Product.objects.select_related('category').prefetch_related('images').filter(active_filter)[:8]
    top_viewed_products = Product.objects.select_related('category').prefetch_related('images').filter(active_filter).order_by('-views_count')[:4]
    newest_products = Product.objects.select_related('category').prefetch_related('images').filter(active_filter).order_by('-created_at')[:4]
    categories = Category.objects.all()
    storyboard = list(StoryboardItem.objects.all()[:6])
    storyboard_columns = [storyboard[i::3] for i in range(3)]
    raws = RawItem.objects.all()[:12]
    cabinet = CabinetItem.objects.all()[:6]

    context = {
        'products': products,
        'top_viewed_products': top_viewed_products,
        'newest_products': newest_products,
        'categories': categories,
        'storyboard_items': storyboard,
        'storyboard_columns': storyboard_columns,
        'raw_items': raws,
        'cabinet_items': cabinet,
    }
    return render(request, 'index.html', context)


def storyboard_detail(request, pk):
    item = get_object_or_404(StoryboardItem, pk=pk)
    related_items = StoryboardItem.objects.exclude(pk=pk).order_by('-created_at')[:3]
    
    context = {
        'item': item,
        'related_items': related_items,
    }
    return render(request, 'storyboard/storyboard_detail.html', context)


def product_detail(request, slug):
    active_filter = Q(category__isnull=True) | Q(category__is_active=True)
    product = get_object_or_404(Product.objects.select_related('category').filter(active_filter), slug=slug)
    variations = list(product.variations.all())
    if variations:
        available_stock = sum(v.available_stock for v in variations)
    else:
        available_stock = product.available_stock
    
    # Gallery images
    gallery_images = list(product.images.all())
    
    if product.category:
        related_products = Product.objects.filter(active_filter, category=product.category).exclude(id=product.id)[:4]
    else:
        related_products = Product.objects.filter(active_filter).exclude(id=product.id)[:4]
    
    # Reviews
    reviews = product.reviews.select_related('user').prefetch_related('images').all()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Rating distribution
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for count_dict in reviews.values('rating').annotate(c=Count('id')):
        rating_counts[count_dict['rating']] = count_dict['c']
    
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    
    # Comments (top-level only, replies via template)
    comments = product.comments.filter(parent=None).select_related('user').prefetch_related('replies__user')
    
    # Increment view count
    product.views_count = F('views_count') + 1
    product.save(update_fields=['views_count'])
    product.refresh_from_db(fields=['views_count'])

    context = {
        'product': product,
        'available_stock': available_stock,
        'gallery_images': gallery_images,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_count': reviews.count(),
        'rating_counts': rating_counts,
        'user_review': user_review,
        'comments': comments,
        'comment_count': product.comments.count(),
    }
    return render(request, 'shop/product_detail.html', context)


def product_reviews_ajax(request, slug):
    """API endpoint to fetch reviews with search, sort, and pagination"""
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.select_related('user').prefetch_related('images').all()
    
    # Text Search (Debounced on frontend)
    query = request.GET.get('q', '').strip()
    if query:
        reviews = reviews.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )
        
    # Sorting
    sort = request.GET.get('sort', 'relevant')
    if sort == 'newest':
        reviews = reviews.order_by('-created_at')
    elif sort == 'highest':
        reviews = reviews.order_by('-rating', '-created_at')
    elif sort == 'lowest':
        reviews = reviews.order_by('rating', '-created_at')
    else:
        # Default 'relevant': combine length, images presence, helpful votes
        # Using a simple heuristic: order by helpful votes, then newest
        reviews = reviews.order_by('-helpful_votes', '-created_at')
        
    # Pagination
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
        
    per_page = 4
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_reviews = reviews[start_idx:end_idx]
    has_next = reviews.count() > end_idx
    
    # Render partial template
    html = render_to_string('shop/partials/review_item.html', {
        'reviews': paginated_reviews,
        'request': request,
    })
    
    from django.http import JsonResponse
    return JsonResponse({
        'html': html,
        'has_next': has_next,
        'total_count': reviews.count()
    })


def product_list_view(request):
    """Trang danh sách sản phẩm với tìm kiếm, lọc nâng cao và phân trang"""
    active_filter = Q(category__isnull=True) | Q(category__is_active=True)
    # Thêm prefetch_related('images')
    products = Product.objects.select_related('category').prefetch_related('images', 'variations').filter(active_filter)
    categories = Category.objects.filter(is_active=True)

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(description__icontains=query)
        )

    # Advanced Filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    rating = request.GET.get('rating')

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if rating:
        products = products.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=rating)

    # Filter by category
    category_slug = request.GET.get('category', '')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # Sort
    sort = request.GET.get('sort', '-created_at')
    valid_sorts = ['price', '-price', 'title', '-title', '-created_at', 'created_at']
    if sort in valid_sorts:
        products = products.order_by(sort)

    total_count = products.count()

    # Pagination — Load More style (12 per page)
    per_page = 12
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    page = max(1, page)

    end_idx = page * per_page
    product_list = list(products[:end_idx])
    for p in product_list:
        variations = list(p.variations.all())
        if variations:
            p.display_stock = sum(v.available_stock for v in variations)
        else:
            p.display_stock = p.available_stock
    has_more = total_count > end_idx
    remaining = total_count - end_idx if has_more else 0

    # Category counts for sidebar
    category_counts = {}
    all_products_in_filter = Product.objects.select_related('category').filter(active_filter)
    if query:
        all_products_in_filter = all_products_in_filter.filter(
            Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(description__icontains=query)
        )
    for cat_count in all_products_in_filter.values('category__slug', 'category__name').annotate(count=Count('id')):
        if cat_count['category__slug']:
            category_counts[cat_count['category__slug']] = cat_count['count']
    uncategorized_count = all_products_in_filter.filter(category__isnull=True).count()

    context = {
        'products': product_list,
        'categories': categories,
        'category_counts': category_counts,
        'uncategorized_count': uncategorized_count,
        'current_query': query,
        'current_category': category_slug,
        'current_sort': sort,
        'min_price': min_price,
        'max_price': max_price,
        'current_rating': rating,
        'total_count': total_count,
        'current_page': page,
        'has_more': has_more,
        'remaining': remaining,
        'per_page': per_page,
    }
    return render(request, 'shop/products.html', context)


# ==================== SEARCH VIEWS ====================

def search_suggestions(request):
    """API endpoint for search suggestions"""
    from django.http import JsonResponse
    from django.urls import reverse
    
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})
    
    active_filter = Q(category__isnull=True) | Q(category__is_active=True)
    products = Product.objects.filter(active_filter).filter(
        Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(category__name__icontains=q)
    ).select_related('category')[:6]
    
    results = []
    for p in products:
        results.append({
            'title': p.title,
            'url': reverse('product_detail', kwargs={'slug': p.slug}),
            'price': float(p.price) if p.price else 0,
            'image_url': p.image.url if p.image else None,
            'category': p.category.name if p.category else 'Sản phẩm',
            'excerpt': p.excerpt[:60] if p.excerpt else ''
        })
    
    return JsonResponse({'results': results})


@login_required(login_url='login')
def review_vote_helpful(request, review_id):
    from django.http import JsonResponse
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        review.helpful_votes = F('helpful_votes') + 1
        review.save(update_fields=['helpful_votes'])
        review.refresh_from_db()
        return JsonResponse({'success': True, 'helpful_votes': review.helpful_votes})
    return JsonResponse({'success': False, 'error': 'Invalid request'})



