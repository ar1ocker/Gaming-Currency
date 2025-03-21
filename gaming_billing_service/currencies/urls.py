from django.urls import path

from .views import (
    ExchangeCreateView,
    TransactionCreateView,
    TransferCreateView,
    exchange_confirm,
    exchange_reject,
    transaction_confirm,
    transaction_reject,
    transfer_confirm,
    transfer_reject,
)

app_name = "currencies"

urlpatterns = [
    path("transactions/create/", TransactionCreateView.as_view(), name="transaction_create"),
    path("transactions/confirm/<str:object_pk>/", transaction_confirm, name="transaction_confirm"),
    path("transactions/reject/<str:object_pk>/", transaction_reject, name="transaction_reject"),
    path("transfers/create/", TransferCreateView.as_view(), name="transfer_create"),
    path("transfers/confirm/<str:object_pk>/", transfer_confirm, name="transfer_confirm"),
    path("transfers/reject/<str:object_pk>/", transfer_reject, name="transfer_reject"),
    path("exchanges/create/", ExchangeCreateView.as_view(), name="exchange_create"),
    path("exchanges/confirm/<str:object_pk>", exchange_confirm, name="exchange_confirm"),
    path("exchanges/reject/<str:object_pk>", exchange_reject, name="exchange_reject"),
]
