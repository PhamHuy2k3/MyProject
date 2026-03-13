from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.index, name='index'),
    path('products/', views.product_list_view, name='product_list_public'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('storyboard/<int:pk>/', views.storyboard_detail, name='storyboard_detail'),
    
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
    path('profile/quick-update/', views.profile_quick_update, name='profile_quick_update'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),
    
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
    # Admin Dashboard
    path('manage/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    path('manage/users/add/', views.admin_user_create, name='admin_user_create'),
    path('manage/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('manage/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    path('manage/users/<int:user_id>/password-reset/', views.admin_user_password_reset, name='admin_user_password_reset'),
    path('manage/users/<int:user_id>/update-role/', views.admin_user_update_role, name='admin_user_update_role'),
    
    # Admin Statistics & Inventory
    path('manage/statistics/', views.admin_statistics, name='admin_statistics'),
    path('manage/inventory/', views.admin_inventory, name='admin_inventory'),
    path('manage/inventory/ledger/', views.admin_inventory_ledger, name='admin_inventory_ledger'),
    path('manage/inventory/receipt/new/', views.admin_inventory_receipt_create, name='admin_inventory_receipt_create'),
    path('manage/orders/', views.admin_order_list, name='admin_order_list'),
    path('manage/invoices/', views.admin_invoice_list, name='admin_invoice_list'),
    path('manage/orders/<str:order_number>/manage/', views.admin_order_detail_manage, name='admin_order_detail_manage'),
    path('manage/returns/', views.admin_return_list, name='admin_return_list'),
    path('manage/returns/<int:return_id>/', views.admin_return_detail, name='admin_return_detail'),
    
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
    
    # Category CRUD
    path('manage/categories/', views.category_list, name='category_list'),
    path('manage/categories/add/', views.category_create, name='category_create'),
    path('manage/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('manage/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('manage/categories/<int:pk>/toggle/', views.category_toggle_active, name='category_toggle_active'),
    
    # Coupon CRUD
    path('manage/coupons/', views.coupon_list, name='coupon_list'),
    path('manage/coupons/add/', views.coupon_create, name='coupon_create'),
    path('manage/coupons/<int:coupon_id>/edit/', views.coupon_edit, name='coupon_edit'),
    path('manage/coupons/<int:coupon_id>/delete/', views.coupon_delete, name='coupon_delete'),
    path('manage/coupons/<int:coupon_id>/toggle/', views.coupon_toggle, name='coupon_toggle'),
    
    # Admin Review & Comment Moderation
    path('manage/reviews/', views.admin_review_list, name='admin_review_list'),
    path('manage/reviews/<int:pk>/delete/', views.admin_review_delete, name='admin_review_delete'),
    path('manage/comments/', views.admin_comment_list, name='admin_comment_list'),
    path('manage/comments/<int:pk>/delete/', views.admin_comment_delete, name='admin_comment_delete'),
    
    # Reviews & Comments
    path('product/<slug:slug>/review/', views.review_create, name='review_create'),
    path('product/<slug:slug>/reviews-ajax/', views.product_reviews_ajax, name='product_reviews_ajax'),
    path('review/<int:review_id>/helpful/', views.review_vote_helpful, name='review_vote_helpful'),
    
    # Comments specifically
    path('product/<slug:slug>/comment/', views.comment_create, name='comment_create'),
    path('product/<slug:slug>/comments-ajax/', views.comments_ajax_view, name='comments_ajax_view'),
    path('comment/<int:comment_id>/interact/', views.comment_interact_api, name='comment_interact_api'),
    path('comment/<int:comment_id>/delete/', views.comment_delete_api, name='comment_delete_api'),
    
    # Messaging
    path('messages/', views.message_inbox, name='message_inbox'),
    path('messages/<int:conversation_id>/', views.message_detail, name='message_detail'),
    path('messages/new/<int:user_id>/', views.message_new, name='message_new'),
    path('api/messages/search-users/', views.message_search_users, name='message_search_users'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('api/notifications/count/', views.notification_count_api, name='notification_count_api'),
    path('api/notifications/list/', views.notification_list_ajax, name='notification_list_ajax'),
    path('api/notifications/dropdown/', views.notification_dropdown_api, name='notification_dropdown_api'),
    path('api/notifications/stream/', views.notification_sse, name='notification_sse'),
    # Orders & Invoices
    path('orders/', views.order_list, name='order_list'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Support & Returns
    path('order/<str:order_number>/request-return/', views.request_return, name='request_return'),
    path('order/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Payment & Invoice
    path('payment/<str:order_number>/', views.payment_view, name='payment'),
    path('payment/<str:order_number>/qr/', views.payment_qr_image, name='payment_qr_image'),
    path('payment/<str:order_number>/confirm/', views.payment_confirm, name='payment_confirm'),
    
    # Invoice Download
    path('invoice/<str:order_number>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoice/<str:order_number>/pdf-qr/', views.invoice_pdf_with_qr, name='invoice_pdf_with_qr'),
    path('invoice/<str:order_number>/xml/', views.export_order_xml, name='export_order_xml'),
    # Search
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    
    # AI Chatbot
    path('api/chatbot/history/', views.api_chat_history, name='api_chat_history'),
    path('api/chatbot/chat/', views.api_chat_message, name='api_chat_message'),

    # Support Chat — Customer APIs
    path('api/support/status/', views.api_support_status, name='api_support_status'),
    path('api/support/tickets/', views.api_support_create_ticket, name='api_support_create_ticket'),
    path('api/support/tickets/<int:ticket_id>/messages/', views.api_support_messages_get, name='api_support_messages_get'),
    path('api/support/tickets/<int:ticket_id>/send/', views.api_support_messages_send, name='api_support_messages_send'),
    path('api/support/tickets/<int:ticket_id>/close/', views.api_support_close, name='api_support_close'),
    path('api/support/tickets/<int:ticket_id>/rate/', views.api_support_rate, name='api_support_rate'),
    path('api/support/tickets/<int:ticket_id>/upload/', views.api_support_upload, name='api_support_upload'),
    
    # Support Chat page (redirect to home since widget is included in base template)
    path('support-chat/', views.support_chat_page, name='support_chat_page'),

    # Support Chat — Agent/Admin URLs
    path('manage/support/', views.admin_support_dashboard, name='admin_support_dashboard'),
    path('manage/support/<int:ticket_id>/', views.admin_support_ticket_detail, name='admin_support_ticket_detail'),
    path('manage/support/<int:ticket_id>/reply/', views.api_agent_reply, name='api_agent_reply'),
    path('manage/support/<int:ticket_id>/assign/', views.api_agent_assign, name='api_agent_assign'),
    path('manage/support/<int:ticket_id>/resolve/', views.api_agent_resolve, name='api_agent_resolve'),
    path('manage/support/<int:ticket_id>/priority/', views.api_agent_set_priority, name='api_agent_set_priority'),

    # Payment Webhooks (auto-confirm)
    path('api/webhook/casso/', views.casso_webhook, name='casso_webhook'),

    # Temporary Seeding
    path('seed-categories/', views.seed_categories_view, name='seed_categories_temp'),
]
