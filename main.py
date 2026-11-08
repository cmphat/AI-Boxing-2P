# AI BOXING - Y8 CONTROLLER
# Self-contained replacement. Does NOT import the old Pygame game modules.

import os
import sys
import time
import math
import shutil
import subprocess
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from pynput import keyboard as pynput_keyboard
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "assets" / "pose_landmarker_lite.task"
GAME_URL = "https://www.y8.com/games/punch_boxing_championship"

CAMERA_INDEX = 0
CAMERA_W = 640
CAMERA_H = 360
CAMERA_PANEL_W = 460
CAMERA_PANEL_H = 390

NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16

POSE_LINES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW), (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, 23), (RIGHT_SHOULDER, 24), (23, 24),
]


def distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def angle_3d(a, b, c):
    ba = [a[i] - b[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    dot = sum(ba[i] * bc[i] for i in range(3))
    na = math.sqrt(sum(v * v for v in ba))
    nc = math.sqrt(sum(v * v for v in bc))
    if na < 1e-8 or nc < 1e-8:
        return 0.0
    value = max(-1.0, min(1.0, dot / (na * nc)))
    return math.degrees(math.acos(value))


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
        "Hay cai Microsoft Edge hoac Chrome roi chay lai."
    )


def launch_game_window(screen_w, screen_h, camera_w):
    browser, kind = find_browser()
    gap = 12
    game_w = max(1024, screen_w - camera_w - gap)
    if game_w + camera_w + gap > screen_w:
        game_w = screen_w - camera_w - gap
    game_h = max(620, screen_h - 45)

    if kind == "chromium":
        profile = os.path.join(
            os.environ.get("LOCALAPPDATA", str(ROOT)),
            "AIBoxing_Y8_App_Profile"
        )
        os.makedirs(profile, exist_ok=True)
        args = [
            browser,
            f"--user-data-dir={profile}",
            f"--app={GAME_URL}",
            "--new-window",
            "--no-first-run",
            "--disable-infobars",
            "--disable-features=TranslateUI",
            "--autoplay-policy=no-user-gesture-required",
            "--window-position=0,0",
            f"--window-size={game_w},{game_h}",
        ]
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        label = "Edge/Chrome App"
    else:
        args = [
            browser, "-new-window",
            f"--width={game_w}", f"--height={game_h}", GAME_URL
        ]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        label = "Firefox window"

    return game_w, game_h, label


class PoseBoxingController:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "Khong tim thay model MediaPipe: " + str(MODEL_PATH) +
                ". Hay chay setup.bat."
            )

        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.55,
            min_pose_presence_confidence=0.55,
            min_tracking_confidence=0.55,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)
        self.smoothed = None
        self.previous = None
        self.previous_time = None
        self.last_timestamp_ms = 0
        self.alpha = 0.58

        self.armed = {"left": True, "right": True}
        self.last_punch = {"left": 0.0, "right": 0.0}
        self.punch_cooldown = 0.38

        self.neutral_samples = []
        self.neutral_head_x = None
        self.dodge_armed = True
        self.last_dodge = 0.0
        self.dodge_cooldown = 0.70

    def close(self):
        self.landmarker.close()

    def recalibrate(self):
        self.neutral_samples.clear()
        self.neutral_head_x = None
        self.dodge_armed = True
        self.armed = {"left": True, "right": True}

    def _smooth(self, raw):
        if self.smoothed is None:
            self.smoothed = [p[:] for p in raw]
        else:
            a = self.alpha
            for i, point in enumerate(raw):
                for j in range(3):
                    self.smoothed[i][j] = a * point[j] + (1.0 - a) * self.smoothed[i][j]
                self.smoothed[i][3] = point[3]
        return self.smoothed

    def process(self, rgb):
        now = time.perf_counter()
        timestamp_ms = max(self.last_timestamp_ms + 1, int(now * 1000))
        self.last_timestamp_ms = timestamp_ms

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.pose_landmarks:
            self.previous = None
            self.previous_time = None
            return [], {
                "pose_ok": False, "guard": False,
                "gesture": "NO PERSON", "key": "-", "landmarks": None
            }

        raw = []
        for point in result.pose_landmarks[0]:
            raw.append([
                float(point.x), float(point.y), float(point.z),
                float(getattr(point, "visibility", 1.0) or 0.0)
            ])

        lm = self._smooth(raw)
        important = [
            NOSE, LEFT_SHOULDER, RIGHT_SHOULDER,
            LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST
        ]
        if min(lm[i][3] for i in important) < 0.35:
            self.previous = [p[:] for p in lm]
            self.previous_time = now
            return [], {
                "pose_ok": False, "guard": False,
                "gesture": "SHOW BOTH ARMS", "key": "-", "landmarks": lm
            }

        ls = lm[LEFT_SHOULDER][:3]
        rs = lm[RIGHT_SHOULDER][:3]
        nose = lm[NOSE][:3]
        shoulder_width = max(0.06, distance(ls, rs))
        shoulder_y = (ls[1] + rs[1]) / 2.0
        shoulder_x = (ls[0] + rs[0]) / 2.0
        lw = lm[LEFT_WRIST][:3]
        rw = lm[RIGHT_WRIST][:3]

        guard = (
            lw[1] < shoulder_y + 0.18 * shoulder_width
            and rw[1] < shoulder_y + 0.18 * shoulder_width
            and abs(lw[0] - nose[0]) < 1.55 * shoulder_width
            and abs(rw[0] - nose[0]) < 1.55 * shoulder_width
        )

        events = []
        dt = 1.0 / 30.0 if self.previous_time is None else max(
            0.012, min(0.12, now - self.previous_time)
        )

        head_offset = (nose[0] - shoulder_x) / shoulder_width
        if self.neutral_head_x is None:
            self.neutral_samples.append(head_offset)
            if len(self.neutral_samples) >= 24:
                values = sorted(self.neutral_samples)
                self.neutral_head_x = values[len(values) // 2]
        elif not guard and abs(head_offset - self.neutral_head_x) < 0.12:
            self.neutral_head_x = 0.99 * self.neutral_head_x + 0.01 * head_offset

        if self.neutral_head_x is not None:
            lean = head_offset - self.neutral_head_x
            if abs(lean) < 0.15:
                self.dodge_armed = True
            if (
                self.dodge_armed and abs(lean) > 0.36
                and now - self.last_dodge >= self.dodge_cooldown
                and not guard
            ):
                events.append(("DODGE", "d"))
                self.last_dodge = now
                self.dodge_armed = False

        if self.previous is not None and not guard:
            arms = {
                "left": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST),
                "right": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST),
            }
            for side, (si, ei, wi) in arms.items():
                s, e, w = lm[si][:3], lm[ei][:3], lm[wi][:3]
                ps, pe, pw = (
                    self.previous[si][:3],
                    self.previous[ei][:3],
                    self.previous[wi][:3],
                )
                current_angle = angle_3d(s, e, w)
                previous_angle = angle_3d(ps, pe, pw)

                vx = (w[0] - pw[0]) / dt / shoulder_width
                vy = (w[1] - pw[1]) / dt / shoulder_width
                vz = (w[2] - pw[2]) / dt / shoulder_width
                speed = math.sqrt(vx * vx + vy * vy + 0.55 * vz * vz)

                if current_angle < 128.0 or distance(s, w) < 1.30 * shoulder_width:
                    self.armed[side] = True

                extended = current_angle > 143.0 and current_angle > previous_angle + 1.0
                fast = speed > 1.35

                if (
                    self.armed[side] and extended and fast
                    and now - self.last_punch[side] >= self.punch_cooldown
                ):
                    if vy < -0.80 and abs(vy) > abs(vx) * 0.80:
                        action, key = f"{side.upper()} UPPERCUT", ("y" if side == "left" else "w")
                    elif abs(vx) > 1.05 and abs(vx) > abs(vy) * 1.20:
                        action, key = f"{side.upper()} HOOK", ("t" if side == "left" else "e")
                    elif vy > 0.85:
                        action, key = f"{side.upper()} OVERHAND", ("i" if side == "left" else "u")
                    else:
                        action, key = f"{side.upper()} CROSS", ("q" if side == "left" else "a")

                    events.append((action, key))
                    self.armed[side] = False
                    self.last_punch[side] = now

        self.previous = [p[:] for p in lm]
        self.previous_time = now

        if guard:
            gesture, key = "BLOCK", "S"
        elif events:
            gesture, key = events[-1][0], events[-1][1].upper()
        elif self.neutral_head_x is None:
            gesture, key = "CALIBRATING", "-"
        else:
            gesture, key = "READY", "-"

        return events, {
            "pose_ok": True, "guard": bool(guard),
            "gesture": gesture, "key": key, "landmarks": lm
        }


