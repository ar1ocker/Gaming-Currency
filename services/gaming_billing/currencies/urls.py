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
    path("adjustmenttransaction/create/", AdjustmentCreateView.as_view(), name="adjustment_create"),
    path("adjustmenttransaction/<str:object_pk>/confirm/", adjustment_confirm, name="adjustment_confirm"),
    path("adjustmenttransaction/<str:object_pk>/reject/", adjustment_reject, name="adjustment_reject"),
    path("transfertransaction/create/", TransferCreateView.as_view(), name="transfer_create"),
    path("transfertransaction/<str:object_pk>/confirm/", transfer_confirm, name="transfer_confirm"),
    path("transfertransaction/<str:object_pk>/reject/", transfer_reject, name="transfer_reject"),
    path("exchangetransaction/create/", ExchangeCreateView.as_view(), name="exchange_create"),
    path("exchangetransaction/<str:object_pk>/confirm/", exchange_confirm, name="exchange_confirm"),
    path("exchangetransaction/<str:object_pk>/reject/", exchange_reject, name="exchange_reject"),
]
