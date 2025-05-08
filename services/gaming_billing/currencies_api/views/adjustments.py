from datetime import timedelta
from decimal import Decimal

from currencies.models import AdjustmentTransaction, CurrencyUnit, Holder
from currencies.permissions import AdjustmentsPermissionsService
from currencies.services import AccountsService, AdjustmentsService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


class AdjustmentsCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.SlugRelatedField(queryset=Holder.objects.all(), slug_field="holder_id")
        unit_symbol = serializers.SlugRelatedField(queryset=CurrencyUnit.objects.all(), slug_field="symbol")
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

        holder: Holder = serializer.validated_data["holder_id"]  # type: ignore
        unit: CurrencyUnit = serializer.validated_data["unit_symbol"]  # type: ignore
        amount: Decimal = serializer.validated_data["amount"]  # type: ignore
        description: str = serializer.validated_data["description"]  # type: ignore
        auto_reject_timeout: int = serializer.validated_data["auto_reject_timeout"]  # type: ignore

        AdjustmentsPermissionsService.enforce_create(permissions=service_auth.service.permissions)
        AdjustmentsPermissionsService.enforce_auto_reject_timeout(
            permissions=service_auth.service.permissions, auto_reject=auto_reject_timeout
        )
        AdjustmentsPermissionsService.enforce_amount(permissions=service_auth.service.permissions, amount=amount)

        account = AccountsService.get(holder=holder, currency_unit=unit)
        if account is None:
            raise ValidationError("Account not found")

        adjustment = AdjustmentsService.create(
            service=service_auth.service,
            checking_account=account,
            amount=amount,
            description=description,
            auto_reject_timedelta=timedelta(seconds=auto_reject_timeout),
        )

        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(adjustment).data)


class AdjustmentsConfirmAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(
            queryset=AdjustmentTransaction.objects.select_related("service").all()
        )
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment: AdjustmentTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        AdjustmentsPermissionsService.enforce_confirm(
            permissions=service_auth.service.permissions, service_name=adjustment.service.name
        )

        AdjustmentsService.confirm(
            adjustment_transaction=adjustment,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)


class AdjustmentsRejectAPI(APIView):
    class InputSerializer(serializers.Serializer):
        uuid = serializers.PrimaryKeyRelatedField(
            queryset=AdjustmentTransaction.objects.select_related("service").all()
        )
        status_description = serializers.CharField()

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment: AdjustmentTransaction = serializer.validated_data["uuid"]  # type: ignore
        status_description: str = serializer.validated_data["status_description"]  # type: ignore

        AdjustmentsPermissionsService.enforce_reject(
            permissions=service_auth.service.permissions, service_name=adjustment.service.name
        )

        AdjustmentsService.reject(
            adjustment_transaction=adjustment,
            status_description=status_description,
        )

        return Response(status=status.HTTP_200_OK)


class AdjustmentsListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        pass

    class FilterSerializer(serializers.Serializer):
        service = serializers.CharField(required=False)
        status = serializers.CharField(required=False)
        created_at_after = serializers.DateTimeField(required=False)
        created_at_before = serializers.DateTimeField(required=False)
        closed_at_after = serializers.DateTimeField(required=False)
        closed_at_before = serializers.DateTimeField(required=False)

        holder = serializers.CharField(required=False)
        currency_unit = serializers.CharField(required=False)
        amount = serializers.DecimalField(max_digits=13, decimal_places=4, required=False)

        ordering = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        service = serializers.CharField(source="service.name")
        status = serializers.CharField()
        holder_id = serializers.CharField(source="checking_account.holder.holder_id")
        unit = serializers.CharField(source="checking_account.currency_unit.symbol")
        amount = serializers.DecimalField(max_digits=13, decimal_places=4)
        created_at = serializers.DateTimeField()
        closed_at = serializers.DateTimeField()
        auto_reject_after = serializers.DateTimeField()

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        AdjustmentsPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        adjustments = AdjustmentsService.list(
            filters=filter_serializer.validated_data,  # type: ignore
        ).select_related("service", "checking_account__holder", "checking_account__currency_unit")

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=adjustments,
            request=request,
            view=self,
        )
