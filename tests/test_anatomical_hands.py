"""Checks that physical right wrist drives the game's right glove."""
import unittest

from solo3d.hands import ARMS, pose_hands, flip_world_controls


class AnatomicalHandsTests(unittest.TestCase):
    def sample(self):
        p=[[0.5,0.5,0.] for _ in range(33)]
        vis=[1.0]*33
        p[11]=[.65,.40,0.]
        p[12]=[.35,.40,0.]
        p[13]=[.70,.56,-.02]
        p[14]=[.30,.56,-.02]
        p[15]=[.75,.45,-.02]  # person's LEFT: image right
        p[16]=[.22,.20,-.30]  # person's RIGHT: image left and raised
        return p,vis

    def test_media_pipe_anatomy_indices(self):
        self.assertEqual(ARMS["left"],(11,13,15))
        self.assertEqual(ARMS["right"],(12,14,16))

    def test_right_wrist_moves_right_glove_only(self):
        p,vis=self.sample()
        baseline=pose_hands(p,vis)
        p[16]=[.10,.12,-.43]
        next_state=pose_hands(p,vis)
        self.assertEqual(baseline["left"],next_state["left"])
        self.assertNotEqual(baseline["right"],next_state["right"])
        self.assertGreater(next_state["right"][1],baseline["right"][1])
        self.assertGreater(next_state["right"][2],baseline["right"][2])

    def test_own_right_glove_remains_on_right_side(self):
        p,vis=self.sample()
        state=pose_hands(p,vis)
        self.assertGreater(state["right"][0],0.)
        self.assertLess(state["left"][0],0.)

    def test_missing_hand_does_not_swap_labels(self):
        p,vis=self.sample()
        vis[16]=.1
        hands=pose_hands(p,vis)
        self.assertIsNone(hands["right"])
        self.assertIsNotNone(hands["left"])

    def test_front_facing_camera_x_is_inverted_for_player(self):
        data=flip_world_controls({"x":-.8,"head_offset":-.2,"head_roll":-8.,"punch":"right"})
        self.assertEqual(data["x"],.8)
        self.assertEqual(data["head_offset"],.2)
        self.assertEqual(data["head_roll"],8.)
        self.assertEqual(data["punch"],"right")


if __name__=="__main__":
    unittest.main()
