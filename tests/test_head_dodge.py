"""Regression tests for tilt geometry, FPS-independent smoothing, and dodge events."""
import math
import unittest

from solo3d.motion import smooth_value, deadband, HeadController
from solo3d.fight import Fight


class HeadMovementTests(unittest.TestCase):
    def test_same_smoothing_with_different_display_fps(self):
        x=0.
        for _ in range(60):
            x=smooth_value(x,1.,1/60,.10)
        y=0.
        for _ in range(30):
            y=smooth_value(y,1.,1/30,.10)
        self.assertAlmostEqual(x,y,places=5)

    def test_deadband_is_continuous(self):
        self.assertEqual(deadband(.1,.12),0)
        self.assertAlmostEqual(deadband(.20,.12),.08)
        self.assertAlmostEqual(deadband(-.20,.12),-.08)

    def test_calibrated_roll_and_shift(self):
        head=HeadController()
        head.update((1.0,0.0),.04)
        for _ in range(30):
            roll,shift=head.update((18.0,.7),1/60)
        self.assertGreater(roll,12.)
        self.assertGreater(shift,.20)
        self.assertLessEqual(roll,22.)

    def test_lost_tracking_returns_to_neutral(self):
        head=HeadController()
        head.update((0.,0.),.05)
        for _ in range(25):
            head.update((18.,.7),1/60)
        before=abs(head.roll)
        for _ in range(40):
            head.update(None,1/60)
        self.assertLess(abs(head.roll),before*.2)

    def test_dodge_negates_one_bot_hit(self):
        f=Fight("normal")
        f.player["z"]=.75
        f.bot["z"]=-.65
        f.bot_cd=0.
        # Seed randomness by replacing random.random for a deterministic hit.
        import random
        old=random.random
        try:
            random.random=lambda: .99
            f.update(.04,{"tracked":True,"x":0.0,"z":.75,
                          "head_roll":19.,"head_offset":.30})
        finally:
            random.random=old
        self.assertEqual(f.player["hp"],100)
        self.assertEqual(f.dodges,1)

    def test_no_tracking_cannot_dodge(self):
        f=Fight("normal")
        f.player["z"]=.75
        f.bot["z"]=-.65
        f.bot_cd=0.
        import random
        old=random.random
        try:
            random.random=lambda: .99
            f.update(.04,{"tracked":False,"head_roll":18.,"head_offset":.40})
        finally:
            random.random=old
        self.assertLess(f.player["hp"],100)


if __name__=="__main__":
    unittest.main()
