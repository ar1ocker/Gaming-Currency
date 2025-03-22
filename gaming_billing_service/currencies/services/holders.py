from currencies.models import Holder, HolderType


class HoldersService:
    @classmethod
    def get_or_create(cls, *, holder_id: str, holder_type: HolderType) -> Holder:
        return Holder.objects.get_or_create(
            holder_id=holder_id, defaults={"enabled": True, "holder_type": holder_type}
        )[0]

    @classmethod
    def get(cls, *, holder_id: str, holder_type: HolderType | None = None):
        try:
            if holder_type is None:
                return Holder.objects.get(holder_id=holder_id)
            else:
                return Holder.objects.get(holder_id=holder_id, holder_type=holder_type)
        except Holder.DoesNotExist:
            return None


class HoldersTypeService:
    @classmethod
    def get(cls, *, name: str):
        try:
            return HolderType.objects.get(name=name)
        except HolderType.DoesNotExist:
            return None

    @classmethod
    def get_default(cls):
        return HolderType.get_default()
