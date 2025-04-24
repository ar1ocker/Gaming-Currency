from currencies.models import HolderType
from currencies.permissions import HoldersPermissionsService
from currencies.services import HoldersService, HoldersTypeService
from currencies_api.auth import hmac_service_auth
from currencies_api.models import CurrencyServiceAuth
from currencies_api.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HolderDetailAPI(APIView):
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


class HolderCreateAPI(APIView):
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

    @hmac_service_auth
    def post(self, request, service_auth: CurrencyServiceAuth):
        HoldersPermissionsService.enforce_create(permissions=service_auth.service.permissions)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holder_id = serializer.validated_data["holder_id"]  # type: ignore
        holder_type = serializer.validated_data["holder_type"]  # type: ignore
        info = serializer.validated_data["info"]  # type: ignore

        holder = HoldersService.get_or_create(holder_id=holder_id, holder_type=holder_type, info=info)[0]

        return Response(self.OutputSerializer(holder).data)


class HolderListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
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
        HoldersPermissionsService.enforce_create(permissions=service_auth.service.permissions)

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
