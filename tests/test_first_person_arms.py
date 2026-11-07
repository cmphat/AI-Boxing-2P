"""Tests for first-person articulated arm retargeting."""
import unittest
from solo3d.hands import pose_arm_joints, arm_tracking_status


def pose():
    pts=[[.5,.5,0.] for _ in range(33)]
    vis=[.95]*33
    pts[11]=[.62,.34,0.]
    pts[12]=[.38,.34,0.]
    pts[13]=[.70,.48,0.]
    pts[14]=[.30,.48,0.]
    pts[15]=[.75,.55,-.1]
    pts[16]=[.25,.55,-.1]
    return pts,vis


class FirstPersonArmTests(unittest.TestCase):
    def test_returns_all_three_joints_for_both_arms(self):
        pts,vis=pose()
        arms=pose_arm_joints(pts,vis)
        self.assertEqual(set(arms),{"left","right"})
        for side in arms:
            self.assertEqual(set(arms[side]),{"shoulder","elbow","wrist"})

    def test_physical_right_arm_maps_to_screen_right(self):
        pts,vis=pose()
        arms=pose_arm_joints(pts,vis)
        self.assertGreater(arms["right"]["shoulder"][0],0)
        self.assertLess(arms["left"]["shoulder"][0],0)

    def test_right_elbow_bends_without_moving_left_arm(self):
        pts,vis=pose()
        a=pose_arm_joints(pts,vis)
        pts[14]=[.34,.62,.05]
        b=pose_arm_joints(pts,vis)
        self.assertNotEqual(a["right"]["elbow"],b["right"]["elbow"])
        self.assertEqual(a["left"],b["left"])

    def test_wrist_forward_extension_is_detected(self):
        pts,vis=pose()
        a=pose_arm_joints(pts,vis)
        pts[16]=[.25,.55,-.38]
        b=pose_arm_joints(pts,vis)
        self.assertGreater(b["right"]["wrist"][2],a["right"]["wrist"][2])


    def test_tracking_status_requires_elbow_and_wrist_visibility(self):
        pts,vis=pose()
        self.assertEqual(arm_tracking_status(pts,vis),{"left":True,"right":True})
        vis[16]=.1
        self.assertEqual(arm_tracking_status(pts,vis),{"left":True,"right":False})

    def test_camera_space_depth_is_bounded(self):
        pts,vis=pose()
        pts[16]=[.25,.55,-2.0]
        arms=pose_arm_joints(pts,vis)
        self.assertLessEqual(abs(arms["right"]["wrist"][2]),.16)

    def test_missing_right_wrist_does_not_swap_to_left(self):
        pts,vis=pose()
        vis[16]=.1
        arms=pose_arm_joints(pts,vis)
        self.assertNotIn("wrist",arms["right"])
        self.assertIn("wrist",arms["left"])


if __name__=="__main__":
    unittest.main()
