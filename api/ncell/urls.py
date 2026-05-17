from django.urls import path

from .views import NcellConfirmPurchaseView, NcellPackCatalogView, NcellSendOtpView


urlpatterns = [
    path('ncell/packs/', NcellPackCatalogView.as_view(), name='ncell-pack-catalog'),
    path('ncell/send-otp/', NcellSendOtpView.as_view(), name='ncell-send-otp'),
    path('ncell/confirm/', NcellConfirmPurchaseView.as_view(), name='ncell-confirm-purchase'),
]

