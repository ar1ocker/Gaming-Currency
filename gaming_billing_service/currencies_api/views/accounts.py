from currencies.models import CurrencyUnit, HolderType
from currencies.permissions import AccountsPermissionsService
from currencies.services import AccountsService, HoldersService, HoldersTypeService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class CheckingAccountsDetailAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        holder_type = serializers.SlugRelatedField(
            queryset=HolderType.objects.all(), slug_field="name", default=HoldersTypeService.get_default
        )
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")

    class OutputSerializer(serializers.Serializer):
        holder_enabled = serializers.BooleanField(source="holder.enabled")
        holder_id = serializers.CharField(source="holder.holder_id")
        holder_type = serializers.CharField(source="holder.holder_type.name")
        currency_unit = serializers.CharField(source="account.currency_unit.symbol")
        amount = serializers.DecimalField(max_digits=13, decimal_places=4, source="account.amount")
        created_at = serializers.DateTimeField(source="account.created_at")

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        AccountsPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        holder_id: str = serializer.validated_data["holder_id"]  # type: ignore
        holder_type: HolderType = serializer.validated_data["holder_type"]  # type: ignore
        currency_unit: CurrencyUnit = serializer.validated_data["unit_symbol"]  # type: ignore

        holder = HoldersService.get(holder_id=holder_id, holder_type=holder_type)

        if holder is None:
            raise Http404("Holder not found")

        account = AccountsService.get(holder=holder, currency_unit=currency_unit)

        if account is None:
            raise Http404("Account not found")

        return Response(self.OutputSerializer(dict(account=account, holder=holder)).data)


class CheckingAccountsListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        holder_type = serializers.CharField(required=False)
        holder_id = serializers.CharField(required=False)
        currency_unit = serializers.CharField(required=False)
        amount_min = serializers.IntegerField(required=False)
        amount_max = serializers.IntegerField(required=False)
        created_at_after = serializers.DateField(required=False)
        created_at_before = serializers.DateField(required=False)

    class OutputSerializer(serializers.Serializer):
        holder_enabled = serializers.BooleanField(source="holder.enabled")
        holder_id = serializers.CharField(source="holder.holder_id")
        holder_type = serializers.CharField(source="holder.holder_type.name")
        currency_unit = serializers.CharField(source="currency_unit.symbol")
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        AccountsPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        accounts = (
            AccountsService.list(
                filters=filter_serializer.validated_data,  # type: ignore
            )
            .select_related("holder__holder_type", "currency_unit")
            .order_by("-created_at")
        )

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=accounts,
            request=request,
            view=self,
        )
