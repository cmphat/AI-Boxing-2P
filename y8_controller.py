import ctypes
import os
import shutil
import subprocess
import tempfile
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
    root = tk.Tk()
    root.withdraw()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    return width, height


def find_browser():
    """Find Edge or Chrome executable."""
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
            return path
    return None


def find_window_for_pid(pid):
    """Find a visible top-level Windows window belonging to browser PID."""
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _):
        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindow(hwnd):
            if user32.GetWindowTextLengthW(hwnd) > 0:
                found.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return found[0] if found else None


def launch_game_app():
    """Launch Y8 in a standalone app window and verify its HWND exists."""
    screen_w, screen_h = get_screen_size()
    game_w = int(screen_w * GAME_SCREEN_RATIO)
    game_h = max(600, screen_h - 80)

    browser = find_browser()
    if not browser:
        raise RuntimeError(
            "Khong tim thay Microsoft Edge/Chrome. "
            "Hay cai Edge hoac Chrome roi chay lai."
        )

    # A dedicated browser profile prevents Chromium from reusing an old
    # normal-browser process and silently ignoring the --app arguments.
    profile_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
        "AIBoxingY8_AppProfile"
    )
    os.makedirs(profile_dir, exist_ok=True)

    args = [
        browser,
        f"--user-data-dir={profile_dir}",
        f"--app={GAME_URL}",
        "--new-window",
        "--no-first-run",
        "--disable-features=TranslateUI",
        f"--window-position=0,0",
        f"--window-size={game_w},{game_h}",
    ]

    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    # Wait for the actual browser window, not just successful Popen().
    hwnd = None
    for _ in range(100):
        hwnd = find_window_for_pid(proc.pid)
        if hwnd:
            break
        time.sleep(0.15)

    if not hwnd:
        raise RuntimeError(
            "Da goi Edge/Chrome nhung khong tim thay cua so game. "
            "Hay kiem tra Edge/Chrome co mo duoc khong, sau do chay lai."
        )

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    SWP_SHOWWINDOW = 0x0040
    HWND_TOP = 0

    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(
        hwnd, HWND_TOP, 0, 0, game_w, game_h, SWP_SHOWWINDOW
    )

    return {
        "screen_w": screen_w,
        "screen_h": screen_h,
        "game_w": game_w,
        "game_h": game_h,
        "game_hwnd": hwnd,
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
    lm = state.get("landmarks")
    h, w = frame.shape[:2]

    if lm:
        def pt(i):
            return int((1.0 - lm[i][0]) * w), int(lm[i][1] * h)

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
    cv2.putText(frame, status, (22, 38), cv2.FONT_HERSHEY_SIMPLEX,
                0.72, status_color, 2, cv2.LINE_AA)

    pose_text = "POSE OK" if state.get("pose_ok") else "SHOW ARMS"
    pose_color = (70, 225, 115) if state.get("pose_ok") else (0, 180, 255)
    cv2.putText(frame, pose_text, (22, 68), cv2.FONT_HERSHEY_SIMPLEX,
                0.57, pose_color, 2, cv2.LINE_AA)

    cv2.putText(
        frame,
        f"{state.get('gesture', 'IDLE')} | KEY {state.get('key', '-')}",
        (22, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.54,
        (238, 238, 238), 1, cv2.LINE_AA
    )
    cv2.putText(
        frame, f"FPS {fps:.0f} | F8 ON/OFF | F9 CAL | F10 EXIT",
        (22, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
        (180, 190, 205), 1, cv2.LINE_AA
    )
    return frame


def configure_camera_window(layout):
    screen_w = layout["screen_w"]
    screen_h = layout["screen_h"]
    game_w = layout["game_w"]

    margin = 10
    available_w = max(300, screen_w - game_w - margin * 2)
    cam_w = min(available_w, 500)
    cam_h = max(260, min(int(cam_w * 9 / 16), screen_h - 100))

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
    print("Game: cua so app rieng ben trai")
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
        print("[OK] Da xac nhan cua so game Y8.")
        print(f"[INFO] Game window: {layout['game_w']} x {layout['game_h']}")

        cap = open_camera()
        engine = Y8GestureEngine()
        cam_w, cam_h = configure_camera_window(layout)

        prev = time.perf_counter()
        fps_ema = 0.0
        timestamp_ms = 0

        print("[READY] Camera da khoi dong.")
        print("[TIP] Vao tran bang chuot, click game, sau do bam F8.")
        print("[TIP] Nhan F10 de thoat. Khong dong cua so camera de dung.")

        while running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.005)
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
            keys.hold("s", bool(state.get("guard")), "BLOCK")

            if not state.get("guard"):
                for action, key in events:
                    duration = 0.055 if action == "DODGE" else 0.045
                    keys.tap(key, duration, action)

            preview = cv2.flip(frame, 1)
            preview = draw_debug(preview, state, fps_ema, control_enabled)
            preview = cv2.resize(
                preview, (cam_w, cam_h), interpolation=cv2.INTER_AREA
            )
            cv2.imshow(WINDOW_TITLE, preview)

            # Do not terminate on WND_PROP_VISIBLE at startup. On some
            # Windows/OpenCV builds it briefly reports 0 before first paint.
            if cv2.waitKey(1) & 0xFF == 27:
                running = False

    except Exception as exc:
        print(f"\n[ERROR] {type(exc).__name__}: {exc}")
        raise

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
