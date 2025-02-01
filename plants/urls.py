from django.urls import path
from . import views
from django.urls import path
from . import views


app_name = 'plants'
urlpatterns = [
    path('current/', views.current_plantings, name='current_plantings'),
]



app_name = 'plants'
urlpatterns = [
    path('current/', views.current_plantings, name='current_plantings'),

    # УДАЛИТЕ ЭТУ СТРОКУ:
    # path('admin/', admin.site.urls),  ← Это должно быть только в zelen_pro/urls.py
]