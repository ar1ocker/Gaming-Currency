from currencies.models import CurrencyUnit
from currencies.permissions import CurrencyUnitsPermissionsService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework import serializers
from rest_framework.views import APIView


class CurrencyUnitsListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        pass

    class OutputSerializer(serializers.Serializer):
        symbol = serializers.CharField()
        measurement = serializers.CharField()

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):

        CurrencyUnitsPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        units = CurrencyUnit.objects.all()

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=units,
            request=request,
            view=self,
        )
