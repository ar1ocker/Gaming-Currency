from datetime import timedelta
from decimal import Decimal

from currencies.models import CurrencyUnit, ExchangeRule, ExchangeTransaction, Holder
from currencies.services import ExchangesService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import ServiceAuth
from currencies_api.services.permissions import ExchangesPermissionsService
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
        status = serializers.CharField()  # noqa: F811
        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        to_amount = serializers.DecimalField(max_digits=13, decimal_places=4)

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        ExchangesPermissionsService.enforce_create(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holder: Holder = serializer.validated_data["holder_id"]  # type: ignore
        exchange_rule: ExchangeRule = serializer.validated_data["exchange_rule"]  # type: ignore
        from_unit: CurrencyUnit = serializer.validated_data["from_unit"]  # type: ignore
        to_unit: CurrencyUnit = serializer.validated_data["to_unit"]  # type: ignore
        from_amount: Decimal = serializer.validated_data["from_amount"]  # type: ignore
        description: str = serializer.validated_data["description"]  # type: ignore
        auto_reject_timeout: int = serializer.validated_data["auto_reject_timeout"]  # type: ignore

        ExchangesPermissionsService.enforce_amount(permissions=service_auth.permissions, amount=from_amount)

        exchange = ExchangesService.create(
            service=service_auth.service,
            holder=holder,
            exchange_rule=exchange_rule,
            from_unit=from_unit,
            to_unit=to_unit,
            from_amount=from_amount,
            description=description,
            auto_reject_timedelta=timedelta(seconds=auto_reject_timeout),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(exchange).data)


class ExchangeConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=ExchangeTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        ExchangesPermissionsService.enforce_access(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exchange: ExchangeTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        ExchangesService.confirm(exchange_transaction=exchange, status_description=status_description)

        return Response(status=status.HTTP_200_OK)


class ExchangeRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=ExchangeTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        ExchangesPermissionsService.enforce_access(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exchange: ExchangeTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        ExchangesService.reject(exchange_transaction=exchange, status_description=status_description)

        return Response(status=status.HTTP_200_OK)
