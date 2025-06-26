from django.contrib import admin
from django.urls import path, include
from .views import *
from Forensic_Image_App import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome, name='welcome'),
    path('analizar/', views.analizar_imagen, name='analizar_imagen'),
    path('results/', views.results, name='results'),
   
    path("__reload__/", include("django_browser_reload.urls")),
    path('test-csrf/', lambda r: render(r, 'test_csrf.html')),
    

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
