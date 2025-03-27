from datetime import timedelta
from decimal import Decimal

from currencies.models import (
    CurrencyUnit,
    ExchangeRule,
    Holder,
    TransferRule,
    TransferTransaction,
)
from currencies.services import AccountsService, TransfersService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import ServiceAuth
from currencies_api.services.permissions import (
    ExchangesPermissionsService,
    TransfersPermissionsService,
)
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class ExchangeCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        exchange_rule = serializers.SlugRelatedField(queryset=ExchangeRule.objects.all(), slug_field="name")
        from_unit = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        to_unit = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        description = serializers.CharField()
        auto_reject_timeout = serializers.IntegerField(min_value=1, default=settings.DEFAULT_AUTO_REJECT_TIMEOUT)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        ExchangesPermissionsService.enforce_create(permissions=service_auth.permissions)
