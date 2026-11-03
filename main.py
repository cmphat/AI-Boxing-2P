import sys
import time

import cv2
import pygame

from boxing_game import BoxingGame
from pose_tracker import PoseTracker


CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(
            "Khong mo duoc webcam. Dong Zoom/Teams/Camera app hoac doi "
            "CAMERA_INDEX trong main.py tu 0 thanh 1."
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)
    return cap


def draw_pose_overlay(frame, people):
    height, width = frame.shape[:2]
    colors = [(255, 170, 40), (70, 80, 255)]
    connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24),
        (23, 25), (25, 27), (24, 26), (26, 28),
    ]
    for player_index, person in enumerate(people):
        if person is None:
            continue
        lm = person["landmarks"]
        color = colors[player_index]
        for a, b in connections:
            if lm[a]["visibility"] < 0.30 or lm[b]["visibility"] < 0.30:
                continue
            p1 = (int(lm[a]["x"] * width), int(lm[a]["y"] * height))
            p2 = (int(lm[b]["x"] * width), int(lm[b]["y"] * height))
            cv2.line(frame, p1, p2, color, 3, cv2.LINE_AA)
        for index in [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]:
            if lm[index]["visibility"] < 0.30:
                continue
            point = (int(lm[index]["x"] * width), int(lm[index]["y"] * height))
            cv2.circle(frame, point, 5, color, -1, cv2.LINE_AA)
        label_x = int(person["center_x"] * width)
        cv2.putText(frame, f"PLAYER {player_index + 1}",
                    (max(8, label_x - 55), 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    return frame


def main():
    print("=" * 58)
    print("AI BOXING - PVE / PVP")
    print("Menu: 1 = PVE, 2 = PVP | E/N/H = bot difficulty")
    print("In game: A/L = test punch | R = restart | M = menu | ESC = quit")
    print("=" * 58)

    cap = None
    tracker = None
    game = None

    try:
        cap = open_camera()
        tracker = PoseTracker()
        game = BoxingGame()
        previous_time = time.perf_counter()
        previous_timestamp_ms = 0
        running = True

        while running:
            now = time.perf_counter()
            dt = min(0.05, max(0.001, now - previous_time))
            previous_time = now
            keyboard_punches = []

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_1:
                        game.start("pve")
                    elif event.key == pygame.K_2:
                        game.start("pvp")
                    elif event.key == pygame.K_e:
                        game.set_difficulty("easy")
                    elif event.key == pygame.K_n:
                        game.set_difficulty("normal")
                    elif event.key == pygame.K_h:
                        game.set_difficulty("hard")
                    elif event.key == pygame.K_r and game.mode is not None:
                        game.reset()
                    elif event.key == pygame.K_m:
                        game.back_to_menu()
                    elif event.key == pygame.K_a:
                        keyboard_punches.append(0)
                    elif event.key == pygame.K_l:
                        keyboard_punches.append(1)

            ok, frame = cap.read()
            if not ok:
                print("[WARNING] Khong doc duoc frame webcam.")
                continue

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            timestamp_ms = int(time.perf_counter() * 1000)
            timestamp_ms = max(timestamp_ms, previous_timestamp_ms + 1)
            previous_timestamp_ms = timestamp_ms

            people, gestures = tracker.process(
                rgb, timestamp_ms, single_player=(game.mode == "pve")
            )
            frame = draw_pose_overlay(frame, people)

            for player_index in keyboard_punches:
                game.keyboard_punch(player_index)

            game.update(dt, gestures)
            game.draw(frame, people)
            game.clock.tick(60)

    except Exception as exc:
        print("\n[ERROR]", exc)
        print("\nKiem tra README.md de xem huong dan khac phuc.")
        input("\nNhan Enter de dong cua so...")
        return 1
    finally:
        if tracker is not None:
            tracker.close()
        if cap is not None:
            cap.release()
        if game is not None:
            game.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
