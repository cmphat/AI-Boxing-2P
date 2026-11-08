# AI BOXING - Y8 CONTROLLER V2
# Standalone controller. No imports from the old Pygame game.
# Webcam -> MediaPipe Pose FULL -> 3D motion features -> gesture FSM -> Win32 SendInput.

import os
import sys
import time
import math
import shutil
import subprocess
import threading
from collections import deque
from pathlib import Path
from ctypes import wintypes

import ctypes
USER32 = ctypes.WinDLL("user32", use_last_error=True)
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
from pynput import keyboard as pynput_keyboard


# ------------------------- CONFIGURATION -------------------------

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "assets" / "pose_landmarker_full.task"
GAME_URL = "https://www.y8.com/games/punch_boxing_championship"

CAMERA_INDEX = 0
CAMERA_CAPTURE_W = 960
CAMERA_CAPTURE_H = 540

PANEL_W = 510
PANEL_H = 520
PREVIEW_W = 480
PREVIEW_H = 270

PUNCH_COOLDOWN = 0.34
PUNCH_REARM_ANGLE = 128.0
PUNCH_MIN_ANGLE = 142.0
MIN_LANDMARK_VISIBILITY = 0.48

# MediaPipe landmark IDs
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

POSE_CONNECTIONS = [
    (NOSE, 7), (NOSE, 8),
    (L_SHOULDER, R_SHOULDER),
    (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),
    (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
    (L_HIP, R_HIP),
]

# Game keys verified against the game's published controls:
# Q/A cross, W/Z right uppercut, Y left uppercut,
# E right hook, T left hook, U right overhand, I left overhand,
# D dodge, S block.


# ------------------------- WINDOWS WINDOW HELPERS -------------------------

def set_dpi_awareness():
    try:
        USER32.SetProcessDPIAware()
    except Exception:
        pass


set_dpi_awareness()


def get_screen_size():
    user32 = USER32
    return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))


def window_title(hwnd):
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 2)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def find_game_window():
    user32 = ctypes.windll.user32
    matches = []

    ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = window_title(hwnd).lower()
        if "punch boxing championship" in title or (
            "y8.com" in title and "boxing" in title
        ):
            matches.append(hwnd)
        return True

    callback = ENUMPROC(enum_callback)
    user32.EnumWindows(callback, 0)
    return matches[0] if matches else None


def find_browser():
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
    ]

    for name in ("msedge.exe", "chrome.exe", "msedge", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.insert(0, found)

    for path in candidates:
        if path and os.path.isfile(path):
            return path, "chromium"

    firefox = shutil.which("firefox.exe") or shutil.which("firefox")
    if firefox:
        return firefox, "firefox"

    raise RuntimeError(
        "Khong tim thay Edge, Chrome hoac Firefox. "
        "Hay cai Microsoft Edge hoac Chrome."
    )


def arrange_game_window(hwnd, screen_w, screen_h, panel_w):
    user32 = ctypes.windll.user32
    game_w = max(850, screen_w - panel_w - 16)
    game_h = max(600, screen_h - 48)

    SW_RESTORE = 9
    SWP_SHOWWINDOW = 0x0040
    SWP_NOZORDER = 0x0004

    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(
        hwnd, 0, 0, 0, game_w, game_h,
        SWP_SHOWWINDOW | SWP_NOZORDER
    )
    return game_w, game_h


def launch_or_find_game(screen_w, screen_h, panel_w, callback):
    """Run in a worker thread; locate the real Y8 top-level window and resize it."""
    try:
        hwnd = find_game_window()
        if hwnd is None:
            browser, kind = find_browser()

            if kind == "chromium":
                profile = os.path.join(
                    os.environ.get("LOCALAPPDATA", str(ROOT)),
                    "AIBoxing_Y8_Profile_V2"
                )
                os.makedirs(profile, exist_ok=True)
                args = [
                    browser,
                    f"--user-data-dir={profile}",
                    f"--app={GAME_URL}",
                    "--new-window",
                    "--no-first-run",
                    "--disable-features=TranslateUI",
                    "--autoplay-policy=no-user-gesture-required",
                    "--window-position=0,0",
                    f"--window-size={screen_w - panel_w - 16},{screen_h - 48}",
                ]
            else:
                args = [browser, "-new-window", GAME_URL]

            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )

            # Wait up to 30 seconds for the page title, not just process creation.
            deadline = time.time() + 30
            while time.time() < deadline:
                hwnd = find_game_window()
                if hwnd:
                    break
                time.sleep(0.25)

        if hwnd:
            game_size = arrange_game_window(hwnd, screen_w, screen_h, panel_w)
            callback(hwnd, game_size, None)
        else:
            callback(None, None, "Khong tim thay cua so game Y8. Hay mo game bang tay.")
    except Exception as exc:
        callback(None, None, str(exc))


