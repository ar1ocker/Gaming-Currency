from datetime import timedelta
from decimal import Decimal

from currencies.models import CurrencyUnit, ExchangeRule, ExchangeTransaction, Holder
from currencies.permissions import ExchangesPermissionsService
from currencies.services import ExchangesService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class ExchangeCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        exchange_rule = serializers.SlugRelatedField(queryset=ExchangeRule.objects.all(), slug_field="name")
        from_unit = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        to_unit = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        description = serializers.CharField()
        auto_reject_timeout = serializers.IntegerField(min_value=1, default=settings.DEFAULT_AUTO_REJECT_SECONDS)

    class OutputSerializer(serializers.Serializer):
        uuid = serializers.UUIDField()
        status = serializers.CharField()  # noqa: F811
        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        to_amount = serializers.DecimalField(max_digits=13, decimal_places=4)

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holder: Holder = serializer.validated_data["holder_id"]  # type: ignore
        exchange_rule: ExchangeRule = serializer.validated_data["exchange_rule"]  # type: ignore
        from_unit: CurrencyUnit = serializer.validated_data["from_unit"]  # type: ignore
        to_unit: CurrencyUnit = serializer.validated_data["to_unit"]  # type: ignore
        from_amount: Decimal = serializer.validated_data["from_amount"]  # type: ignore
        description: str = serializer.validated_data["description"]  # type: ignore
        auto_reject_timeout: int = serializer.validated_data["auto_reject_timeout"]  # type: ignore

        ExchangesPermissionsService.enforce_create(permissions=service_auth.service.permissions)
        ExchangesPermissionsService.enforce_auto_reject_timeout(
            permissions=service_auth.service.permissions, auto_reject=auto_reject_timeout
        )
        ExchangesPermissionsService.enforce_amount(permissions=service_auth.service.permissions, amount=from_amount)

        exchange = ExchangesService.create(
            service=service_auth.service,
            holder=holder,
            exchange_rule=exchange_rule,
            from_unit=from_unit,
            to_unit=to_unit,
            from_amount=from_amount,
            description=description,
            auto_reject_timedelta=timedelta(seconds=auto_reject_timeout),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(exchange).data)


class ExchangeConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=ExchangeTransaction.objects.select_related("service").all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exchange: ExchangeTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        ExchangesPermissionsService.enforce_confirm(
            permissions=service_auth.service.permissions, service_name=exchange.service.name
        )

        ExchangesService.confirm(exchange_transaction=exchange, status_description=status_description)

        return Response(status=status.HTTP_200_OK)


class ExchangeRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(queryset=ExchangeTransaction.objects.select_related("service").all())
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exchange: ExchangeTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        ExchangesPermissionsService.enforce_reject(
            permissions=service_auth.service.permissions, service_name=exchange.service.name
        )

        ExchangesService.reject(exchange_transaction=exchange, status_description=status_description)

        return Response(status=status.HTTP_200_OK)


class ExchangesListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        pass

    class FilterSerializer(serializers.Serializer):
        service = serializers.CharField(required=False)
        status = serializers.CharField(required=False)
        holder = serializers.CharField(required=False)
        currency_unit = serializers.CharField(required=False)
        created_at_after = serializers.DateTimeField(required=False)
        created_at_before = serializers.DateTimeField(required=False)
        closed_at_after = serializers.DateTimeField(required=False)
        closed_at_before = serializers.DateTimeField(required=False)

        exchange_rule = serializers.CharField(required=False)

        exchange_rule_null = serializers.BooleanField(required=False)

        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4, required=False)
        to_amount = serializers.DecimalField(max_digits=13, decimal_places=4, required=False)
        from_unit = serializers.CharField(required=False)
        to_unit = serializers.CharField(required=False)

        ordering = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        service = serializers.CharField(source="service.name")
        status = serializers.CharField()
        holder_id = serializers.CharField(source="from_checking_account.holder.holder_id")
        created_at = serializers.DateTimeField()
        closed_at = serializers.DateTimeField()
        auto_reject_after = serializers.DateTimeField()

        exchange_rule = serializers.CharField(source="exchange_rule.name", default=None)

        from_unit = serializers.CharField(source="from_checking_account.currency_unit.symbol")
        to_unit = serializers.CharField(source="to_checking_account.currency_unit.symbol")
        from_amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        to_amount = serializers.DecimalField(max_digits=13, decimal_places=4)

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        ExchangesPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        exchanges = ExchangesService.list(
            filters=filter_serializer.validated_data,  # type: ignore
        ).select_related(
            "service",
            "from_checking_account__holder",
            "exchange_rule",
            "from_checking_account__currency_unit",
            "to_checking_account__currency_unit",
        )

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=exchanges,
            request=request,
            view=self,
        )
