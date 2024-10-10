from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),

    # Аутентификация
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),

    # Продукты
    path('add-product/', views.add_product_view, name='add_product'),
    path('products/', views.product_list_view, name='products_list'),
    path('products/<int:id>/', views.product_detail_view, name='product_detail_view'),
    path('products/<int:id>/edit/', views.edit_product_view, name='edit_product_view'),
    path('products/add/', views.add_product_view, name='add_product_view'),
    path('products/<int:id>/delete/', views.delete_product, name='delete_product'),

    # Категории
    path('categories/', views.category_filter_view, name='category_filter_view'),
    path('categories/add/', views.add_category_view, name='add_category_view'),
    path('categories/<int:category_id>/', views.category_detail_view, name='category_detail_view'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:pk>/delete/', views.DeleteCategoryView.as_view(), name='delete_category'),

    # Корзина и заказы
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/', views.order_confirmation, name='order_confirmation'),
    path('order-history/', views.order_history, name='order_history'),

    # Поиск
    path('search/', views.search_view, name='search'),
    
    # path('test-session/', views.test_session, name='test_session'),
    # API маршруты
    path('api/products/', views.product_list_or_create, name='product_list_api'),
    path('api/products/<int:id>/', views.product_detail, name='product_detail_api'),  
    path('api/categories/', views.api_categories_list, name='api_categories_list'),
    path('api/products/featured/', views.api_featured_products, name='api_featured_products'),
]

# Добавляем это условие только если вы уверены, что оно не дублируется в корневом urls.py
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)