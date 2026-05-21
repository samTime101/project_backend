from django.urls import path

from .views import NtcConfirmPurchaseView, NtcPackCatalogView, NtcSendOtpView


urlpatterns = [
    path('ntc/packs/', NtcPackCatalogView.as_view(), name='ntc-pack-catalog'),
    path('ntc/send-otp/', NtcSendOtpView.as_view(), name='ntc-send-otp'),
    path('ntc/confirm/', NtcConfirmPurchaseView.as_view(), name='ntc-confirm-purchase'),
]
