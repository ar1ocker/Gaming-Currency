from currencies.models import CurrencyUnit
from currencies.services import AccountsService, PlayersService
from currencies_api.models import ServiceHMAC
from currencies_api.service_auth import hmac_service_auth
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class CheckingAccountDetailAPI(APIView):
    class InputSerializer(serializers.Serializer):
        player_id = serializers.CharField()
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")

    class OutputSerializer(serializers.Serializer):
        player_id = serializers.CharField()
        currency_unit = serializers.CharField(source="currency_unit.symbol")
        amount = serializers.IntegerField()
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def post(self, request, serviceHMAC: ServiceHMAC):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        player = PlayersService.get_or_create(player_id=serializer.validated_data["player_id"])

        return Response(
            self.OutputSerializer(
                AccountsService.get_or_create(player=player, currency_unit=serializer.validated_data["unit_symbol"])
            ).data
        )
