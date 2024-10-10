from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from products.serializers import ProductSerializer, CategorySerializer
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.middleware.csrf import get_token
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import ValidationError, PermissionDenied
from .forms import CategoryForm, ProductForm, UserProfileForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Category, Product, CartItem, Order, OrderItem, Profile
from rest_framework import generics, permissions
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator 
import logging 
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.contrib import messages
from django.contrib.auth.models import User
import json
from .cart import Cart
from django.db import transaction
from django.db.utils import IntegrityError
from .settings import FEATURED_PRODUCTS_COUNT, POPULAR_CATEGORIES_COUNT
from django.http import HttpResponseForbidden
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from decimal import Decimal
from django.core.paginator import Paginator
import sys
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from .models import Product

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [decimal_to_float(item) for item in obj]
    return obj

class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Константы
FEATURED_PRODUCTS_COUNT = 6
POPULAR_CATEGORIES_COUNT = 5

logger = logging.getLogger(__name__)

# API представления
@method_decorator(csrf_exempt, name='dispatch')
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Разрешаем доступ всем для тестирования

    def create(self, request, *args, **kwargs):
        logger.info(f"Received data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.exception("Error creating product")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def csrf_token(request):
    """
    API для получения CSRF-токена.
    Используйте этот токен в POST, PUT, DELETE запросах.
    """
    token = get_token(request)
    return Response({'csrfToken': token})

@api_view(['GET', 'POST'])
def product_list_or_create(request):
    try:
        if request.method == 'GET':
            # Фильтрация по категории
            category_id = request.GET.get('category_id')
            if category_id:
                products = Product.objects.filter(category_id=category_id)
            else:
                products = Product.objects.all()
    
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            # Добавление продукта с CSRF защитой
            serializer = ProductSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
def product_detail(request, id):
    """
    API для работы с продуктом:
    - GET: получение одного продукта по ID.
    - PUT: обновление продукта по ID.
    - DELETE: удаление продукта по ID.
    """
    product = get_object_or_404(Product, id=id)

    if request.method == 'GET':
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Логика для обновления продукта
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            print(serializer.errors)  # Логирование ошибок
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Логика для удаления продукта
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# API для списка категорий
@api_view(['GET'])
def category_list_api(request):
    """
    API для получения списка категорий с подсчетом количества продуктов в каждой категории.
    """
    categories = Category.objects.annotate(product_count=Count('products'))  # 'products' — это related_name у ForeignKey в модели Product
    
    if not categories.exists():
        return Response({"message": "No categories available."}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

# HTML представления

@require_http_methods(["GET", "POST"])
@login_required  # Добавьте эту декорацию, если требуется аутентификация
def product_edit_view(request, id):
    product = get_object_or_404(Product, id=id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail_view', id=product.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'products/edit_product.html', {
        'form': form,
        'product': product,
        'categories': categories
    })

@require_http_methods(["GET", "POST"])
def add_category_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('category_filter_view')
    else:
        form = CategoryForm()
    
    return render(request, 'products/add_category.html', {'form': form})

def filter_products(category_id=None):
    if category_id:
        return Product.objects.filter(category_id=category_id)
    return Product.objects.all()

def product_list_view(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    # Фильтрация по категории
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Сортировка
    sort_by = request.GET.get('sort', 'name')  # По умолчанию сортируем по имени
    products = products.order_by(sort_by)

    # Пагинация
    paginator = Paginator(products, 9)  # 9 продуктов на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }

    return render(request, 'products/products_list.html', context)

def product_detail_view(request, id):
    """
    HTML страница для детального отображения одного продукта.
    """
    product = get_object_or_404(Product, id=id)
    return render(request, 'products/product_page.html', {'product': product})

def category_filter_view(request):
    """
    HTML представление для фильтрации продуктов по категории.
    Если категория не выбрана, отображаем все продукты.
    """
    categories = Category.objects.all()
    selected_category_id = request.GET.get('category_id') 

    if selected_category_id:
        selected_category = get_object_or_404(Category, id=selected_category_id)
        products = Product.objects.filter(category=selected_category)
    else:
        selected_category = None
        products = Product.objects.all()

    return render(request, 'products/category_list.html', {
        'categories': categories,
        'selected_category': selected_category,
        'selected_category_id': selected_category_id,
        'products': products
    })

def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_detail_view', category_id=category.id)
    else:
        form = CategoryForm(instance=category)
    return render(request, 'products/edit_category.html', {'form': form, 'category': category})

class DeleteCategoryView(UserPassesTestMixin, DeleteView):
    model = Category
    template_name = 'products/delete_category.html'
    success_url = reverse_lazy('category_filter_view')  # Изменено на существующий URL-паттерн

    def test_func(self):
        return self.request.user.is_superuser

def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(lambda u: u.is_staff)
def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.save()
            messages.success(request, 'Product added successfully.')
            return redirect('products_list')
    else:
        form = ProductForm()
    return render(request, 'products/add_product.html', {'form': form})

def category_detail_view(request, category_id):
    """
    HTML страница для детального отображения одной категории.
    """
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products
    })
    
    
