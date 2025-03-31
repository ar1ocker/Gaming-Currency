from currencies.models import CurrencyUnit, HolderType
from currencies.permissions import AccountsPermissionsService, HoldersPermissionsService
from currencies.services import AccountsService, HoldersService, HoldersTypeService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
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

        create_if_not_exists: bool = serializer.validated_data["create_if_not_exists"]  # type: ignore
        holder_id: str = serializer.validated_data["holder_id"]  # type: ignore
        holder_type: HolderType = serializer.validated_data["holder_type"]  # type: ignore
        unit_symbol: CurrencyUnit = serializer.validated_data["unit_symbol"]  # type: ignore

        if create_if_not_exists:
            HoldersPermissionsService.enforce_create(permissions=service_auth.service.permissions)
            AccountsPermissionsService.enforce_create(permissions=service_auth.service.permissions)

            holder = HoldersService.get_or_create(holder_id=holder_id, holder_type=holder_type)
            account = AccountsService.get_or_create(holder=holder, currency_unit=unit_symbol)
        else:
            holder = HoldersService.get(holder_id=holder_id, holder_type=holder_type)

            if holder is None:
                return Response({"error": "Holder not found"}, status=status.HTTP_404_NOT_FOUND)

            account = AccountsService.get(holder=holder, currency_unit=unit_symbol)
            if account is None:
                return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.OutputSerializer(dict(account=account, holder=holder)).data)


class CheckingAccountListAPI(APIView):
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
