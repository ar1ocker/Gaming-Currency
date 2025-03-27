from currencies.models import CurrencyUnit, HolderType
from currencies.services import AccountsService, HoldersService, HoldersTypeService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import ServiceAuth
from currencies_api.services import (
    AccountsPermissionsService,
    HoldersPermissionsService,
)
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class CheckingAccountDetailAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        holder_type = serializers.SlugRelatedField(
            queryset=HolderType.objects.all(), slug_field="name", default=HoldersTypeService.get_default
        )
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        create_if_not_exists = serializers.BooleanField(default=False)

    class OutputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        currency_unit = serializers.CharField(source="currency_unit.symbol")
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def post(self, request, service_auth: ServiceAuth):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        create_if_not_exists: bool = serializer.validated_data["create_if_not_exists"]  # type: ignore
        holder_id: str = serializer.validated_data["holder_id"]  # type: ignore
        holder_type: HolderType = serializer.validated_data["holder_type"]  # type: ignore
        unit_symbol: CurrencyUnit = serializer.validated_data["unit_symbol"]  # type: ignore

        if create_if_not_exists:
            HoldersPermissionsService.enforce_create(permissions=service_auth.permissions)
            AccountsPermissionsService.enforce_create(permissions=service_auth.permissions)

            holder = HoldersService.get_or_create(holder_id=holder_id, holder_type=holder_type)
            account = AccountsService.get_or_create(holder=holder, currency_unit=unit_symbol)
        else:
            holder = HoldersService.get(holder_id=holder_id, holder_type=holder_type)

            if holder is None:
                return Response({"error": "Holder not found"}, status=status.HTTP_404_NOT_FOUND)

            account = AccountsService.get(holder=holder, currency_unit=unit_symbol)
            if account is None:
                return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.OutputSerializer(account).data)
