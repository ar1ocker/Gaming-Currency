from currencies.models import CurrencyUnit
from currencies.services import AccountsService, HoldersService, HoldersTypeService
from currencies_api.models import ServiceHMAC
from currencies_api.service_auth import hmac_service_auth
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class CheckingAccountDetailAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        create_if_not_exists = serializers.BooleanField(default=False)

    class OutputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        currency_unit = serializers.CharField(source="currency_unit.symbol")
        amount = serializers.IntegerField()
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def post(self, request, serviceHMAC: ServiceHMAC):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        holder = HoldersService.get(
            holder_id=serializer.validated_data["holder_id"], holder_type=HoldersTypeService.get_default()
        )

        return Response(
            self.OutputSerializer(
                AccountsService.get_or_create(holder=holder, currency_unit=serializer.validated_data["unit_symbol"])
            ).data
        )