@login_required
@require_POST
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    return redirect('product_list_view')

def api_categories_list(request):
    try:
        categories = Category.objects.all()
        data = [{'id': category.id, 'name': category.name} for category in categories]
        logger.info(f"Returning {len(data)} categories")
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error in api_categories_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_featured_products(request):
    try:
        products = Product.objects.filter(featured=True)[:FEATURED_PRODUCTS_COUNT]
        data = [{
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': str(product.price),
            'image': product.image.url if product.image else None
        } for product in products]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error in api_featured_products: {str(e)}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)
    
def home(request):
    categories = Category.objects.all()[:6]  # Получаем первые 6 категорий
    products = Product.objects.all()  # Получаем все продукты
    
    context = {
        'categories': categories,
        'products': products,
    }
    
    return render(request, 'products/home.html', context)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # или куда вы хотите перенаправить после входа
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_staff)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'add_category.html', {'form': form})

@require_POST
@csrf_exempt
def add_to_cart(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        cart = Cart(request)
        quantity = json.loads(request.body).get('quantity', 1)
        cart.add(product, quantity)
        return JsonResponse({'success': True, 'cart_count': len(cart)})
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def remove_from_cart(request, item_id):
    cart = Cart(request)
    try:
        cart.remove(item_id)
       
        cart_items = []
        for item in cart:
            product_data = item['product']
            cart_items.append({
                'id': product_data['id'],
                'name': product_data['name'],
                'price': float(product_data['price']),
                'quantity': item['quantity'],
                'total_price': float(item['total_price']),
            })
        
        subtotal = float(cart.get_total_price())
        tax = float(subtotal * 0.10)
        total = float(subtotal + tax)

        return JsonResponse({
            'success': True,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'tax': tax,
            'total': total,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def calculate_cart_totals(cart_items):
    subtotal = sum(item.total_price() for item in cart_items)
    tax = subtotal * Decimal('0.1')  # 10% tax
    total = subtotal + tax
    return subtotal, tax, total

def cart_view(request):
    cart = Cart(request)
    cart_items = []
    for item in cart:
        product_data = item['product']  # Это теперь словарь
        cart_item = {
            'id': product_data['id'],
            'name': product_data['name'],
            'price': float(product_data['price']),
            'quantity': item['quantity'],
            'total_price': item['total_price'],
        }
        cart_items.append(cart_item)
        logger.debug(f"Added cart item: {cart_item}")
    
    if not cart_items:
        return render(request, 'products/cart.html', {'cart_empty': True})
    
    subtotal = cart.get_total_price()
    tax = subtotal * 0.10  # Предполагаем 10% налог
    total = subtotal + tax

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }
    
    logger.info(f"Cart view context: {context}")
    
    return render(request, 'products/cart.html', context)

@login_required
def checkout(request):
    if request.method == 'POST':
        cart_items = CartItem.objects.filter(user=request.user)
        subtotal, tax, total = calculate_cart_totals(cart_items)
        
        try:
            with transaction.atomic():
                order = Order.objects.create(user=request.user, total_price=total)
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                cart_items.delete()  # Очищаем корзину
            return redirect('order_confirmation', order_id=order.id)
        except IntegrityError:
            messages.error(request, "An error occurred while processing your order. Please try again.")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
    
    cart_items = CartItem.objects.filter(user=request.user)
    subtotal, tax, total = calculate_cart_totals(cart_items)
    return render(request, 'products/checkout.html', {'cart_items': cart_items, 'total': total})

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'products/order_confirmation.html', {'order': order})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'products/order_history.html', {'orders': orders})

