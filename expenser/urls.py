from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
urlpatterns = [
    path('api/', include('api.authentication.urls')),
    path('api/', include('api.expenses.urls')),
    path('api/', include('api.user.urls')),
    path('api/', include('api.transaction.urls')),
    path('api/', include('api.paymentplan.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc')
]
