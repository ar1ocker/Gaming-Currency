from django.urls import path

from .views.accounts import CheckingAccountDetailAPI, CheckingAccountListAPI
from .views.adjustments import (
    AdjustmentConfirmAPI,
    AdjustmentCreateAPI,
    AdjustmentListAPI,
    AdjustmentRejectAPI,
)
from .views.exchanges import ExchangeConfirmAPI, ExchangeCreateAPI, ExchangeRejectAPI, ExchangesListAPI
from .views.holders import HolderCreateAPI, HolderDetailAPI, HolderListAPI
from .views.transfers import TransferConfirmAPI, TransferCreateAPI, TransferRejectAPI
from .views.units import CurrencyUnitsListAPI

urlpatterns = [
    path("holders/", HolderListAPI.as_view(), name="holders_list"),
    path("holders/detail/", HolderDetailAPI.as_view(), name="holders_detail"),
    path("holders/create/", HolderCreateAPI.as_view(), name="holders_create"),
    #
    path("accounts/", CheckingAccountListAPI.as_view(), name="checking_accounts_list"),
    path("accounts/detail/", CheckingAccountDetailAPI.as_view(), name="checking_accounts_detail"),
    #
    path("units/", CurrencyUnitsListAPI.as_view(), name="currency_units_list"),
    #
    path("adjustments/", AdjustmentListAPI.as_view(), name="adjustments_list"),
    path("adjustments/create/", AdjustmentCreateAPI.as_view(), name="adjustments_create"),
    path("adjustments/confirm/", AdjustmentConfirmAPI.as_view(), name="adjustments_confirm"),
    path("adjustments/reject/", AdjustmentRejectAPI.as_view(), name="adjustments_reject"),
    #
    path("transfers/create/", TransferCreateAPI.as_view(), name="transfers_create"),
    path("transfers/confirm/", TransferConfirmAPI.as_view(), name="transfers_confirm"),
    path("transfers/reject/", TransferRejectAPI.as_view(), name="transfers_reject"),
    #
    path("exchanges/", ExchangesListAPI.as_view(), name="exchanges_list"),
    path("exchanges/create/", ExchangeCreateAPI.as_view(), name="exchanges_create"),
    path("exchanges/confirm/", ExchangeConfirmAPI.as_view(), name="exchanges_confirm"),
    path("exchanges/reject/", ExchangeRejectAPI.as_view(), name="exchanges_reject"),
    #
]
