import threading
import time
import webbrowser

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

running = True
control_enabled = False
recalibrate_requested = False


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
            "Khong mo duoc webcam. Dong Zoom/Teams/Camera hoac doi "
            "CAMERA_INDEX trong y8_controller.py."
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
            return int(lm[i][0] * w), int(lm[i][1] * h)

        for a, b in SKELETON:
            if lm[a][3] > 0.30 and lm[b][3] > 0.30:
                cv2.line(frame, pt(a), pt(b), (70, 220, 120), 3, cv2.LINE_AA)

        for i in [NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST]:
            if lm[i][3] > 0.30:
                cv2.circle(frame, pt(i), 7, (0, 220, 255), -1, cv2.LINE_AA)

    status = "CONTROL ON" if enabled else "CONTROL OFF - press F8"
    color = (60, 220, 100) if enabled else (0, 180, 255)

    cv2.rectangle(frame, (12, 12), (475, 145), (20, 25, 32), -1)
    cv2.putText(frame, status, (25, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.76, color, 2)
    cv2.putText(
        frame,
        f"POSE: {'OK' if state.get('pose_ok') else 'NOT READY'}",
        (25, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (235, 235, 235), 2
    )
    cv2.putText(
        frame,
        f"ACTION: {state.get('gesture', 'IDLE')}  KEY: {state.get('key', '-')}",
        (25, 102), cv2.FONT_HERSHEY_SIMPLEX, 0.57, (235, 235, 235), 2
    )
    cv2.putText(
        frame,
        f"FPS: {fps:.1f} | F8 toggle | F9 calibrate | F10 exit",
        (25, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 190, 205), 1
    )

    cv2.putText(
        frame,
        "Stand 1.5-2.5m away - show head, shoulders, elbows and wrists",
        (18, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 230), 1
    )
    return frame


def main():
    global running, recalibrate_requested

    print("=" * 70)
    print("AI BOXING - Y8 POSE CONTROLLER")
    print("F8  : bat/tat gui phim vao game")
    print("F9  : can chinh lai tu the trung tam")
    print("F10 : thoat controller")
    print("=" * 70)
    print("Game se mo trong trinh duyet. Chon mode va vao tran bang chuot.")
    print("Khi vao tran: click vao game de game nhan keyboard, sau do bam F8.")

    webbrowser.open(GAME_URL)

    cap = None
    engine = None
    keys = GameKeyOutput()

    listener = keyboard.Listener(on_press=hotkeys)
    listener.start()

    try:
        cap = open_camera()
        engine = Y8GestureEngine()

        prev = time.perf_counter()
        fps_ema = 0.0
        timestamp_ms = 0

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

            # Block is a held key. It is released immediately when hands leave guard.
            keys.hold("s", bool(state.get("guard")), "BLOCK")

            # Never punch while blocking.
            if not state.get("guard"):
                for action, key in events:
                    if action == "DODGE":
                        keys.tap(key, 0.055, action)
                    else:
                        keys.tap(key, 0.045, action)

            # Mirror only the preview, not the image sent to MediaPipe.
            preview = cv2.flip(frame, 1)
            preview = draw_debug(preview, state, fps_ema, control_enabled)
            cv2.imshow("AI Boxing - Pose Debug (F8 ON/OFF, F10 Exit)", preview)

            # Window can stay unfocused while Y8 receives injected keyboard.
            if cv2.waitKey(1) & 0xFF == 27:
                # ESC only closes debug if it currently has focus.
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