class KeyboardOutput:
    def __init__(self):
        self.controller = pynput_keyboard.Controller()
        self.enabled = False
        self.block_held = False

    def set_enabled(self, value):
        self.enabled = bool(value)
        if not self.enabled:
            self.set_block(False)

    def tap(self, key):
        if not self.enabled:
            return
        self.controller.press(key)
        time.sleep(0.045)
        self.controller.release(key)

    def set_block(self, active):
        active = bool(active) and self.enabled
        if active and not self.block_held:
            self.controller.press("s")
            self.block_held = True
        elif not active and self.block_held:
            self.controller.release("s")
            self.block_held = False

    def release_all(self):
        self.set_block(False)
        self.enabled = False


class BoxingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI BOXING - CAMERA")
        self.root.configure(bg="#111827")
        self.root.resizable(False, False)

        self.cap = None
        self.pose = None
        self.keys = KeyboardOutput()
        self.running = True
        self.control_enabled = False
        self.hotkey_listener = None
        self.last_frame_time = time.perf_counter()
        self.fps = 0.0

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.panel_w = min(CAMERA_PANEL_W, max(340, int(screen_w * 0.25)))
        self.game_w, self.game_h, self.browser_label = launch_game_window(
            screen_w, screen_h, self.panel_w
        )

        x = screen_w - self.panel_w - 8
        self.root.geometry(f"{self.panel_w}x{CAMERA_PANEL_H}+{x}+12")

        self._build_ui()
        self._open_camera()
        self.pose = PoseBoxingController()

        self.hotkey_listener = pynput_keyboard.Listener(on_press=self._on_hotkey)
        self.hotkey_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(20, self.update_frame)

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#111827")
        header.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(
            header, text="AI BOXING CAMERA",
            font=("Segoe UI", 13, "bold"), fg="#F9FAFB", bg="#111827"
        ).pack(side="left")

        self.status_label = tk.Label(
            header, text="CONTROL OFF",
            font=("Segoe UI", 9, "bold"), fg="#FBBF24", bg="#111827"
        )
        self.status_label.pack(side="right")

        self.image_label = tk.Label(self.root, bg="#020617", bd=0)
        self.image_label.pack(padx=10, pady=4)

        self.action_label = tk.Label(
            self.root, text="POSE: WAITING | ACTION: -",
            font=("Segoe UI", 9, "bold"), fg="#E5E7EB", bg="#111827"
        )
        self.action_label.pack(fill="x", padx=10, pady=(2, 5))

        buttons = tk.Frame(self.root, bg="#111827")
        buttons.pack(fill="x", padx=10, pady=2)

        self.toggle_button = tk.Button(
            buttons, text="BAT DIEU KHIEN (F8)",
            command=self.toggle_control, bg="#166534", fg="white",
            activebackground="#15803D", activeforeground="white",
            relief="flat", font=("Segoe UI", 9, "bold"), padx=8, pady=6
        )
        self.toggle_button.pack(side="left", expand=True, fill="x", padx=(0, 4))

        tk.Button(
            buttons, text="CAN CHINH (F9)", command=self.recalibrate,
            bg="#334155", fg="white", activebackground="#475569",
            activeforeground="white", relief="flat",
            font=("Segoe UI", 9, "bold"), padx=8, pady=6
        ).pack(side="left", expand=True, fill="x", padx=4)

        tk.Button(
            buttons, text="THOAT (F10)", command=self.close,
            bg="#7F1D1D", fg="white", activebackground="#991B1B",
            activeforeground="white", relief="flat",
            font=("Segoe UI", 9, "bold"), padx=8, pady=6
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        tk.Label(
            self.root,
            text=f"Game: {self.browser_label} | Click game truoc khi bat F8",
            font=("Segoe UI", 8), fg="#94A3B8", bg="#111827"
        ).pack(fill="x", padx=10, pady=(5, 4))

    def _open_camera(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
        if not self.cap.isOpened():
            raise RuntimeError(
                "Khong mo duoc webcam. Dong Zoom/Teams/Camera hoac doi CAMERA_INDEX = 1."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_H)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _on_hotkey(self, key):
        if key == pynput_keyboard.Key.f8:
            self.root.after(0, self.toggle_control)
        elif key == pynput_keyboard.Key.f9:
            self.root.after(0, self.recalibrate)
        elif key == pynput_keyboard.Key.f10:
            self.root.after(0, self.close)

    def toggle_control(self):
        self.control_enabled = not self.control_enabled
        self.keys.set_enabled(self.control_enabled)
        if self.control_enabled:
            self.status_label.config(text="CONTROL ON", fg="#4ADE80")
            self.toggle_button.config(text="TAT DIEU KHIEN (F8)", bg="#991B1B")
        else:
            self.status_label.config(text="CONTROL OFF", fg="#FBBF24")
            self.toggle_button.config(text="BAT DIEU KHIEN (F8)", bg="#166534")

    def recalibrate(self):
        if self.pose is not None:
            self.pose.recalibrate()
        self.action_label.config(text="POSE: CALIBRATING - DUNG THANG NHIN CAMERA")

    def _draw_pose(self, frame, landmarks):
        h, w = frame.shape[:2]

        def point(index):
            return int((1.0 - landmarks[index][0]) * w), int(landmarks[index][1] * h)

        for a, b in POSE_LINES:
            if landmarks[a][3] > 0.30 and landmarks[b][3] > 0.30:
                cv2.line(frame, point(a), point(b), (70, 220, 120), 2, cv2.LINE_AA)

        for index in [
            NOSE, LEFT_SHOULDER, RIGHT_SHOULDER,
            LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST
        ]:
            if landmarks[index][3] > 0.30:
                cv2.circle(frame, point(index), 5, (0, 220, 255), -1, cv2.LINE_AA)

    def update_frame(self):
        if not self.running:
            return

        ok, frame = self.cap.read()
        if ok:
            frame = cv2.resize(frame, (CAMERA_W, CAMERA_H), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            events, state = self.pose.process(rgb)

            self.keys.set_block(state["guard"])
            if self.control_enabled and not state["guard"]:
                for action, key in events:
                    self.keys.tap(key)

            now = time.perf_counter()
            dt = max(0.001, now - self.last_frame_time)
            self.last_frame_time = now
            instant_fps = 1.0 / dt
            self.fps = instant_fps if self.fps == 0 else 0.85 * self.fps + 0.15 * instant_fps

            preview = cv2.flip(frame, 1)
            if state["landmarks"] is not None:
                self._draw_pose(preview, state["landmarks"])

            color = (60, 210, 100) if self.control_enabled else (0, 170, 255)
            cv2.rectangle(preview, (8, 8), (CAMERA_W - 8, 56), (15, 23, 42), -1)
            cv2.putText(
                preview, "CONTROL ON" if self.control_enabled else "CONTROL OFF",
                (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2, cv2.LINE_AA
            )
            cv2.putText(
                preview, f"FPS {self.fps:.0f}",
                (18, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1, cv2.LINE_AA
            )

            image = Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
            image = image.resize((self.panel_w - 20, 205), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image=image)
            self.image_label.configure(image=photo)
            self.image_label.image = photo

            pose_text = "POSE OK" if state["pose_ok"] else state["gesture"]
            self.action_label.config(
                text=f"{pose_text} | {state['gesture']} | KEY {state['key']} | {self.fps:.0f} FPS"
            )

        self.root.after(15, self.update_frame)

    def close(self):
        if not self.running:
            return
        self.running = False
        self.keys.release_all()
        try:
            if self.hotkey_listener is not None:
                self.hotkey_listener.stop()
        except Exception:
            pass
        try:
            if self.pose is not None:
                self.pose.close()
        except Exception:
            pass
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.root.destroy()


def main():
    try:
        app = BoxingApp()
        print("[OK] Da mo game Y8 va camera panel.")
        print("[TIP] Click game, chon Quick Mode, sau do bam F8.")
        app.root.mainloop()
        return 0
    except Exception as exc:
        print("[ERROR]", type(exc).__name__, str(exc))
        try:
            messagebox.showerror("AI Boxing - Loi khoi dong", str(exc))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
