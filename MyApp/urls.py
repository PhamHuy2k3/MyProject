from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.index, name='index'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
    
    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('wishlist/add/<int:product_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),
    
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    
    # Admin Dashboard
    path('manage/', views.admin_dashboard, name='admin_dashboard'),
    
    # Product CRUD
    path('manage/products/', views.product_list, name='product_list'),
    path('manage/products/add/', views.product_create, name='product_create'),
    path('manage/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('manage/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Storyboard CRUD
    path('manage/storyboard/', views.storyboard_list, name='storyboard_list'),
    path('manage/storyboard/add/', views.storyboard_create, name='storyboard_create'),
    path('manage/storyboard/<int:pk>/edit/', views.storyboard_edit, name='storyboard_edit'),
    path('manage/storyboard/<int:pk>/delete/', views.storyboard_delete, name='storyboard_delete'),
    
    # Raw CRUD
    path('manage/raw/', views.raw_list, name='raw_list'),
    path('manage/raw/add/', views.raw_create, name='raw_create'),
    path('manage/raw/<int:pk>/edit/', views.raw_edit, name='raw_edit'),
    path('manage/raw/<int:pk>/delete/', views.raw_delete, name='raw_delete'),
    
    # Cabinet CRUD
    path('manage/cabinet/', views.cabinet_list, name='cabinet_list'),
    path('manage/cabinet/add/', views.cabinet_create, name='cabinet_create'),
    path('manage/cabinet/<int:pk>/edit/', views.cabinet_edit, name='cabinet_edit'),
    path('manage/cabinet/<int:pk>/delete/', views.cabinet_delete, name='cabinet_delete'),
]
