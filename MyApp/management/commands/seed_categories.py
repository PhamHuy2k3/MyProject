import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from MyApp.models import Category, Product

class Command(BaseCommand):
    help = 'Seed product categories and assign them to existing products'

    def handle(self, *args, **kwargs):
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
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {item["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {item["name"]}'))
            created_categories.append(category)

        # Assign random categories to products that don't have one
        products_without_category = Product.objects.filter(category__isnull=True)
        count = 0
        for product in products_without_category:
            product.category = random.choice(created_categories)
            product.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully assigned categories to {count} products.'))
