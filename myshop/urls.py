from django.contrib import admin
from django.urls import include, path
from django.conf import settings  # Используем django.conf.settings для получения настроек
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('products.urls')),  # Маршруты вашего приложения
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # Меню аутентификации REST Framework
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Сначала медиа
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # Потом статические файлы
