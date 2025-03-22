from currencies.models import Holder


class HoldersService:
    @classmethod
    def get_or_create(cls, *, holder_id: str) -> Holder:
        return Holder.objects.get_or_create(holder_id=holder_id, defaults={"enabled": True})[0]
