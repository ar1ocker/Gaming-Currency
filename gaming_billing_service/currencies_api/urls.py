from django.urls import path

from .views.accounts import CheckingAccountDetailAPI, CheckingAccountListAPI
from .views.adjustments import (
    AdjustmentConfirmAPI,
    AdjustmentCreateAPI,
    AdjustmentListAPI,
    AdjustmentRejectAPI,
)
from .views.exchanges import ExchangeConfirmAPI, ExchangeCreateAPI, ExchangeRejectAPI
from .views.transfers import TransferConfirmAPI, TransferCreateAPI, TransferRejectAPI
from .views.units import CurrencyUnitsListAPI

urlpatterns = [
    path("accounts/", CheckingAccountListAPI.as_view()),
    path("accounts/detail/", CheckingAccountDetailAPI.as_view()),
    #
    path("units/", CurrencyUnitsListAPI.as_view()),
    #
    path("adjustments/", AdjustmentListAPI.as_view()),
    path("adjustments/create/", AdjustmentCreateAPI.as_view()),
    path("adjustments/confirm/", AdjustmentConfirmAPI.as_view()),
    path("adjustments/reject/", AdjustmentRejectAPI.as_view()),
    #
    path("transfers/create/", TransferCreateAPI.as_view()),
    path("transfers/confirm/", TransferConfirmAPI.as_view()),
    path("transfers/reject/", TransferRejectAPI.as_view()),
    #
    path("exchanges/create/", ExchangeCreateAPI.as_view()),
    path("exchanges/confirm/", ExchangeConfirmAPI.as_view()),
    path("exchanges/reject/", ExchangeRejectAPI.as_view()),
]
