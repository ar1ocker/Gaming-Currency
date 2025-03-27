from django.urls import path

from .views.accounts import CheckingAccountDetailAPI
from .views.adjustments import (
    AdjustmentConfirmAPI,
    AdjustmentCreateAPI,
    AdjustmentRejectAPI,
)
from .views.transfers import TransferConfirmAPI, TransferCreateAPI, TransferRejectAPI
from .views.units import CurrencyUnitsListAPI

urlpatterns = [
    path("accounts/", CheckingAccountDetailAPI.as_view()),
    path("units/", CurrencyUnitsListAPI.as_view()),
    path("adjustments/create/", AdjustmentCreateAPI.as_view()),
    path("adjustments/confirm/", AdjustmentConfirmAPI.as_view()),
    path("adjustments/reject/", AdjustmentRejectAPI.as_view()),
    path("transfers/create/", TransferCreateAPI.as_view()),
    path("transfers/confirm/", TransferConfirmAPI.as_view()),
    path("transfers/reject/", TransferRejectAPI.as_view()),
]
