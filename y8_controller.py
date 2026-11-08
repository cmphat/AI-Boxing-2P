import os
import shutil
import subprocess
import threading
import time
import tkinter as tk

import cv2
from pynput import keyboard

from gesture_engine import (
    Y8GestureEngine, SKELETON,
    NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST
)
from key_output import GameKeyOutput


GAME_URL = "https://vi.y8.com/games/punch_boxing_championship"

CAMERA_INDEX = 0
CAMERA_WIDTH = 960
CAMERA_HEIGHT = 540

WINDOW_TITLE = "AI Boxing - Camera Controller"
GAME_SCREEN_RATIO = 0.72

running = True
control_enabled = False
recalibrate_requested = False


def get_screen_size():
    """Return Windows desktop working size without extra dependencies."""
    root = tk.Tk()
    root.withdraw()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    return width, height


def find_browser():
    """Prefer Edge, then Chrome. Return executable path or None."""
    candidates = []

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app = os.environ.get("LOCALAPPDATA", "")

    candidates += [
        os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_app, "Google", "Chrome", "Application", "chrome.exe"),
    ]

    for exe_name in ("msedge.exe", "chrome.exe", "msedge", "google-chrome", "chrome"):
        found = shutil.which(exe_name)
        if found:
            candidates.insert(0, found)

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def launch_game_app():
    """
    Launch Y8 as a separate app-style window:
    - no browser tabs
    - no address bar
    - game window on the left
    - camera/debug window will sit on the right
    """
    screen_w, screen_h = get_screen_size()

    game_w = int(screen_w * GAME_SCREEN_RATIO)
    game_h = max(650, screen_h - 80)

    browser = find_browser()
    if browser is None:
        raise RuntimeError(
            "Khong tim thay Microsoft Edge hoac Google Chrome. "
            "Hay cai Edge/Chrome hoac sua find_browser() trong y8_controller.py."
        )

    args = [
        browser,
        f"--app={GAME_URL}",
        f"--window-position=0,0",
        f"--window-size={game_w},{game_h}",
        "--no-first-run",
        "--disable-features=TranslateUI",
    ]

    # New process/group avoids reusing a normal browser tab in most cases.
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    return {
        "screen_w": screen_w,
        "screen_h": screen_h,
        "game_w": game_w,
        "game_h": game_h,
    }


def hotkeys(key):
    global running, control_enabled, recalibrate_requested

    if key == keyboard.Key.f8:
        control_enabled = not control_enabled
        print(f"[CONTROL] {'ON' if control_enabled else 'OFF'}")

    elif key == keyboard.Key.f9:
        recalibrate_requested = True
        print("[POSE] Recalibration requested")

    elif key == keyboard.Key.f10:
        running = False
        return False


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError(
            "Khong mo duoc webcam. Dong Zoom/Teams/Camera app "
            "hoac doi CAMERA_INDEX trong y8_controller.py."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw_debug(frame, state, fps, enabled):
    """
    Draw compact debug HUD.
    Preview is mirrored, therefore landmark X is mirrored too.
    """
    lm = state.get("landmarks")
    h, w = frame.shape[:2]

    if lm:
        def pt(i):
            x = int((1.0 - lm[i][0]) * w)
            y = int(lm[i][1] * h)
            return x, y

        for a, b in SKELETON:
            if lm[a][3] > 0.30 and lm[b][3] > 0.30:
                cv2.line(frame, pt(a), pt(b), (70, 220, 120), 2, cv2.LINE_AA)

        for i in [
            NOSE, L_SHOULDER, R_SHOULDER,
            L_ELBOW, R_ELBOW, L_WRIST, R_WRIST
        ]:
            if lm[i][3] > 0.30:
                cv2.circle(frame, pt(i), 5, (0, 220, 255), -1, cv2.LINE_AA)

    status = "CONTROL ON" if enabled else "CONTROL OFF"
    status_color = (70, 225, 115) if enabled else (0, 180, 255)

    cv2.rectangle(frame, (10, 10), (w - 10, 126), (18, 22, 28), -1)

    cv2.putText(
        frame, status,
        (22, 38),
        cv2.FONT_HERSHEY_SIMPLEX, 0.72,
        status_color, 2, cv2.LINE_AA
    )

    pose_text = "POSE OK" if state.get("pose_ok") else "SHOW ARMS"
    pose_color = (70, 225, 115) if state.get("pose_ok") else (0, 180, 255)

    cv2.putText(
        frame, pose_text,
        (22, 68),
        cv2.FONT_HERSHEY_SIMPLEX, 0.57,
        pose_color, 2, cv2.LINE_AA
    )

    action = state.get("gesture", "IDLE")
    key = state.get("key", "-")

    cv2.putText(
        frame, f"{action}  |  KEY {key}",
        (22, 96),
        cv2.FONT_HERSHEY_SIMPLEX, 0.54,
        (238, 238, 238), 1, cv2.LINE_AA
    )

    cv2.putText(
        frame, f"FPS {fps:.0f}  |  F8 ON/OFF  F9 CAL  F10 EXIT",
        (22, 118),
        cv2.FONT_HERSHEY_SIMPLEX, 0.40,
        (180, 190, 205), 1, cv2.LINE_AA
    )

    return frame


def configure_camera_window(layout):
    """Create a compact camera panel on the right side of the desktop."""
    screen_w = layout["screen_w"]
    screen_h = layout["screen_h"]
    game_w = layout["game_w"]

    margin = 10
    available_w = max(300, screen_w - game_w - margin * 2)

    cam_w = min(available_w, 500)
    cam_h = int(cam_w * 9 / 16)

    # Keep a sensible minimum height for the HUD.
    cam_h = max(260, min(cam_h, screen_h - 100))

    x = min(screen_w - cam_w - margin, game_w + margin)
    y = 20

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, cam_w, cam_h)
    cv2.moveWindow(WINDOW_TITLE, x, y)

    return cam_w, cam_h


