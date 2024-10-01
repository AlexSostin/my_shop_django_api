from django.contrib import admin
from products.models import Product, Category

# Регистрируем модель Product
admin.site.register(Product)

# Регистрируем модель Category с кастомной админкой
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'popularity', 'image_preview')  # Показываем имя и популярность в списке
    readonly_fields = ['image_preview']  # Поле для превью изображения (только для чтения)
    
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 100px;" />'
        return 'No Image'
    
    image_preview.allow_tags = True  # Позволяем отображать HTML в админке
    image_preview.short_description = 'Preview'
