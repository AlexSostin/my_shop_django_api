from django.urls import path
from .views import add_category_view, home, product_edit_view, product_detail_view, product_list_or_create, product_list_view, product_detail, category_list_api, category_filter_view, add_product_view
from . import views

urlpatterns = [
    # Веб-приложение (HTML представления)
    path('', home, name='home'),
    path('products/', product_list_view, name='products_list'),  
    path('products/<int:id>/', product_detail_view, name='product_detail_view'),
    path('products/<int:id>/edit/', product_edit_view, name='edit_product_view'),
    path('products/add/', add_product_view, name='add_product_view'),
    path('categories/', category_filter_view, name='category_filter_view'),
    path('categories/<int:category_id>/edit/', views.edit_category_view, name='edit_category_view'),
    path('categories/add/', add_category_view, name='add_category_view'),
    

    # API маршруты
    path('api/products/', product_list_or_create, name='product_list_api'),  # Исправлено: используем product_list_or_create
    path('api/products/<int:id>/', product_detail, name='product_detail_api'),  
    path('api/categories/', category_list_api, name='category_list_api'),
]
