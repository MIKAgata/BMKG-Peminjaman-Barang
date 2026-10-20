from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reports.urls')),
    path('accounts/', include('accounts.urls')),
    path('inventory/', include('inventory.urls')),
    path('loans/', include('loans.urls')),
    path('consumables/', include('consumables.urls')),
    path('audit/', include('audit.urls')),
]

handler403 = 'config.views.custom_permission_denied_view'
handler404 = 'config.views.custom_page_not_found_view'
handler500 = 'config.views.custom_server_error_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