# ------------------------- KEYBOARD OUTPUT -------------------------

ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", INPUT_UNION)]


# Declare pointer-sized Win32 signatures explicitly (important on 64-bit Windows).
USER32.SetProcessDPIAware.argtypes = []
USER32.SetProcessDPIAware.restype = wintypes.BOOL
USER32.GetSystemMetrics.argtypes = [ctypes.c_int]
USER32.GetSystemMetrics.restype = ctypes.c_int
USER32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
USER32.GetWindowTextLengthW.restype = ctypes.c_int
USER32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
USER32.GetWindowTextW.restype = ctypes.c_int
USER32.IsWindowVisible.argtypes = [wintypes.HWND]
USER32.IsWindowVisible.restype = wintypes.BOOL
USER32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
USER32.EnumWindows.restype = wintypes.BOOL
USER32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
USER32.ShowWindow.restype = wintypes.BOOL
USER32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT
]
USER32.SetWindowPos.restype = wintypes.BOOL
USER32.GetForegroundWindow.argtypes = []
USER32.GetForegroundWindow.restype = wintypes.HWND
USER32.SetForegroundWindow.argtypes = [wintypes.HWND]
USER32.SetForegroundWindow.restype = wintypes.BOOL
USER32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
USER32.SendInput.restype = wintypes.UINT


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002


class WindowsKeySender:
    """Use Win32 SendInput rather than pynput's high-level key wrapper."""

    def __init__(self, focus_check):
        self.focus_check = focus_check
        self.enabled = False
        self.held = set()
        self.lock = threading.RLock()
        self.release_timers = {}

    def _send(self, key, key_up=False):
        vk = ord(key.upper())
        flags = KEYEVENTF_KEYUP if key_up else 0
        packet = INPUT(
            type=INPUT_KEYBOARD,
            ii=INPUT_UNION(
                ki=KEYBDINPUT(
                    wVk=vk, wScan=0, dwFlags=flags,
                    time=0, dwExtraInfo=0
                )
            )
        )
        sent = USER32.SendInput(
            1, ctypes.byref(packet), ctypes.sizeof(INPUT)
        )
        return sent == 1

    def set_enabled(self, value):
        with self.lock:
            self.enabled = bool(value)
            if not self.enabled:
                self.release_all()

    def key_down(self, key, require_focus=True):
        with self.lock:
            if not self.enabled:
                return False
            if require_focus and not self.focus_check():
                return False
            key = key.lower()
            if key in self.held:
                return True
            ok = self._send(key, False)
            if ok:
                self.held.add(key)
            return ok

    def key_up(self, key):
        with self.lock:
            key = key.lower()
            if key in self.held:
                self._send(key, True)
                self.held.discard(key)
            timer = self.release_timers.pop(key, None)
            if timer:
                timer.cancel()

    def tap(self, key, duration=0.075, require_focus=True):
        with self.lock:
            if not self.enabled:
                return False
            if require_focus and not self.focus_check():
                return False

            key = key.lower()
            old_timer = self.release_timers.pop(key, None)
            if old_timer:
                old_timer.cancel()

            if key not in self.held:
                if not self._send(key, False):
                    return False
                self.held.add(key)

            timer = threading.Timer(duration, self.key_up, args=(key,))
            timer.daemon = True
            self.release_timers[key] = timer
            timer.start()
            return True

    def hold(self, key, active):
        if active:
            return self.key_down(key, require_focus=True)
        self.key_up(key)
        return True

    def release_all(self):
        with self.lock:
            for timer in list(self.release_timers.values()):
                timer.cancel()
            self.release_timers.clear()
            for key in list(self.held):
                self._send(key, True)
            self.held.clear()


# ------------------------- MEDIAPIPE POSE TRACKER -------------------------

def get_visibility(point):
    value = getattr(point, "visibility", None)
    if value is None:
        value = getattr(point, "presence", None)
    if value is None:
        return 1.0
    return float(value)


def pack_landmarks(points):
    packed = []
    for p in points:
        packed.append([
            float(p.x), float(p.y), float(p.z), get_visibility(p)
        ])
    return packed