@login_required
def edit_product_view(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail_view', id=product.id)
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/edit_product.html', {'form': form, 'product': product})

@require_POST
def update_cart(request, item_id):
    cart = Cart(request)
    try:
        data = json.loads(request.body)
        quantity = data.get('quantity')
        
        if quantity is None:
            return JsonResponse({'success': False, 'error': 'Quantity is required'}, status=400)
        
        quantity = int(quantity)
        
        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)
        
        cart.update(item_id, quantity)
        
        cart_items = []
        for item in cart:
            product_data = item['product']
            print(f"Debug: product_data = {product_data}")  # Добавьте эту строку
            cart_items.append({
                'id': product_data['id'],
                'name': product_data['name'],
                'price': float(product_data['price']),
                'quantity': item['quantity'],
                'total_price': float(item['total_price']),
            })
        
        subtotal = float(cart.get_total_price())
        tax = float(subtotal * 0.10)
        total = float(subtotal + tax)

        print(f"Debug: cart_items = {cart_items}")  # Добавьте эту строку
        print(f"Debug: subtotal = {subtotal}, tax = {tax}, total = {total}")  # Добавьте эту строку

        return JsonResponse({
            'success': True,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'tax': tax,
            'total': total,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        print(f"Debug: ValueError - {str(e)}")  # Добавьте эту строку
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        print(f"Debug: Unexpected error - {str(e)}")  # Добавьте эту строку
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def products_list(request):
    products = Product.objects.all()
    return render(request, 'products/products_list.html', {'products': products})

def search_view(request):
       query = request.GET.get('q')
       if query:
           products = Product.objects.filter(
               Q(name__icontains=query) | 
               Q(description__icontains=query) |
               Q(category__name__icontains=query)
           ).distinct()
       else:
           products = Product.objects.none()
       
       paginator = Paginator(products, 12)  # 12 продуктов на страницу
       page_number = request.GET.get('page')
       page_obj = paginator.get_page(page_number)
       
       context = {
           'page_obj': page_obj,
           'query': query
       }
       return render(request, 'products/search_results.html', context)
   
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')  # или куда вы хотите перенаправить после регистрации
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if 'avatar' in request.FILES:
                try:
                    image = Image.open(request.FILES['avatar'])
                    # Обрезаем изображение до квадрата
                    size = min(image.size)
                    crop = ((image.size[0] - size) // 2,
                            (image.size[1] - size) // 2,
                            (image.size[0] + size) // 2,
                            (image.size[1] + size) // 2)
                    image = image.crop(crop)
                    # Изменяем размер до 200x200
                    image = image.resize((200, 200), Image.LANCZOS)
                    # Сохраняем изображение
                    output = BytesIO()
                    image.save(output, format='JPEG', quality=85)
                    output.seek(0)
                    profile.avatar = InMemoryUploadedFile(output, 'ImageField', 
                                                          f"{request.user.username}_avatar.jpg",
                                                          'image/jpeg', sys.getsizeof(output), None)
                    profile.save()
                except Exception as e:
                    print(f"Error processing avatar: {e}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'avatar_url': profile.avatar.url if profile.avatar else None,
                    'username': request.user.username,
                    # Добавьте другие поля, которые вы хотите обновить на странице
                })
            else:
                return redirect('profile')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': form.errors})
            # Если это не AJAX-запрос, отрендерим страницу с ошибками
    else:
        form = UserProfileForm(instance=request.user)
    
    orders = request.user.order_set.all().order_by('-created_at')
    
    context = {
        'form': form,
        'orders': orders,
        'profile': profile,
    }
    return render(request, 'products/profile.html', context)

@login_required
@require_POST
def upload_avatar(request):
    if 'avatar' in request.FILES:
        avatar = request.FILES['avatar']
        request.user.profile.avatar = avatar
        request.user.profile.save()
        return JsonResponse({
            'success': True,
            'avatar_url': request.user.profile.avatar.url
        })
    return JsonResponse({'success': False, 'error': 'No file was uploaded.'})

# def test_session(request):
#        cart = request.session.get('cart', {})
#        return HttpResponse(f"Cart contents: {cart}")
   
# def is_admin_or_owner(user, product_id):
#     if user.is_superuser:
#         return True
#     product = get_object_or_404(Product, id=product_id)
#     return product.owner == user

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        product.delete()
        return redirect('products_list')  # или куда вы хотите перенаправить после удаления
    return redirect('product_detail', id=id)  

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def create_product(request):
    logger.info(f"Received data: {request.data}")
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        try:
            product = serializer.save(owner=request.user)
            logger.info(f"Product created: {product.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return Response({"detail": "Error creating product"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    logger.error(f"Validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    # Логика добавления продукта
    return render(request, 'products/add_product.html')
