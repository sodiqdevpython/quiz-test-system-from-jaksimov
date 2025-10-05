
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.conf.urls import handler404
from django.shortcuts import render

from django.http import HttpResponse
from django.views.decorators.http import require_GET
from pathlib import Path

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

def custom_404(request, exception):
    return render(request, '404.html', status=404)

schema_view = get_schema_view(
   openapi.Info(
      title="Test",
      default_version='v1',
      description="Test description",
      terms_of_service="sodiqdev.netlify.app",
      contact=openapi.Contact(email="sodiqdevpython@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny]
)

@require_GET
def service_worker(request):
    sw_path = Path(settings.BASE_DIR) / "static" / "sw.js"
    content = sw_path.read_text(encoding="utf-8")
    return HttpResponse(content, content_type="application/javascript")

handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path("sw.js", service_worker),
	path('', include('mainApp.urls')),
    path('', include('notifications.urls')),
    path('statistics/', include('statistic.urls')),
    path('auth/', include('customAuth.urls')),
    path("ckeditor/", include("ckeditor_uploader.urls")),

	path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
	urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)