def main():
    global running, recalibrate_requested

    print("=" * 70)
    print("AI BOXING - Y8 POSE CONTROLLER")
    print("Game: cua so rieng ben trai")
    print("Camera: cua so nho ben phai")
    print("F8  : bat/tat dieu khien")
    print("F9  : calibrate lai")
    print("F10 : thoat controller")
    print("=" * 70)

    cap = None
    engine = None
    keys = GameKeyOutput()

    listener = keyboard.Listener(on_press=hotkeys)
    listener.start()

    try:
        layout = launch_game_app()
        time.sleep(1.0)

        cap = open_camera()
        engine = Y8GestureEngine()

        cam_w, cam_h = configure_camera_window(layout)

        prev = time.perf_counter()
        fps_ema = 0.0
        timestamp_ms = 0

        print("[READY] Game da mo o cua so app rieng.")
        print("[READY] Camera debug nam ben phai.")
        print("[TIP] Click vao game, sau do bam F8 de bat pose control.")

        while running:
            ok, frame = cap.read()
            if not ok:
                continue

            now = time.perf_counter()
            dt = max(1e-3, now - prev)
            prev = now

            inst_fps = 1.0 / dt
            fps_ema = inst_fps if fps_ema == 0 else 0.90 * fps_ema + 0.10 * inst_fps

            if recalibrate_requested:
                engine.recalibrate()
                recalibrate_requested = False

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            timestamp_ms += max(1, int(dt * 1000))
            events, state = engine.process(rgb, timestamp_ms)

            keys.set_enabled(control_enabled)

            # Block is held while guard pose is active.
            keys.hold("s", bool(state.get("guard")), "BLOCK")

            # Punch/dodge events are edge-triggered.
            if not state.get("guard"):
                for action, key in events:
                    duration = 0.055 if action == "DODGE" else 0.045
                    keys.tap(key, duration, action)

            preview = cv2.flip(frame, 1)
            preview = draw_debug(preview, state, fps_ema, control_enabled)
            preview = cv2.resize(preview, (cam_w, cam_h), interpolation=cv2.INTER_AREA)

            cv2.imshow(WINDOW_TITLE, preview)

            # ESC only works when the camera window is focused.
            if cv2.waitKey(1) & 0xFF == 27:
                running = False

            # User may close the camera window manually.
            try:
                if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                    running = False
            except cv2.error:
                running = False

    finally:
        keys.set_enabled(False)
        keys.release_all()

        if engine is not None:
            engine.close()

        if cap is not None:
            cap.release()

        cv2.destroyAllWindows()

        try:
            listener.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
