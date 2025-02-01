from django.contrib import admin
from django.urls import include, path
from plants.views import home  # Если используете домашнюю страницу

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),  # Админка только здесь!
    path('plants/', include('plants.urls')),
]