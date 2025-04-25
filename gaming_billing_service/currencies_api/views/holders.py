from currencies.models import HolderType
from currencies.permissions import HoldersPermissionsService
from currencies.services import HoldersService, HoldersTypeService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HoldersDetailAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()

    class OutputSerializer(serializers.Serializer):
        enabled = serializers.BooleanField()
        holder_id = serializers.CharField()
        holder_type = serializers.CharField(source="holder_type.name")
        info = serializers.JSONField()
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        HoldersPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        holder_id = serializer.validated_data["holder_id"]  # type: ignore

        holder = HoldersService.get(holder_id=holder_id)

        if holder is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(self.OutputSerializer(holder).data)


class HoldersCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()
        holder_type = serializers.SlugRelatedField(
            queryset=HolderType.objects.all(), slug_field="name", default=HoldersTypeService.get_default
        )
        info = serializers.JSONField(default=dict)

    class OutputSerializer(serializers.Serializer):
        enabled = serializers.BooleanField()
        holder_id = serializers.CharField()
        holder_type = serializers.CharField(source="holder_type.name")
        info = serializers.JSONField()
        created_at = serializers.DateTimeField()
        created_now = serializers.BooleanField(source="_created_now")

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):
        HoldersPermissionsService.enforce_create(permissions=service_auth.service.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holder_id = serializer.validated_data["holder_id"]  # type: ignore
        holder_type = serializer.validated_data["holder_type"]  # type: ignore
        info = serializer.validated_data["info"]  # type: ignore

        holder, created_now = HoldersService.get_or_create(holder_id=holder_id, holder_type=holder_type, info=info)

        holder._created_now = created_now  # type: ignore

        return Response(self.OutputSerializer(holder).data, status=status.HTTP_201_CREATED)


class HoldersUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        holder_id = serializers.CharField()

    class UpdateDataSerializer(serializers.Serializer):
        enabled = serializers.BooleanField(required=False)
        info = serializers.JSONField(required=False)

    class OutputSerializer(serializers.Serializer):
        enabled = serializers.BooleanField()
        holder_id = serializers.CharField()
        holder_type = serializers.CharField(source="holder_type.name")
        info = serializers.JSONField()
        created_at = serializers.DateTimeField()
        updated_now = serializers.BooleanField(source="_updated_now")

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):
        input_serializer = self.InputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        holder_id = input_serializer.validated_data["holder_id"]  # type: ignore

        holder = HoldersService.get(holder_id=holder_id)

        if holder is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        parameter_serializer = self.UpdateDataSerializer(data=request.data)
        parameter_serializer.is_valid(raise_exception=True)

        updated_holder, updated_now = HoldersService.update(
            holder=holder,
            data=parameter_serializer.validated_data,  # type: ignore
        )

        updated_holder._updated_now = updated_now  # type: ignore

        return Response(self.OutputSerializer(updated_holder).data)


class HoldersListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        enabled = serializers.CharField(required=False)
        holder_type = serializers.CharField(required=False)
        created_at_after = serializers.DateTimeField(required=False)
        created_at_before = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.Serializer):
        enabled = serializers.BooleanField()
        holder_id = serializers.CharField()
        holder_type = serializers.CharField(source="holder_type.name")
        info = serializers.JSONField()
        created_at = serializers.DateTimeField()

    @hmac_service_auth
    def get(self, request, service_auth: CurrencyServiceAuth):
        HoldersPermissionsService.enforce_access(permissions=service_auth.service.permissions)

        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        holders = (
            HoldersService.list(
                filters=filter_serializer.validated_data,  # type: ignore
            )
            .select_related("holder_type")
            .order_by("-created_at")
        )

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=holders,
            request=request,
            view=self,
        )
