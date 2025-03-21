from django.urls import path

from .views.accounts import CheckingAccountDetailAPI
from .views.transactions import (
    TransactionConfirmAPI,
    TransactionCreateAPI,
    TransactionRejectAPI,
)
from .views.transfers import TransferConfirmAPI, TransferCreateAPI, TransferRejectAPI
from .views.units import CurrencyUnitsListAPI

urlpatterns = [
    path("accounts/", CheckingAccountDetailAPI.as_view()),
    path("units/", CurrencyUnitsListAPI.as_view()),
    path("transactions/create/", TransactionCreateAPI.as_view()),
    path("transactions/confirm/", TransactionConfirmAPI.as_view()),
    path("transactions/reject/", TransactionRejectAPI.as_view()),
    path("transfers/create/", TransferCreateAPI.as_view()),
    path("transfers/confirm/", TransferConfirmAPI.as_view()),
    path("transfers/reject/", TransferRejectAPI.as_view()),
]