class AsyncPoseTracker:
    """MediaPipe LIVE_STREAM: inference runs asynchronously to keep camera UI responsive."""

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Khong co model FULL: {MODEL_PATH}. Hay chay setup.bat."
            )

        self.lock = threading.Lock()
        self.latest_poses = []
        self.sequence = 0
        self.last_timestamp_ms = 0
        self.last_result_wall_time = 0.0

        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_poses=2,
            min_pose_detection_confidence=0.60,
            min_pose_presence_confidence=0.60,
            min_tracking_confidence=0.60,
            result_callback=self._on_result,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def _on_result(self, result, output_image, timestamp_ms):
        poses = []
        normalized = result.pose_landmarks or []
        world = result.pose_world_landmarks or []

        for index, norm_points in enumerate(normalized):
            norm_pack = pack_landmarks(norm_points)
            if index < len(world):
                world_pack = pack_landmarks(world[index])
            else:
                world_pack = [p[:] for p in norm_pack]
            poses.append((norm_pack, world_pack))

        with self.lock:
            self.latest_poses = poses
            self.sequence += 1
            self.last_timestamp_ms = timestamp_ms
            self.last_result_wall_time = time.perf_counter()

    def submit(self, rgb_frame):
        timestamp_ms = max(
            self.last_timestamp_ms + 1,
            int(time.perf_counter() * 1000)
        )
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        try:
            self.landmarker.detect_async(image, timestamp_ms)
        except ValueError:
            pass

    def get_latest(self):
        with self.lock:
            return self.sequence, self.latest_poses, self.last_result_wall_time

    def close(self):
        self.landmarker.close()


def select_primary_pose(poses, previous_center=None):
    """Prefer the largest, clearest, centrally located person in the camera frame."""
    best = None
    best_score = -1e9

    for norm, world in poses:
        required = [L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST]
        visibility = min(norm[i][3] for i in required)
        shoulder_width = abs(norm[L_SHOULDER][0] - norm[R_SHOULDER][0])
        center_x = (norm[L_SHOULDER][0] + norm[R_SHOULDER][0]) / 2.0

        score = shoulder_width * 3.0 + visibility
        if previous_center is not None:
            score -= abs(center_x - previous_center) * 0.8

        if score > best_score:
            best_score = score
            best = (norm, world, center_x)

    return best


# ------------------------- BOXING GESTURE RECOGNITION -------------------------

def point_distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )


