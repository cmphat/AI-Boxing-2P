import unittest
from fps3d.game import Match


class MatchTests(unittest.TestCase):
    def test_punch_hits(self):
        m = Match("pvp")
        self.assertTrue(m.punch(0, "right"))
        self.assertEqual(m.players[1]["health"], 90)
        self.assertEqual(m.players[0]["attack_arm"], "right")

    def test_guard_reduces_damage(self):
        m = Match("pvp")
        m.players[1]["guard"] = True
        m.punch(0)
        self.assertEqual(m.players[1]["health"], 98)

    def test_cooldown_prevents_rapid_repeats(self):
        m = Match("pvp")
        m.punch(0)
        self.assertFalse(m.punch(0))
        self.assertEqual(m.players[1]["health"], 90)

    def test_two_players_can_attack(self):
        m = Match("pvp")
        m.punch(0)
        m.punch(1)
        self.assertEqual([p["health"] for p in m.players], [90, 90])

    def test_time_limit(self):
        m = Match("pvp")
        m.seconds = 0.03
        m.players[0]["health"] = 60
        m.players[1]["health"] = 20
        m.update(0.07, [{},{}])
        self.assertEqual(m.finished, "PLAYER 1 WINS")

    def test_guard_resets_without_tracking(self):
        m = Match("pvp")
        m.players[0]["guard"] = True
        m.update(0.02,[{"tracked":False},{"tracked":False}])
        self.assertFalse(m.players[0]["guard"])

    def test_bot_mode(self):
        m = Match("pve")
        m.bot_timer=0.0
        m.update(0.05,[{},{}])
        self.assertLess(m.bot_timer, 3.5)


if __name__ == "__main__":
    unittest.main()
