from datetime import timedelta

from currencies.models import CurrencyTransaction, CurrencyUnit, Player
from currencies.services import AccountsService, TransfersService
from currencies_api.models import ServiceHMAC
from currencies_api.service_auth import hmac_service_auth
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class TransferCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        from_player_id = serializers.SlugRelatedField(queryset=Player.objects.all(), slug_field="player_id")
        to_player_id = serializers.SlugRelatedField(queryset=Player.objects.all(), slug_field="player_id")
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        amount = serializers.IntegerField()
        description = serializers.CharField()
        auto_reject_timeout = serializers.IntegerField(min_value=1, default=settings.DEFAULT_AUTO_REJECT_TIMEOUT)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField()

    @hmac_service_auth
    def post(self, request, serviceHMAC: ServiceHMAC):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from_account = AccountsService.get_or_create(
            player=serializer.validated_data["from_player_id"], currency_unit=serializer.validated_data["unit_symbol"]
        )

        to_account = AccountsService.get_or_create(
            player=serializer.validated_data["to_player_id"], currency_unit=serializer.validated_data["unit_symbol"]
        )

        transaction = TransfersService.create(
            service=serviceHMAC.service,
            from_checking_account=from_account,
            to_checking_account=to_account,
            amount=serializer.validated_data["amount"],
            description=serializer.validated_data["description"],
            auto_reject_timedelta=timedelta(seconds=serializer.validated_data["auto_reject_timeout"]),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(transaction).data)


class TransferConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=CurrencyTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, serviceHMAC: ServiceHMAC):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        TransfersService.confirm(
            transfer_transaction=serializer.validated_data["uuid"],
            status_description=serializer.validated_data["status_description"],
        )

        return Response(status=status.HTTP_200_OK)


class TransferRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=CurrencyTransaction.objects.all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, serviceHMAC: ServiceHMAC):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        TransfersService.reject(
            transfer_transaction=serializer.validated_data["uuid"],
            status_description=serializer.validated_data["status_description"],
        )

        return Response(status=status.HTTP_200_OK)
