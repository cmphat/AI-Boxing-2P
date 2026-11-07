"""Game-logic tests; no camera, graphics context or MediaPipe required."""
import unittest
from solo3d.fight import Fight


class SoloFightTests(unittest.TestCase):
    def test_far_punch_does_not_damage_bot(self):
        f=Fight()
        f.player["z"]=3.2
        f.bot["z"]=-2.0
        self.assertFalse(f.user_attack())
        self.assertEqual(f.bot["hp"],100)
        self.assertEqual(f.misses,1)

    def test_close_punch_damages_bot(self):
        f=Fight()
        f.player["z"]=.8
        f.bot["z"]=-1.0
        self.assertTrue(f.user_attack("left"))
        self.assertEqual(f.bot["hp"],90)

    def test_guard_reduces_damage(self):
        f=Fight()
        f.player["z"]=.8
        f.bot["z"]=-1.
        f.bot["guard"]=True
        f.user_attack()
        self.assertEqual(f.bot["hp"],97)

    def test_keyboard_movement_changes_coordinates(self):
        f=Fight()
        z0=f.player["z"]
        f.update(.08,{},move=(0,-1))
        self.assertLess(f.player["z"],z0)

    def test_bot_chases_from_a_distance(self):
        f=Fight()
        z0=f.bot["z"]
        f.bot_cd=10
        f.update(.07,{},move=(0,0))
        self.assertGreater(f.bot["z"],z0)

    def test_game_timeout_finishes(self):
        f=Fight()
        f.seconds=.03
        f.bot_cd=10
        f.update(.07,{})
        self.assertEqual(f.finished,"DRAW")


if __name__=="__main__":
    unittest.main()
