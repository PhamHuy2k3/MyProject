import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

from MyApp.models import Product, ProductVariation
from django.db.models import Sum

products = Product.objects.filter(reserved_stock__gt=0)
print(f"Products with reserved_stock > 0: {products.count()}")
for p in products:
    print(f"- [Product] {p.title}: {p.reserved_stock}")

variations = ProductVariation.objects.filter(reserved_stock__gt=0)
print(f"Variations with reserved_stock > 0: {variations.count()}")
for v in variations:
    print(f"- [Variation] {v.product.title} ({v.name}): {v.reserved_stock}")

# Test the annotation from admin_views
from django.db.models.functions import Coalesce
from django.db.models import F

print("\nTesting annotate logic for one product if possible:")
test_p = Product.objects.annotate(
    eff_reserved=Coalesce(Sum('variations__reserved_stock'), F('reserved_stock'))
).filter(eff_reserved__gt=0)
print(f"Products with eff_reserved > 0 via annotate: {test_p.count()}")
for p in test_p:
    print(f"- {p.title}: {p.eff_reserved} (Raw: {p.reserved_stock})")
