from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from products.models import Product, Category
from products.serializers import ProductSerializer, CategorySerializer
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.middleware.csrf import get_token
from django.http import HttpResponse


# API представления

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

def product_list_view(request):
    """
    HTML страница для отображения списка продуктов с фильтрацией по категориям и сортировкой.
    """
    categories = Category.objects.all()
    popular_categories = Category.objects.annotate(product_count=Count('products')).order_by('-product_count')[:5]
    
    # Получаем выбранную категорию из GET-параметра
    selected_category_id = request.GET.get('category_id')
    
    # Получаем параметр сортировки из GET-параметра
    sort_param = request.GET.get('sort', 'name')  # По умолчанию сортировка по имени

    # Если категория выбрана, фильтруем продукты по категории
    if selected_category_id:
        products = Product.objects.filter(category_id=selected_category_id)
    else:
        products = Product.objects.all()

    # Сортируем продукты в зависимости от выбранного параметра
    if sort_param == 'price':
        products = products.order_by('price')
    elif sort_param == 'category':
        products = products.order_by('category__name')
    else:
        products = products.order_by('name')

    # Отображаем страницу с продуктами
    return render(request, 'products/products_list.html', {
        'products': products,
        'categories': categories,
        'popular_categories': popular_categories,
        'selected_category_id': selected_category_id,
        'sort_param': sort_param,  # Передаем параметр сортировки в шаблон
    })



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


def product_edit_view(request, id):
    product = get_object_or_404(Product, id=id)
    categories = Category.objects.all()  # Получаем все категории
    
    if request.method == 'POST':
        # Получаем данные из POST-запроса
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        category_id = request.POST.get('category')

        # Если изображение было загружено, обновляем его
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        
        # Обновляем категорию, если выбрана
        if category_id:
            product.category_id = category_id

        # Сохраняем изменения в продукте
        product.save()
        return redirect('product_detail_view', id=product.id)
    
    return render(request, 'products/edit_product.html', {
        'product': product,
        'categories': categories  # Передаем категории в шаблон
    })

def edit_category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.POST.get('name')
        description = request.POST.get('description')
        image = request.FILES.get('image')

        # Обновляем поля категории
        category.name = name
        category.description = description

        if image:
            category.image = image  # Обновляем изображение, если оно есть
        
        # Сохраняем изменения
        category.save()
        
        return redirect('category_filter_view')  # Перенаправляем обратно к списку категорий
    
    return render(request, 'products/edit_category.html', {'category': category})

def add_category_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name and description:
            Category.objects.create(name=name, description=description)
            return redirect('category_filter_view')
        else:
            return HttpResponse("Name and description are required.", status=400)
    
    return render(request, 'products/add_category.html')

def add_product_view(request):
    return render(request, 'products/add_product.html')

def home(request):
    return render(request, 'products/index.html')