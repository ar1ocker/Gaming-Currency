from currencies.models import Player


class PlayersService:
    @classmethod
    def get_or_create(cls, *, player_id: str) -> Player:
        return Player.objects.get_or_create(player_id=player_id)[0]
