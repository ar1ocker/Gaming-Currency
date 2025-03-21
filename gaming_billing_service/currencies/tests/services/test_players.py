from currencies.services import PlayersService
from django.test import TestCase


class PlayerServicesTests(TestCase):
    def test_create_player(self):
        player = PlayersService.get_or_create(player_id="test")
        self.assertEqual(player.player_id, "test")

    def test_double_create_player(self):
        self.assertEqual(PlayersService.get_or_create(player_id="test"), PlayersService.get_or_create(player_id="test"))