def joint_angle(a, b, c):
    ba = [a[i] - b[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    dot = sum(ba[i] * bc[i] for i in range(3))
    na = math.sqrt(sum(v * v for v in ba))
    nc = math.sqrt(sum(v * v for v in bc))
    if na < 1e-7 or nc < 1e-7:
        return 0.0
    cosine = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(cosine))


class BoxingGestureEngine:
    """
    Motion-based gesture FSM:
    - coordinates are body-relative and normalized by shoulder width
    - velocities use a short temporal window, not one-frame pixel differences
    - each arm must retract before another punch can trigger
    """

    def __init__(self):
        self.histories = {
            "left": deque(maxlen=12),
            "right": deque(maxlen=12),
        }
        self.armed = {"left": True, "right": True}
        self.last_punch = {"left": 0.0, "right": 0.0}
        self.last_head_samples = deque(maxlen=30)
        self.neutral_head_x = None
        self.dodge_armed = True
        self.last_dodge = 0.0
        self.previous_center = None
        self.last_pose_time = 0.0
        self.last_action = "READY"
        self.last_key = "-"
        self.last_event_time = 0.0

    def recalibrate(self):
        self.last_head_samples.clear()
        self.neutral_head_x = None
        self.dodge_armed = True
        self.armed = {"left": True, "right": True}
        self.histories["left"].clear()
        self.histories["right"].clear()
        self.last_action = "CALIBRATING"

    def _choose_pose(self, poses):
        selected = select_primary_pose(poses, self.previous_center)
        if selected is None:
            return None
        norm, world, center = selected
        self.previous_center = center
        return norm, world

    def update(self, poses, timestamp_ms):
        now = timestamp_ms / 1000.0
        selected = self._choose_pose(poses)

        if selected is None:
            if time.perf_counter() - self.last_pose_time > 0.35:
                self.last_action = "NO PERSON"
                self.last_key = "-"
            return [], {
                "pose_ok": False, "guard": False,
                "action": self.last_action, "key": self.last_key,
                "norm": None, "world": None, "quality": "NO PERSON",
                "angles": {}, "velocities": {}
            }

        norm, world = selected
        self.last_pose_time = time.perf_counter()

        required = [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST]
        min_vis = min(norm[i][3] for i in required)
        shoulder_width_px = abs(norm[L_SHOULDER][0] - norm[R_SHOULDER][0])
        left_wrist, right_wrist = norm[L_WRIST], norm[R_WRIST]

        if min_vis < MIN_LANDMARK_VISIBILITY:
            return [], {
                "pose_ok": False, "guard": False,
                "action": "SHOW BOTH ARMS", "key": "-",
                "norm": norm, "world": world,
                "quality": "LOW VISIBILITY - SHOW SHOULDERS, ELBOWS, WRISTS",
                "angles": {}, "velocities": {}
            }

        if shoulder_width_px > 0.48:
            quality = "STEP BACK - CAMERA TOO CLOSE"
        elif shoulder_width_px < 0.11:
            quality = "MOVE CLOSER TO CAMERA"
        elif (
            min(left_wrist[0], right_wrist[0]) < 0.015
            or max(left_wrist[0], right_wrist[0]) > 0.985
            or min(left_wrist[1], right_wrist[1]) < 0.02
            or max(left_wrist[1], right_wrist[1]) > 0.98
        ):
            quality = "KEEP BOTH HANDS INSIDE FRAME"
        else:
            quality = "GOOD FRAMING - READY"

        ls_n, rs_n = norm[L_SHOULDER], norm[R_SHOULDER]
        ls_w, rs_w = world[L_SHOULDER], world[R_SHOULDER]
        shoulder_mid_x = (ls_n[0] + rs_n[0]) / 2.0
        shoulder_mid_y = (ls_n[1] + rs_n[1]) / 2.0
        shoulder_scale = max(0.08, abs(ls_n[0] - rs_n[0]))
        world_scale = max(0.08, point_distance(ls_w[:3], rs_w[:3]))
        nose = norm[NOSE]

        # Guard: both fists are held near the head, above shoulder line.
        guard = (
            left_wrist[1] < nose[1] + 0.18 * shoulder_scale
            and right_wrist[1] < nose[1] + 0.18 * shoulder_scale
            and abs(left_wrist[0] - nose[0]) < 1.10 * shoulder_scale
            and abs(right_wrist[0] - nose[0]) < 1.10 * shoulder_scale
        )

        events = []
        angles = {}
        velocities = {}

        # Calibrate neutral head position after the player is detected.
        head_rel_x = (nose[0] - shoulder_mid_x) / shoulder_scale
        if self.neutral_head_x is None:
            if not guard:
                self.last_head_samples.append(head_rel_x)
            if len(self.last_head_samples) >= 24:
                values = sorted(self.last_head_samples)
                self.neutral_head_x = values[len(values) // 2]
        else:
            lean = head_rel_x - self.neutral_head_x
            if abs(lean) < 0.16:
                self.dodge_armed = True
            if (
                not guard and self.dodge_armed and abs(lean) > 0.34
                and now - self.last_dodge > 0.72
            ):
                events.append(("DODGE", "d"))
                self.last_dodge = now
                self.dodge_armed = False

        arm_defs = {
            "left": (L_SHOULDER, L_ELBOW, L_WRIST, "q", "y", "t", "i"),
            "right": (R_SHOULDER, R_ELBOW, R_WRIST, "a", "w", "e", "u"),
        }

        if not guard:
            for side, (si, ei, wi, cross_key, upper_key, hook_key, over_key) in arm_defs.items():
                s_n, e_n, w_n = norm[si], norm[ei], norm[wi]
                s_w, e_w, w_w = world[si], world[ei], world[wi]

                angle = joint_angle(s_w[:3], e_w[:3], w_w[:3])
                rel_x = (w_n[0] - shoulder_mid_x) / shoulder_scale
                rel_y = (w_n[1] - shoulder_mid_y) / shoulder_scale
                rel_z = (w_w[2] - s_w[2]) / world_scale

                sample = (now, rel_x, rel_y, rel_z, angle)
                history = self.histories[side]
                history.append(sample)

                eligible = [candidate for candidate in history if 0.075 <= now - candidate[0] <= 0.19]
                old = min(eligible, key=lambda candidate: abs((now - candidate[0]) - 0.12)) if eligible else None

                if old is None:
                    angles[side] = angle
                    velocities[side] = (0.0, 0.0, 0.0)
                    continue

                dt = max(0.035, now - old[0])
                vx = (rel_x - old[1]) / dt
                vy = (rel_y - old[2]) / dt
                vz = (rel_z - old[3]) / dt
                forward_speed = -vz  # smaller MediaPipe z means closer to camera
                speed_2d = math.hypot(vx, vy)
                angle_delta = angle - old[4]
                inward_speed = -math.copysign(1.0, old[1] if abs(old[1]) > 0.05 else rel_x) * vx

                angles[side] = angle
                velocities[side] = (round(vx, 2), round(vy, 2), round(forward_speed, 2))

                # Re-arm only after the hand has clearly retracted.
                shoulder_to_wrist = math.hypot(
                    (w_n[0] - s_n[0]) / shoulder_scale,
                    (w_n[1] - s_n[1]) / shoulder_scale
                )
                if angle < PUNCH_REARM_ANGLE or shoulder_to_wrist < 1.05:
                    self.armed[side] = True

                if (
                    not self.armed[side]
                    or now - self.last_punch[side] < PUNCH_COOLDOWN
                ):
                    continue

                action = None
                key = None

                # Uppercut: fist travels upward quickly with a bent-to-extending arm.
                if vy < -1.05 and speed_2d > 1.25 and angle > 105 and angle_delta > 2:
                    action, key = f"{side.upper()} UPPERCUT", upper_key

                # Overhand: fist starts above shoulder and arcs down while advancing.
                elif (
                    vy > 0.95 and forward_speed > 0.12
                    and old[2] < 0.05 and angle > 112
                ):
                    action, key = f"{side.upper()} OVERHAND", over_key

                # Hook: bent arm sweeps inward across the body.
                elif (
                    inward_speed > 1.05 and speed_2d > 1.20
                    and 72 < angle < 148
                ):
                    action, key = f"{side.upper()} HOOK", hook_key

                # Cross/straight: elbow extends while the fist moves toward the camera.
                elif (
                    angle > PUNCH_MIN_ANGLE and angle_delta > 7
                    and forward_speed > 0.32
                ):
                    action, key = f"{side.upper()} CROSS", cross_key

                # Straight punch: depth movement is the primary cue.
                elif (
                    angle > 138 and forward_speed > 0.38
                    and speed_2d > 0.65
                ):
                    action, key = f"{side.upper()} CROSS", cross_key

                # Fallback for a fast full extension when depth estimation is noisy.
                elif (
                    angle > 153 and angle_delta > 12
                    and speed_2d > 1.35
                ):
                    action, key = f"{side.upper()} CROSS", cross_key

                if action:
                    events.append((action, key))
                    self.armed[side] = False
                    self.last_punch[side] = now

        if events:
            self.last_action, self.last_key = events[-1]
            self.last_event_time = now
        elif guard:
            self.last_action, self.last_key = "BLOCK", "s"
        elif now - self.last_event_time > 0.30:
            self.last_action, self.last_key = "READY", "-"

        return events, {
            "pose_ok": True,
            "guard": bool(guard),
            "action": self.last_action,
            "key": self.last_key,
            "norm": norm,
            "world": world,
            "quality": quality,
            "angles": angles,
            "velocities": velocities,
        }


# ------------------------- CAMERA + UI -------------------------

class BoxingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI BOXING - POSE CONTROLLER V2")
        self.root.configure(bg="#111827")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.screen_w, self.screen_h = get_screen_size()
        self.panel_w = min(PANEL_W, max(430, int(self.screen_w * 0.28)))
        self.panel_h = PANEL_H

        panel_x = self.screen_w - self.panel_w - 8
        self.root.geometry(f"{self.panel_w}x{self.panel_h}+{panel_x}+35")

        self.running = True
        self.control_enabled = False
        self.game_hwnd = None
        self.game_status = "OPENING Y8 GAME..."
        self.last_pose_seq = -1
        self.latest_norm = None
        self.latest_state = {
            "pose_ok": False, "guard": False,
            "action": "WAITING FOR CAMERA", "key": "-",
            "norm": None, "quality": "INITIALIZING",
            "angles": {}, "velocities": {}
        }
        self.fps = 0.0
        self.last_frame_time = time.perf_counter()
        self.last_submit_time = 0.0

        self._build_ui()
        self._open_camera()

        self.pose_tracker = AsyncPoseTracker()
        self.gesture_engine = BoxingGestureEngine()
        self.keys = WindowsKeySender(self.is_game_focused)

        self.hotkey_listener = pynput_keyboard.Listener(on_press=self._on_hotkey)
        self.hotkey_listener.start()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        threading.Thread(
            target=launch_or_find_game,
            args=(
                self.screen_w, self.screen_h, self.panel_w,
                self._game_window_callback
            ),
            daemon=True
        ).start()

        self.root.after(15, self.update_frame)

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#111827")
        header.pack(fill="x", padx=12, pady=(9, 4))

        tk.Label(
            header, text="AI BOXING - POSE V2",
            font=("Segoe UI", 13, "bold"),
            fg="#F9FAFB", bg="#111827"
        ).pack(side="left")

        self.control_label = tk.Label(
            header, text="CONTROL OFF",
            font=("Segoe UI", 9, "bold"),
            fg="#FBBF24", bg="#111827"
        )
        self.control_label.pack(side="right")

        self.image_label = tk.Label(self.root, bg="#020617", bd=0)
        self.image_label.pack(padx=12, pady=4)

        self.quality_label = tk.Label(
            self.root, text="CAMERA: CHECKING...",
            font=("Segoe UI", 9, "bold"),
            fg="#93C5FD", bg="#111827"
        )
        self.quality_label.pack(fill="x", padx=12, pady=(3, 1))

        self.action_label = tk.Label(
            self.root, text="POSE: WAITING | ACTION: - | KEY: -",
            font=("Segoe UI", 9, "bold"),
            fg="#E5E7EB", bg="#111827"
        )
        self.action_label.pack(fill="x", padx=12, pady=2)

        self.metrics_label = tk.Label(
            self.root, text="ELBOW: L -- | R --    WRIST SPEED: L -- | R --",
            font=("Consolas", 8),
            fg="#93C5FD", bg="#111827"
        )
        self.metrics_label.pack(fill="x", padx=12, pady=(0, 2))

        self.game_label = tk.Label(
            self.root, text="GAME: OPENING...",
            font=("Segoe UI", 8),
            fg="#FBBF24", bg="#111827"
        )
        self.game_label.pack(fill="x", padx=12, pady=2)

        buttons = tk.Frame(self.root, bg="#111827")
        buttons.pack(fill="x", padx=12, pady=(6, 3))

        self.toggle_button = tk.Button(
            buttons, text="BAT DIEU KHIEN (F8)",
            command=self.toggle_control,
            bg="#166534", fg="white",
            activebackground="#15803D", activeforeground="white",
            relief="flat", font=("Segoe UI", 9, "bold"),
            padx=7, pady=7
        )
        self.toggle_button.pack(side="left", expand=True, fill="x", padx=(0, 4))

        tk.Button(
            buttons, text="CAN CHINH (F9)",
            command=self.recalibrate,
            bg="#334155", fg="white",
            activebackground="#475569", activeforeground="white",
            relief="flat", font=("Segoe UI", 9, "bold"),
            padx=7, pady=7
        ).pack(side="left", expand=True, fill="x", padx=4)

        tk.Button(
            buttons, text="TEST Q (F7)",
            command=lambda: self.test_key("q"),
            bg="#1D4ED8", fg="white",
            activebackground="#2563EB", activeforeground="white",
            relief="flat", font=("Segoe UI", 9, "bold"),
            padx=7, pady=7
        ).pack(side="left", expand=True, fill="x", padx=4)

        tk.Button(
            buttons, text="THOAT (F10)",
            command=self.close,
            bg="#7F1D1D", fg="white",
            activebackground="#991B1B", activeforeground="white",
            relief="flat", font=("Segoe UI", 9, "bold"),
            padx=7, pady=7
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        tk.Label(
            self.root,
            text="Dat camera thay dau -> eo -> hai co tay. Chi 1 nguoi trong khung.",
            font=("Segoe UI", 8), fg="#CBD5E1", bg="#111827"
        ).pack(fill="x", padx=12, pady=(5, 2))

        tk.Label(
            self.root,
            text="F7 test phim Q | F8 bat/tat | F9 can chinh | F10 thoat",
            font=("Segoe UI", 8), fg="#94A3B8", bg="#111827"
        ).pack(fill="x", padx=12, pady=(0, 7))

    def _open_camera(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(CAMERA_INDEX)

        if not self.cap.isOpened():
            raise RuntimeError(
                "Khong mo duoc webcam. Dong Camera/Zoom/Teams hoac doi CAMERA_INDEX = 1."
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CAPTURE_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CAPTURE_H)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _game_window_callback(self, hwnd, game_size, error):
        def apply():
            if not self.running:
                return
            if hwnd:
                self.game_hwnd = hwnd
                self.game_status = "Y8 WINDOW FOUND - CLICK GAME TO PLAY"
                self.game_label.config(text=self.game_status, fg="#4ADE80")
            else:
                self.game_status = "GAME WINDOW NOT FOUND"
                self.game_label.config(text=self.game_status, fg="#F87171")
                if error:
                    self.quality_label.config(text="GAME: " + error, fg="#F87171")
        try:
            self.root.after(0, apply)
        except Exception:
            pass

    def is_game_focused(self):
        if not self.game_hwnd:
            return False
        foreground = USER32.GetForegroundWindow()
        if foreground == self.game_hwnd:
            return True
        title = window_title(foreground).lower()
        return "punch boxing championship" in title or (
            "y8.com" in title and "boxing" in title
        )

    def focus_game(self):
        if not self.game_hwnd:
            return False
        user32 = ctypes.windll.user32
        user32.ShowWindow(self.game_hwnd, 9)
        user32.SetForegroundWindow(self.game_hwnd)
        return self.is_game_focused()

    def _on_hotkey(self, key):
        if key == pynput_keyboard.Key.f7:
            self.root.after(0, lambda: self.test_key("q"))
        elif key == pynput_keyboard.Key.f8:
            self.root.after(0, self.toggle_control)
        elif key == pynput_keyboard.Key.f9:
            self.root.after(0, self.recalibrate)
        elif key == pynput_keyboard.Key.f10:
            self.root.after(0, self.close)

    def toggle_control(self):
        self.control_enabled = not self.control_enabled
        self.keys.set_enabled(self.control_enabled)

        if self.control_enabled:
            self.control_label.config(text="CONTROL ON", fg="#4ADE80")
            self.toggle_button.config(text="TAT DIEU KHIEN (F8)", bg="#991B1B")
            self.root.after(180, self.focus_game)
        else:
            self.control_label.config(text="CONTROL OFF", fg="#FBBF24")
            self.toggle_button.config(text="BAT DIEU KHIEN (F8)", bg="#166534")

    def recalibrate(self):
        self.gesture_engine.recalibrate()
        self.quality_label.config(
            text="CALIBRATING: DUNG THANG, HAI TAY THA LONG TRONG 1 GIAY",
            fg="#93C5FD"
        )

    def test_key(self, key):
        if not self.game_hwnd:
            self.game_label.config(text="GAME WINDOW NOT FOUND - OPEN Y8 MANUALLY", fg="#F87171")
            return

        self.focus_game()

        def send_test():
            if not self.is_game_focused():
                self.game_label.config(text="TEST FAILED: CLICK THE GAME WINDOW FIRST", fg="#F87171")
                return
            was_enabled = self.keys.enabled
            if not was_enabled:
                self.keys.set_enabled(True)
            sent = self.keys.tap(key, duration=0.11, require_focus=True)
            self.action_label.config(text=f"KEY TEST {key.upper()}: {'SENT' if sent else 'FAILED'}")
            if not was_enabled:
                self.root.after(180, lambda: self.keys.set_enabled(False))

        self.root.after(250, send_test)

    def _draw_skeleton(self, frame, norm):
        h, w = frame.shape[:2]

        def point(index):
            return (
                int((1.0 - norm[index][0]) * w),
                int(norm[index][1] * h)
            )

        for a, b in POSE_CONNECTIONS:
            if norm[a][3] >= 0.30 and norm[b][3] >= 0.30:
                cv2.line(frame, point(a), point(b), (60, 230, 130), 3, cv2.LINE_AA)

        for index in [
            NOSE, L_SHOULDER, R_SHOULDER,
            L_ELBOW, R_ELBOW, L_WRIST, R_WRIST,
            L_HIP, R_HIP
        ]:
            if norm[index][3] >= 0.30:
                cv2.circle(frame, point(index), 6, (0, 220, 255), -1, cv2.LINE_AA)

    def _draw_overlay(self, frame, state):
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (8, 8), (w - 8, 62), (15, 23, 42), -1)

        control_text = "CONTROL ON" if self.control_enabled else "CONTROL OFF"
        control_color = (70, 230, 110) if self.control_enabled else (0, 180, 255)
        cv2.putText(
            frame, control_text, (18, 31),
            cv2.FONT_HERSHEY_SIMPLEX, 0.62, control_color, 2, cv2.LINE_AA
        )

        pose_text = "POSE OK" if state.get("pose_ok") else "POSE LOST"
        cv2.putText(
            frame, pose_text, (18, 54),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 240, 240), 1, cv2.LINE_AA
        )

        # Framing guide: hands and shoulders should stay inside this area.
        cv2.rectangle(frame, (int(w * 0.08), int(h * 0.10)),
                      (int(w * 0.92), int(h * 0.96)), (90, 130, 180), 1)

    def update_frame(self):
        if not self.running:
            return

        ok, frame = self.cap.read()
        if ok:
            frame = cv2.resize(
                frame, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA
            )
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            now = time.perf_counter()
            if now - self.last_submit_time >= 1.0 / 30.0:
                self.pose_tracker.submit(rgb)
                self.last_submit_time = now

            seq, poses, result_time = self.pose_tracker.get_latest()
            if seq != self.last_pose_seq:
                self.last_pose_seq = seq
                timestamp_ms = int(result_time * 1000) if result_time else int(now * 1000)
                events, state = self.gesture_engine.update(poses, timestamp_ms)
                self.latest_state = state
                self.latest_norm = state.get("norm")

                if self.control_enabled:
                    if self.is_game_focused():
                        self.keys.hold("s", state.get("guard", False))
                        if not state.get("guard", False):
                            for action, key in events:
                                self.keys.tap(key)
                    else:
                        self.keys.hold("s", False)

            dt = max(0.001, now - self.last_frame_time)
            self.last_frame_time = now
            instant_fps = 1.0 / dt
            self.fps = instant_fps if self.fps == 0 else 0.82 * self.fps + 0.18 * instant_fps

            preview = cv2.flip(frame, 1)
            if self.latest_norm is not None:
                self._draw_skeleton(preview, self.latest_norm)
            self._draw_overlay(preview, self.latest_state)

            rgb_preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_preview)
            photo = ImageTk.PhotoImage(image=image)
            self.image_label.configure(image=photo, width=PREVIEW_W, height=PREVIEW_H)
            self.image_label.image = photo

            quality = self.latest_state.get("quality", "WAITING FOR POSE")
            self.quality_label.config(
                text=f"CAMERA: {quality} | {self.fps:.0f} FPS",
                fg="#4ADE80" if "GOOD" in quality else "#FBBF24"
            )

            action = self.latest_state.get("action", "READY")
            key = self.latest_state.get("key", "-")
            pose_status = "POSE OK" if self.latest_state.get("pose_ok") else "POSE LOST"

            if self.control_enabled and not self.is_game_focused():
                focus_text = " | CLICK GAME - NO KEY SENT"
                self.game_label.config(text="GAME: CLICK GAME WINDOW TO FOCUS", fg="#FBBF24")
            else:
                focus_text = ""
                if self.game_hwnd:
                    self.game_label.config(text="GAME: WINDOW FOUND", fg="#4ADE80")

            self.action_label.config(
                text=f"{pose_status} | {action} | KEY {key}{focus_text}"
            )

            angles = self.latest_state.get("angles", {})
            velocities = self.latest_state.get("velocities", {})
            left_angle = angles.get("left")
            right_angle = angles.get("right")
            left_vel = velocities.get("left", (0.0, 0.0, 0.0))
            right_vel = velocities.get("right", (0.0, 0.0, 0.0))
            if left_angle is None:
                metric_text = "ELBOW: L -- | R --    WRIST SPEED: waiting..."
            else:
                metric_text = (
                    f"ELBOW L {left_angle:.0f}  R {(right_angle or 0):.0f} deg"
                    f" | FWD L {left_vel[2]:.1f} R {right_vel[2]:.1f}"
                )
            self.metrics_label.config(text=metric_text)

        self.root.after(15, self.update_frame)

    def close(self):
        if not self.running:
            return
        self.running = False

        try:
            self.keys.release_all()
        except Exception:
            pass

        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
        except Exception:
            pass

        try:
            self.pose_tracker.close()
        except Exception:
            pass

        try:
            self.cap.release()
        except Exception:
            pass

        self.root.destroy()


def main():
    app = None
    try:
        app = BoxingApp()
        app.root.mainloop()
        return 0
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        try:
            messagebox.showerror("AI Boxing - Startup Error", str(exc))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
