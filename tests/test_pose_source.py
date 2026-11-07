"""Regression: ensure the pose process no longer references undefined variables.

No webcam or MediaPipe installation needed: run from a GitHub Actions runner.
"""
import ast
import pathlib
import unittest


POSE_PATH = pathlib.Path(__file__).resolve().parents[1] / "solo3d" / "pose.py"


class PoseSourceSanityTests(unittest.TestCase):
    def test_wrist_velocity_uses_defined_shoulder_width(self):
        tree=ast.parse(POSE_PATH.read_text(encoding="utf-8"))
        clazz=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="SoloPose")
        process=next(n for n in clazz.body if isinstance(n,ast.FunctionDef) and n.name=="process")
        lines=POSE_PATH.read_text(encoding="utf-8").splitlines()
        assignments=[
            n.lineno for n in ast.walk(process)
            if isinstance(n,(ast.Assign,ast.AnnAssign)) and (
                any(isinstance(t,ast.Name) and t.id=="width" for t in n.targets)
                if isinstance(n,ast.Assign)
                else isinstance(n.target,ast.Name) and n.target.id=="width"
            )
        ]
        uses=[
            n.lineno for n in ast.walk(process)
            if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id=="width"
        ]
        self.assertTrue(uses, "Speed calculation should use a normalized width")
        self.assertTrue(assignments, "BUG: wrist speed referenced width before assignment")
        self.assertLess(min(assignments), min(uses),
                        "BUG: shoulder width must be assigned before use")

    def test_solo_pose_module_compiles(self):
        source=POSE_PATH.read_text(encoding="utf-8")
        compile(source,str(POSE_PATH),"exec")


if __name__ == "__main__":
    unittest.main()
