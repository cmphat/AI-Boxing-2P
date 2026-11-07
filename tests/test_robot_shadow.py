"""Verify anatomical retargeting from pose landmarks to robot joints."""
import unittest

from solo3d.robot_rig import REST, BONES, retarget_pose, SmoothRobotPose


def template():
    pts=[[.5,.5,0.] for _ in range(33)]
    conf=[.95]*33
    pts[11]=[.62,.34,0.]
    pts[12]=[.38,.34,0.]
    pts[23]=[.57,.58,0.]
    pts[24]=[.43,.58,0.]
    pts[13]=[.72,.43,0.]
    pts[14]=[.28,.43,0.]
    pts[15]=[.78,.51,-.11]
    pts[16]=[.22,.51,-.11]
    pts[25]=[.57,.77,0.]
    pts[26]=[.43,.77,0.]
    pts[27]=[.56,.92,0.]
    pts[28]=[.44,.92,0.]
    pts[0]=[.5,.19,0.]
    return pts,conf


class RobotRigTests(unittest.TestCase):
    def test_all_joints_have_finite_coordinates(self):
        p,v=template()
        pose=retarget_pose(p,v)
        self.assertEqual(set(REST),set(pose))
        self.assertEqual(len(BONES),14)
        for point in pose.values():
            self.assertEqual(len(point),3)
            self.assertTrue(all(-2<=c<=4 for c in point))

    def test_physical_right_wrist_controls_robot_right_wrist_only(self):
        p,v=template()
        a=retarget_pose(p,v)
        p[16]=[.12,.32,-.33]  # Anatomical RIGHT wrist
        b=retarget_pose(p,v)
        self.assertNotEqual(a["right_wrist"],b["right_wrist"])
        self.assertEqual(a["left_wrist"],b["left_wrist"])
        self.assertGreater(b["right_wrist"][1],a["right_wrist"][1])

    def test_knee_bend_is_visible_in_robot(self):
        p,v=template()
        a=retarget_pose(p,v)
        p[26]=[.31,.61,.20]  # Bend anatomical RIGHT knee
        b=retarget_pose(p,v)
        self.assertNotEqual(a["right_knee"],b["right_knee"])
        self.assertEqual(a["left_knee"],b["left_knee"])

    def test_missing_limbs_fallback_instead_of_crashing(self):
        p,v=template()
        v[16]=0.
        pose=retarget_pose(p,v)
        self.assertEqual(pose["right_wrist"],REST["right_wrist"])

    def test_frametime_smoothing(self):
        s=SmoothRobotPose()
        target=dict(REST)
        target["right_elbow"]=(1.1,1.65,0.)
        before=s.joints["right_elbow"]
        out=s.update(target,1/60)
        self.assertGreater(out["right_elbow"][0],before[0])
        self.assertLess(out["right_elbow"][0],1.1)


if __name__=="__main__":
    unittest.main()
