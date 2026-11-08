from collections import deque
from pathlib import Path
import math
import time

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


MODEL_PATH = Path(__file__).resolve().parent / "assets" / "pose_landmarker_lite.task"

# MediaPipe Pose indices
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

SKELETON = [
    (L_SHOULDER, R_SHOULDER),
    (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),
    (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
    (L_HIP, R_HIP),
]


def _dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _angle(a, b, c):
    ba = [a[i] - b[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    dot = sum(ba[i] * bc[i] for i in range(3))
    na = math.sqrt(sum(v * v for v in ba))
    nc = math.sqrt(sum(v * v for v in bc))
    if na < 1e-8 or nc < 1e-8:
        return 0.0
    v = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(v))


class Y8GestureEngine:
    """
    Pose -> boxing gestures.

    Stable design:
    - EMA smoothing for landmarks.
    - Arm state machine (armed -> strike -> re-arm).
    - Per-move cooldown.
    - Guard is held, punches are edge-triggered.
    - Dodge uses head/torso lateral lean with hysteresis.
    """

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Khong tim thay model: {MODEL_PATH}\n"
                "Hay chay: python download_model.py"
            )

        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.55,
            min_pose_presence_confidence=0.55,
            min_tracking_confidence=0.55,
            output_segmentation_masks=False,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)
        self.last_timestamp_ms = -1

        self.alpha = 0.48
        self.smooth = None
        self.prev = None
        self.prev_t = None

        self.arm_armed = {"left": True, "right": True}
        self.last_arm_fire = {"left": 0.0, "right": 0.0}
        self.arm_cooldown = 0.34

        self.dodge_armed = True
        self.last_dodge = 0.0
        self.dodge_cooldown = 0.55

        self.neutral_head_offset = 0.0
        self.neutral_ready = False
        self.neutral_samples = deque(maxlen=45)

        self.last_gesture = "IDLE"
        self.last_key = "-"
        self.pose_ok = False

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def recalibrate(self):
        self.neutral_samples.clear()
        self.neutral_ready = False
        self.neutral_head_offset = 0.0
        self.arm_armed = {"left": True, "right": True}
        self.dodge_armed = True

    def _landmarks(self, result):
        if not result.pose_landmarks:
            return None
        out = []
        for lm in result.pose_landmarks[0]:
            out.append([
                float(lm.x), float(lm.y), float(lm.z),
                float(getattr(lm, "visibility", 1.0) or 0.0),
            ])
        return out

    def _smooth_landmarks(self, raw):
        if self.smooth is None:
            self.smooth = [p[:] for p in raw]
            return self.smooth
        a = self.alpha
        for i, p in enumerate(raw):
            for j in range(3):
                self.smooth[i][j] = a * p[j] + (1.0 - a) * self.smooth[i][j]
            self.smooth[i][3] = p[3]
        return self.smooth

    def process(self, rgb_frame, timestamp_ms):
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1
        self.last_timestamp_ms = timestamp_ms

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        raw = self._landmarks(result)

        events = []
        state = {
            "guard": False,
            "pose_ok": False,
            "gesture": "NO POSE",
            "key": "-",
            "landmarks": None,
        }

        if raw is None:
            self.pose_ok = False
            self.prev = None
            self.prev_t = None
            return events, state

        lm = self._smooth_landmarks(raw)
        state["landmarks"] = lm

        important = [
            L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
            L_WRIST, R_WRIST, NOSE
        ]
        if min(lm[i][3] for i in important) < 0.35:
            self.pose_ok = False
            state["gesture"] = "SHOW ARMS"
            return events, state

        self.pose_ok = True
        state["pose_ok"] = True

        now = time.perf_counter()
        dt = 1 / 30
        if self.prev_t is not None:
            dt = max(0.008, min(0.10, now - self.prev_t))

        ls = lm[L_SHOULDER][:3]
        rs = lm[R_SHOULDER][:3]
        nose = lm[NOSE][:3]
        shoulder_width = max(0.055, _dist(ls, rs))
        shoulder_y = (ls[1] + rs[1]) / 2.0
        shoulder_x = (ls[0] + rs[0]) / 2.0

        # Guard: both wrists near face / upper chest.
        lw = lm[L_WRIST][:3]
        rw = lm[R_WRIST][:3]
        guard = (
            lw[1] < shoulder_y + 0.12 * shoulder_width
            and rw[1] < shoulder_y + 0.12 * shoulder_width
            and abs(lw[0] - nose[0]) < 1.65 * shoulder_width
            and abs(rw[0] - nose[0]) < 1.65 * shoulder_width
        )
        state["guard"] = bool(guard)

        # Neutral head position used for dodge detection.
        head_offset = (nose[0] - shoulder_x) / shoulder_width
        if not self.neutral_ready and not guard:
            self.neutral_samples.append(head_offset)
            if len(self.neutral_samples) >= 25:
                vals = sorted(self.neutral_samples)
                self.neutral_head_offset = vals[len(vals) // 2]
                self.neutral_ready = True
        elif self.neutral_ready and abs(head_offset - self.neutral_head_offset) < 0.12:
            self.neutral_head_offset = (
                0.985 * self.neutral_head_offset + 0.015 * head_offset
            )

        if self.neutral_ready:
            lean = head_offset - self.neutral_head_offset
            if abs(lean) < 0.14:
                self.dodge_armed = True
            if (
                self.dodge_armed
                and abs(lean) > 0.34
                and now - self.last_dodge > self.dodge_cooldown
                and not guard
            ):
                events.append(("DODGE", "d"))
                self.last_dodge = now
                self.dodge_armed = False

        if self.prev is not None and not guard:
            arms = {
                "left": (L_SHOULDER, L_ELBOW, L_WRIST),
                "right": (R_SHOULDER, R_ELBOW, R_WRIST),
            }

            for side, (si, ei, wi) in arms.items():
                s = lm[si][:3]
                e = lm[ei][:3]
                w = lm[wi][:3]
                p = self.prev[wi][:3]

                ang = _angle(s, e, w)
                prev_ang = _angle(
                    self.prev[si][:3],
                    self.prev[ei][:3],
                    self.prev[wi][:3],
                )

                vx = (w[0] - p[0]) / dt / shoulder_width
                vy = (w[1] - p[1]) / dt / shoulder_width
                vz = (w[2] - p[2]) / dt / shoulder_width
                speed = math.sqrt(vx * vx + vy * vy + 0.45 * vz * vz)

                # Re-arm only when the arm comes back/bends.
                if ang < 122.0 or _dist(s, w) < 1.35 * shoulder_width:
                    self.arm_armed[side] = True

                extended = ang > 146.0 and (ang - prev_ang) > 3.0
                fast = speed > 1.55

                if (
                    self.arm_armed[side]
                    and extended
                    and fast
                    and now - self.last_arm_fire[side] > self.arm_cooldown
                ):
                    # Classification from trajectory. Y grows downward.
                    if vy < -1.05 and abs(vy) > abs(vx) * 0.75:
                        action = f"{side.upper()} UPPERCUT"
                        key = "y" if side == "left" else "w"
                    elif abs(vx) > 1.45 and abs(vx) > abs(vy) * 1.15:
                        action = f"{side.upper()} HOOK"
                        key = "t" if side == "left" else "e"
                    elif vy > 0.90 and w[1] < shoulder_y:
                        action = f"{side.upper()} OVERHAND"
                        key = "i" if side == "left" else "u"
                    else:
                        action = f"{side.upper()} STRAIGHT"
                        # Game exposes Q/A as cross-punch aliases.
                        key = "q" if side == "left" else "a"

                    events.append((action, key))
                    self.arm_armed[side] = False
                    self.last_arm_fire[side] = now

        if guard:
            state["gesture"] = "BLOCK"
            state["key"] = "S"
        elif events:
            state["gesture"], state["key"] = events[-1][0], events[-1][1].upper()
            self.last_gesture = state["gesture"]
            self.last_key = state["key"]
        else:
            state["gesture"] = "READY" if self.neutral_ready else "CALIBRATING"
            state["key"] = "-"

        self.prev = [p[:] for p in lm]
        self.prev_t = now
        return events, state
