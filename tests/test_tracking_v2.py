"""Synthetic regression tests for the user's specific movement failures."""
import unittest

from solo3d.tracking import RelativeMovement, body_measure


class TrackingV2Tests(unittest.TestCase):
    def test_calibrates_in_twelve_frames(self):
        t=RelativeMovement(12)
        for _ in range(11):
            r=t.update((.5,.2,.95),1/30)
            self.assertFalse(r["calibrated"])
        r=t.update((.5,.2,.95),1/30)
        self.assertTrue(r["calibrated"])
        self.assertEqual(r["calibration"],100)

    def test_lateral_movement_changes_x(self):
        t=RelativeMovement(3)
        for _ in range(3):
            t.update((.5,.2,.98),1/30)
        for _ in range(20):
            r=t.update((.58,.2,.98),1/30)
        self.assertGreater(r["x"],.45)

    def test_forward_and_backward_change_z(self):
        t=RelativeMovement(3)
        for _ in range(3):t.update((.5,.2,.98),1/30)
        z0=t.output(True)["z"]
        for _ in range(30):
            near=t.update((.5,.26,.98),1/30)
        self.assertLess(near["z"],z0-.8)
        for _ in range(55):
            far=t.update((.5,.15,.98),1/30)
        self.assertGreater(far["z"],z0+.7)

    def test_shoulders_work_without_visible_hips(self):
        points=[[.5,.5,0.] for _ in range(33)]
        points[11]=[.40,.35,0.]
        points[12]=[.60,.35,0.]
        vis=[0.0]*33
        vis[11]=.95
        vis[12]=.9
        result=body_measure(points,vis)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0],.5,places=3)
        self.assertGreater(result[1],.19)

    def test_recalibration_returns_neutral(self):
        t=RelativeMovement(3)
        for _ in range(3):t.update((.5,.2,.95),1/30)
        for _ in range(20):r=t.update((.65,.27,.95),1/30)
        self.assertGreater(r["x"],.5)
        t.reset()
        for _ in range(3):
            r=t.update((.65,.27,.95),1/30)
        self.assertTrue(r["calibrated"])
        self.assertAlmostEqual(r["x"],0.)

    def test_missing_measurement_does_not_wipe_position(self):
        t=RelativeMovement(3)
        for _ in range(3):t.update((.5,.2,.95),1/30)
        for _ in range(15):r=t.update((.60,.21,.95),1/30)
        r2=t.update(None,1/30)
        self.assertFalse(r2["tracked"])
        self.assertEqual(r["x"],r2["x"])


if __name__=="__main__":
    unittest.main()
