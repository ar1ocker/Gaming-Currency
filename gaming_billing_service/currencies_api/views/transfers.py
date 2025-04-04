from datetime import timedelta
from decimal import Decimal

from currencies.models import Holder, TransferRule, TransferTransaction
from currencies.permissions import TransfersPermissionsService
from currencies.services import AccountsService, TransfersService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class TransferCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        from_holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        to_holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        transfer_rule = serializers.SlugRelatedField(
            queryset=TransferRule.objects.select_related("unit").all(), slug_field="name"
        )
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        description = serializers.CharField()
        auto_reject_timeout = serializers.IntegerField(min_value=1, default=settings.DEFAULT_AUTO_REJECT_SECONDS)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField()
        status = serializers.CharField()
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from_holder: Holder = serializer.validated_data["from_holder_id"]  # type: ignore
        to_holder: Holder = serializer.validated_data["to_holder_id"]  # type: ignore
        transfer_rule: TransferRule = serializer.validated_data["transfer_rule"]  # type: ignore
        amount: Decimal = serializer.validated_data["amount"]  # type: ignore
        description: str = serializer.validated_data["description"]  # type: ignore
        auto_reject_timeout: int = serializer.validated_data["auto_reject_timeout"]  # type: ignore

        TransfersPermissionsService.enforce_create(permissions=service_auth.service.permissions)
        TransfersPermissionsService.enforce_auto_reject_timeout(
            permissions=service_auth.service.permissions, auto_reject=auto_reject_timeout
        )
        TransfersPermissionsService.enforce_amount(permissions=service_auth.service.permissions, amount=amount)

        from_account = AccountsService.get(holder=from_holder, currency_unit=transfer_rule.unit)
        if from_account is None:
            return Response(
                {
                    "error": (
                        f"Checking account for {from_holder.holder_id} with "
                        f"currency unit {transfer_rule.unit.symbol} not found"
                    )
                }
            )

        to_account = AccountsService.get(holder=to_holder, currency_unit=transfer_rule.unit)

        if to_account is None:
            return Response(
                {
                    "error": (
                        f"Checking account for {to_holder.holder_id} with "
                        f"currency unit {transfer_rule.unit.symbol} not found"
                    )
                }
            )

        transaction = TransfersService.create(
            service=service_auth.service,
            transfer_rule=transfer_rule,
            from_checking_account=from_account,
            to_checking_account=to_account,
            from_amount=amount,
            description=description,
            auto_reject_timedelta=timedelta(seconds=auto_reject_timeout),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(transaction).data)


class TransferConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=TransferTransaction.objects.select_related("service").all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer: TransferTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        TransfersPermissionsService.enforce_confirm(
            permissions=service_auth.service.permissions, service_name=transfer.service.name
        )

        TransfersService.confirm(
            transfer_transaction=transfer,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)


class TransferRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=TransferTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer: TransferTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        TransfersPermissionsService.enforce_reject(
            permissions=service_auth.service.permissions, service_name=transfer.service.name
        )

        TransfersService.reject(
            transfer_transaction=transfer,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)
