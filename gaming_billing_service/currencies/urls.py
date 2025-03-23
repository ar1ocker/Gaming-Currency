from django.urls import path

from .views import (
    AdjustmentCreateView,
    ExchangeCreateView,
    TransferCreateView,
    adjustment_confirm,
    adjustment_reject,
    exchange_confirm,
    exchange_reject,
    transfer_confirm,
    transfer_reject,
)

app_name = "currencies"

urlpatterns = [
    path("adjustments/create/", AdjustmentCreateView.as_view(), name="adjustment_create"),
    path("adjustments/confirm/<str:object_pk>/", adjustment_confirm, name="adjustment_confirm"),
    path("adjustments/reject/<str:object_pk>/", adjustment_reject, name="adjustment_reject"),
    path("transfers/create/", TransferCreateView.as_view(), name="transfer_create"),
    path("transfers/confirm/<str:object_pk>/", transfer_confirm, name="transfer_confirm"),
    path("transfers/reject/<str:object_pk>/", transfer_reject, name="transfer_reject"),
    path("exchanges/create/", ExchangeCreateView.as_view(), name="exchange_create"),
    path("exchanges/confirm/<str:object_pk>", exchange_confirm, name="exchange_confirm"),
    path("exchanges/reject/<str:object_pk>", exchange_reject, name="exchange_reject"),
]
