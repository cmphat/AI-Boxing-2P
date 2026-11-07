"""MediaPipe full-body motion controller for the first-person 3D mode.

A camera only estimates pose; it is not a real 6-DOF boxing tracker.
Coordinates are normalized by apparent shoulder width and damped with EMA.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import mediapipe as mp
import numpy as np

MODEL = Path(__file__).resolve().parents[1] / "assets" / "pose_landmarker_lite.task"
SHOULDERS = (11, 12)
ELBOWS = (13, 14)
WRISTS = (15, 16)
HIPS = (23, 24)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def angle(a, b, c):
    ba, bc = a-b, c-b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    return math.degrees(math.acos(clamp(float(np.dot(ba, bc) / denom), -1, 1))) if denom > 1e-8 else 0.0


@dataclass
class ArmState:
    last: np.ndarray | None = None
    filtered: np.ndarray | None = None
    armed: bool = True
    last_fire: float = -10.0
    peak: float = 0.0


@dataclass
class PlayerState:
    arms: list = field(default_factory=lambda: [ArmState(), ArmState()])
    smoothed_center: float | None = None
    last_seen: float = 0.0


class PoseControl:
    def __init__(self, sensitivity=1.0):
        if not MODEL.is_file():
            raise FileNotFoundError("Missing pose model. Run setup.bat (download_model.py) first.")
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=2,
            min_pose_detection_confidence=0.45,
            min_pose_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        self.engine = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.states = [PlayerState(), PlayerState()]
        self.sensitivity = float(sensitivity)
        self.ts = -1

    def close(self):
        self.engine.close()

    def _people(self, rgb, timestamp_ms):
        ts = max(timestamp_ms, self.ts + 1)
        dt = clamp((ts - self.ts)/1000 if self.ts >= 0 else 1/30, 0.008, 0.12)
        self.ts = ts
        res = self.engine.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), ts)
        out = []
        for item in res.pose_landmarks:
            pts = np.array([(p.x, p.y, p.z) for p in item], dtype=np.float32)
            vis = np.array([getattr(p, "visibility", 1.0) for p in item], dtype=np.float32)
            center = float(np.mean(pts[list(SHOULDERS), 0]))
            out.append((center, pts, vis))
        return sorted(out, key=lambda x: x[0]), dt

    def process(self, rgb, timestamp_ms, pvp=True):
        detected, dt = self._people(rgb, timestamp_ms)
        assigned = [None, None]
        if not pvp and detected:
            assigned[0] = min(detected, key=lambda x: abs(x[0] - 0.5))
        elif len(detected) >= 2:
            assigned[0], assigned[1] = detected[:2]
        elif len(detected) == 1:
            # Preserve left / right player zones to avoid a single person
            # randomly controlling both players when the other leaves the frame.
            assigned[0 if detected[0][0] < 0.5 else 1] = detected[0]

        now = time.monotonic()
        result = []
        for idx, item in enumerate(assigned):
            data = {"tracked": False, "guard": False, "punch": None,
                    "lean": 0.0, "head_y": 0.0, "speed": 0.0, "landmarks": None,
                    "visibility": None, "confidence": 0.0}
            state = self.states[idx]
            if item is None:
                if now - state.last_seen > 0.20:
                    for arm in state.arms:
                        arm.last = None
                        arm.filtered = None
                        arm.armed = True
                result.append(data)
                continue
            center, pts, vis = item
            state.last_seen = now
            data["tracked"] = True
            data["landmarks"] = pts
            data["visibility"] = vis
            data["confidence"] = float(np.mean(vis[[11,12,13,14,15,16]]))
            span = max(float(np.linalg.norm(pts[11,:2] - pts[12,:2])), 0.10)
            shoulder_mid = np.mean(pts[list(SHOULDERS), :2], axis=0)
            hip_mid = np.mean(pts[list(HIPS), :2], axis=0)
            data["lean"] = clamp(float((hip_mid[0] - shoulder_mid[0]) / span), -1.0, 1.0)
            data["head_y"] = clamp(float((shoulder_mid[1] - pts[0,1]) / span), -1.0, 1.0)

            # Guard: visible wrists near head/shoulders, rather than a gesture
            # that remains on after a hand disappears from the image.
            data["guard"] = bool(
                min(vis[15], vis[16], vis[11], vis[12]) >= 0.45
                and pts[15,1] < shoulder_mid[1] + 0.16*span
                and pts[16,1] < shoulder_mid[1] + 0.16*span
                and abs(float(pts[15,0] - pts[16,0])) < 2.2*span
            )

            for arm_idx, (s,e,w) in enumerate([(11,13,15),(12,14,16)]):
                arm = state.arms[arm_idx]
                if min(vis[s], vis[e], vis[w]) < 0.45:
                    arm.last = None
                    continue
                wrist = pts[w].copy()
                # Smaller smoothing on gesture detection retains rapid punches.
                arm.filtered = wrist if arm.filtered is None else (0.70*wrist + 0.30*arm.filtered)
                current = arm.filtered
                elbow = angle(pts[s], pts[e], pts[w])
                velocity = (current - arm.last) / dt if arm.last is not None else np.zeros(3)
                speed = float(np.linalg.norm(velocity[:2]) / span)
                forward = float(-velocity[2] / span)  # pose z is weak depth proxy
                data["speed"] = max(data["speed"], speed)
                if elbow < 122:
                    arm.armed = True
                if (arm.armed and now-arm.last_fire > 0.33
                        and elbow > 143
                        and (speed > 2.2/max(0.5,self.sensitivity)
                             or (forward > 1.2/max(0.5,self.sensitivity) and speed > 0.65))):
                    data["punch"] = "left" if arm_idx == 0 else "right"
                    arm.last_fire = now
                    arm.armed = False
                arm.last = current.copy()
            result.append(data)
        return result
