from MyApp.models import Category, SupportTicket

def categories(request):
    """
    Returns all active categories to be available in every template.
    """
    return {
        'all_categories': Category.objects.filter(is_active=True)
    }


def support_context(request):
    """
    Inject support chat categories into all templates.
    """
    return {
        'support_categories': SupportTicket.CATEGORY_CHOICES,
    }
