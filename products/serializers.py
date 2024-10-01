from rest_framework import serializers
from .models import Product, Category
from django.db.models import Count

class CategorySerializer(serializers.ModelSerializer):
    # Добавляем вычисляемое поле product_count
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'image']  # Включаем поле product_count


class ProductSerializer(serializers.ModelSerializer):
    # Для записи категории по ее ID (при создании или обновлении продукта)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    
    # Для чтения данных категории (при получении данных о продукте)
    category = CategorySerializer(read_only=True)  

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category', 'category_id', 'image']  # Включаем category и category_id
