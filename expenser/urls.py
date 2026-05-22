from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
urlpatterns = [
    path('api/', include('api.authentication.urls')),
    path('api/', include('api.expenses.urls')),
    path('api/', include('api.user.urls')),
    path('api/', include('api.transaction.urls')),
    path('api/', include('api.paymentplan.urls')),
    path('api/', include('api.budget.urls')),
    path('api/', include('api.savings.urls')),
    path('api/', include('api.analytics.urls')),
    path('api/', include('api.ncell.urls')),
    path('api/', include('api.ntc.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
