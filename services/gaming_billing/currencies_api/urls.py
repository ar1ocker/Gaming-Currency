from django.urls import path

from .views.accounts import (
    CheckingAccountsCreateAPI,
    CheckingAccountsDetailAPI,
    CheckingAccountsListAPI,
)
from .views.adjustments import (
    AdjustmentsConfirmAPI,
    AdjustmentsCreateAPI,
    AdjustmentsListAPI,
    AdjustmentsRejectAPI,
)
from .views.exchanges import (
    ExchangesConfirmAPI,
    ExchangesCreateAPI,
    ExchangesListAPI,
    ExchangesRejectAPI,
)
from .views.holders import (
    HoldersCreateAPI,
    HoldersDetailAPI,
    HoldersListAPI,
    HoldersUpdateAPI,
)
from .views.transfers import (
    TransfersConfirmAPI,
    TransfersCreateAPI,
    TransfersListAPI,
    TransfersRejectAPI,
)
from .views.units import CurrencyUnitsListAPI

urlpatterns = [
    path("holders/", HoldersListAPI.as_view(), name="holders_list"),
    path("holders/detail/", HoldersDetailAPI.as_view(), name="holders_detail"),
    path("holders/create/", HoldersCreateAPI.as_view(), name="holders_create"),
    path("holders/update/", HoldersUpdateAPI.as_view(), name="holders_update"),
    #
    path("accounts/", CheckingAccountsListAPI.as_view(), name="checking_accounts_list"),
    path("accounts/detail/", CheckingAccountsDetailAPI.as_view(), name="checking_accounts_detail"),
    path("accounts/create/", CheckingAccountsCreateAPI.as_view(), name="checking_accounts_create"),
    #
    path("units/", CurrencyUnitsListAPI.as_view(), name="currency_units_list"),
    #
    path("adjustments/", AdjustmentsListAPI.as_view(), name="adjustments_list"),
    path("adjustments/create/", AdjustmentsCreateAPI.as_view(), name="adjustments_create"),
    path("adjustments/confirm/", AdjustmentsConfirmAPI.as_view(), name="adjustments_confirm"),
    path("adjustments/reject/", AdjustmentsRejectAPI.as_view(), name="adjustments_reject"),
    #
    path("transfers/", TransfersListAPI.as_view(), name="transfers_list"),
    path("transfers/create/", TransfersCreateAPI.as_view(), name="transfers_create"),
    path("transfers/confirm/", TransfersConfirmAPI.as_view(), name="transfers_confirm"),
    path("transfers/reject/", TransfersRejectAPI.as_view(), name="transfers_reject"),
    #
    path("exchanges/", ExchangesListAPI.as_view(), name="exchanges_list"),
    path("exchanges/create/", ExchangesCreateAPI.as_view(), name="exchanges_create"),
    path("exchanges/confirm/", ExchangesConfirmAPI.as_view(), name="exchanges_confirm"),
    path("exchanges/reject/", ExchangesRejectAPI.as_view(), name="exchanges_reject"),
    #
]
