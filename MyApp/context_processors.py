from django.core.cache import cache
from MyApp.models import Category, SupportTicket, Wishlist, CartItem

def categories(request):
    """
    Returns all active categories to be available in every template.
    """
    cache_key = 'active_categories'
    categories = cache.get(cache_key)
    if categories is None:
        categories = list(
            Category.objects.filter(is_active=True).only('id', 'name', 'slug').order_by('name')
        )
        cache.set(cache_key, categories, 600)
    return {
        'all_categories': categories
    }


def support_context(request):
    """
    Inject support chat categories into all templates.
    """
    return {
        'support_categories': SupportTicket.CATEGORY_CHOICES,
    }


def user_badges(request):
    """
    Provide lightweight badge counts for base template.
    Cached briefly to reduce repeated hits under load.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    cache_key = f'user_badges_{user.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = {
        'wishlist_count': Wishlist.objects.filter(user=user).count(),
        'cart_item_count': CartItem.objects.filter(cart__user=user).count(),
    }
    cache.set(cache_key, data, 30)
    return data
