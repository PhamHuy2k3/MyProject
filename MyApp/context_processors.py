from MyApp.models import Category

def categories(request):
    """
    Returns all active categories to be available in every template.
    """
    return {
        'all_categories': Category.objects.filter(is_active=True)
    }
