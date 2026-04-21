from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentPlanViewSet

router = DefaultRouter()
router.register(r'paymentplans', PaymentPlanViewSet, basename='paymentplan')

urlpatterns = [
    path('', include(router.urls)),
]