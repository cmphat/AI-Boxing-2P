from pathlib import Path
import math
import time

import mediapipe as mp


MODEL_PATH = Path(__file__).resolve().parent / "assets" / "pose_landmarker_lite.task"


def angle_at_joint(a, b, c):
    """Return angle A-B-C at elbow, in degrees."""
    ba = [a[i] - b[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    dot = sum(ba[i] * bc[i] for i in range(3))
    na = math.sqrt(sum(v * v for v in ba))
    nc = math.sqrt(sum(v * v for v in bc))
    if na < 1e-8 or nc < 1e-8:
        return 0.0
    cosine = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(cosine))


def distance3(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


class PoseTracker:
    """Track up to two people and recognize simple boxing gestures."""

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Khong tim thay model: {MODEL_PATH}\n"
                "Hay chay setup.bat hoac python download_model.py."
            )

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=2,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.last_timestamp_ms = -1
        self.previous_wrists = [[None, None], [None, None]]
        self.armed = [[True, True], [True, True]]
        self.last_punch_time = [0.0, 0.0]

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def process(self, rgb_frame, timestamp_ms, single_player=False):
        """Return [P1, P2] pose data and gesture dictionaries.

        In PvE, the only detected person is always assigned to Player 1.
        In PvP, people are assigned from left to right.
        """
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        if self.last_timestamp_ms < 0:
            dt = 1.0 / 30.0
        else:
            dt = max(0.005, min(0.15, (timestamp_ms - self.last_timestamp_ms) / 1000.0))
        self.last_timestamp_ms = timestamp_ms

        detected = []
        for pose in result.pose_landmarks or []:
            landmarks = []
            for lm in pose:
                landmarks.append({
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "visibility": float(getattr(lm, "visibility", 1.0) or 0.0),
                })
            center_x = (landmarks[11]["x"] + landmarks[12]["x"]) / 2.0
            detected.append({"landmarks": landmarks, "center_x": center_x})

        detected.sort(key=lambda item: item["center_x"])
        people = [None, None]

        if len(detected) >= 2:
            people[0], people[1] = detected[0], detected[1]
        elif len(detected) == 1:
            if single_player:
                people[0] = detected[0]
            else:
                slot = 0 if detected[0]["center_x"] < 0.5 else 1
                people[slot] = detected[0]

        gestures = [
            {"punch": False, "guard": False, "tracked": False},
            {"punch": False, "guard": False, "tracked": False},
        ]
        now = time.perf_counter()

        for player_index, person in enumerate(people):
            if person is None:
                self.previous_wrists[player_index] = [None, None]
                self.armed[player_index] = [True, True]
                continue

            lm = person["landmarks"]
            gestures[player_index]["tracked"] = True

            shoulder_y = (lm[11]["y"] + lm[12]["y"]) / 2.0
            left_wrist, right_wrist = lm[15], lm[16]
            wrists_visible = (
                left_wrist["visibility"] > 0.35
                and right_wrist["visibility"] > 0.35
            )
            gestures[player_index]["guard"] = bool(
                wrists_visible
                and left_wrist["y"] < shoulder_y + 0.02
                and right_wrist["y"] < shoulder_y + 0.02
            )

            arms = [(11, 13, 15), (12, 14, 16)]
            punch_detected = False

            for arm_index, (shoulder_i, elbow_i, wrist_i) in enumerate(arms):
                shoulder, elbow, wrist = lm[shoulder_i], lm[elbow_i], lm[wrist_i]
                if min(shoulder["visibility"], elbow["visibility"], wrist["visibility"]) < 0.35:
                    self.previous_wrists[player_index][arm_index] = None
                    continue

                a = (shoulder["x"], shoulder["y"], shoulder["z"])
                b = (elbow["x"], elbow["y"], elbow["z"])
                c = (wrist["x"], wrist["y"], wrist["z"])
                elbow_angle = angle_at_joint(a, b, c)

                previous = self.previous_wrists[player_index][arm_index]
                wrist_speed = distance3(c, previous) / dt if previous is not None else 0.0

                if elbow_angle < 125.0:
                    self.armed[player_index][arm_index] = True

                if (
                    self.armed[player_index][arm_index]
                    and elbow_angle > 148.0
                    and wrist_speed > 0.55
                    and now - self.last_punch_time[player_index] > 0.42
                ):
                    punch_detected = True
                    self.armed[player_index][arm_index] = False
                    self.last_punch_time[player_index] = now

                self.previous_wrists[player_index][arm_index] = c

            gestures[player_index]["punch"] = punch_detected

        return people, gestures
