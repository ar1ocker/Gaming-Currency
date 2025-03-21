from currencies.models import CurrencyUnit
from currencies_api.service_auth import hmac_service_auth
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class CurrencyUnitsListAPI(APIView):
    class OutputSerializer(serializers.Serializer):
        symbol = serializers.CharField()
        measurement = serializers.CharField()

    @hmac_service_auth
    def get(self, request, serviceHMAC):
        return Response(self.OutputSerializer(CurrencyUnit.objects.all(), many=True).data)
