from datetime import timedelta
from decimal import Decimal

from currencies.models import AdjustmentTransaction, CurrencyUnit, Holder
from currencies.services import AccountsService, AdjustmentsService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import ServiceAuth
from currencies_api.services import AdjustmentsPermissionsService
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class AdjustmentCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        description = serializers.CharField()
        auto_reject_timeout = serializers.IntegerField(min_value=1, default=settings.DEFAULT_AUTO_REJECT_TIMEOUT)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        AdjustmentsPermissionsService.enforce_create(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holder: Holder = serializer.validated_data["holder_id"]  # type: ignore
        unit: CurrencyUnit = serializer.validated_data["unit_symbol"]  # type: ignore
        amount: Decimal = serializer.validated_data["amount"]  # type: ignore
        description: str = serializer.validated_data["description"]  # type: ignore
        auto_reject_timeout: int = serializer.validated_data["auto_reject_timeout"]  # type: ignore

        AdjustmentsPermissionsService.enforce_amount(permissions=service_auth.permissions, amount=amount)

        account = AccountsService.get(holder=holder, currency_unit=unit)
        if account is None:
            return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

        adjustment = AdjustmentsService.create(
            service=service_auth.service,
            checking_account=account,
            amount=amount,
            description=description,
            auto_reject_timedelta=timedelta(seconds=auto_reject_timeout),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(adjustment).data)


class AdjustmentConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=AdjustmentTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        AdjustmentsPermissionsService.enforce_access(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment: AdjustmentTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        AdjustmentsService.confirm(
            adjustment_transaction=adjustment,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)


class AdjustmentRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=AdjustmentTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        AdjustmentsPermissionsService.enforce_access(permissions=service_auth.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment: AdjustmentTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        AdjustmentsService.reject(
            adjustment_transaction=adjustment,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)
