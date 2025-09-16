"""workbench_project URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/auth/login/', permanent=False), name='home'),
    path('auth/', include('authentication.urls')),
    path('query/', include('query.urls')),
    path('data/', include('data.urls')),
    path('metadata/', include('metadata.urls')),
    path('apex/', include('apex.urls')),
    path('bulk/', include('bulk.urls')),
    path('streaming/', include('streaming.urls')),
    path('rest/', include('rest_explorer.urls')),
    path('api/', include('rest_framework.urls')),
]

# Serve static/media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
