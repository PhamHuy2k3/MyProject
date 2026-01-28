from django.contrib import admin
from .models import Product, StoryboardItem, RawItem, CabinetItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'price', 'created_at')
	prepopulated_fields = {'slug': ('title',)}


@admin.register(StoryboardItem)
class StoryboardAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'created_at')
	prepopulated_fields = {'slug': ('title',)}


@admin.register(RawItem)
class RawItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_at')


@admin.register(CabinetItem)
class CabinetItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_at')
