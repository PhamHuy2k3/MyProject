import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

from MyApp.models import Product

count = 0
for p in Product.objects.all():
    p.views_count = random.randint(10, 500)
    p.save(update_fields=['views_count'])
    count += 1
print(f"Seeding complete for {count} products.")
