"""Responsive solo 3D boxing.

Rendering runs independently of webcam/MediaPipe inference:
    python -m solo3d.main
    python -m solo3d.main --demo
"""
from __future__ import annotations

import argparse
import sys

import cv2
import pygame

from .fight import Fight
from .visual import SoloScene


def parse():
    parser=argparse.ArgumentParser(description="Solo 3D boxing with head dodge")
    parser.add_argument("--demo",action="store_true",
                        help="Keyboard-only preview, no webcam required")
    parser.add_argument("--camera",type=int,default=0)
    parser.add_argument("--difficulty",choices=("easy","normal","hard"),
                        default="normal")
    parser.add_argument("--sensitivity",type=float,default=1.15)
    return parser.parse_args()


def make_preview(frame_bgr):
    h,w=frame_bgr.shape[:2]
    # Pygame surface is constructed only when a new camera preview arrives.
    image=cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(image.tobytes(),(w,h),"RGB").copy()


def main():
    args=parse()
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER,1)
    pygame.display.set_mode((1280,720),pygame.OPENGL|pygame.DOUBLEBUF)
    pygame.display.set_caption("AI Boxing | Solo 3D | Head Dodge")
    worker=None
    scene=None
    try:
        scene=SoloScene()
        fight=Fight(args.difficulty)
        if not args.demo:
            from .worker import PoseWorker
            worker=PoseWorker(camera=args.camera,sensitivity=args.sensitivity)
            worker.start()

        clock=pygame.time.Clock()
        cached_preview=None
        last_preview_frame=None
        preview_large=True
        running=True
        while running:
            dt=min(.06,max(.001,clock.tick(60)/1000.))
            force_punch=None
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    running=False
                elif event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        running=False
                    elif event.key==pygame.K_r:
                        fight.reset()
                    elif event.key==pygame.K_c and worker:
                        worker.request_calibrate()
                        print("[CALIBRATION] Face camera and remain still for 12 valid frames.")
                    elif event.key==pygame.K_v:
                        preview_large=not preview_large
                    elif event.key==pygame.K_j:
                        force_punch="left"
                    elif event.key==pygame.K_k:
                        force_punch="right"
                    elif event.key in (pygame.K_1,pygame.K_2,pygame.K_3):
                        difficulty={pygame.K_1:"easy",pygame.K_2:"normal",pygame.K_3:"hard"}[event.key]
                        fight=Fight(difficulty)
                    elif event.key==pygame.K_LEFTBRACKET and worker:
                        args.sensitivity=max(.7,args.sensitivity-.10)
                        worker.set_sensitivity(args.sensitivity)
                    elif event.key==pygame.K_RIGHTBRACKET and worker:
                        args.sensitivity=min(2.,args.sensitivity+.10)
                        worker.set_sensitivity(args.sensitivity)
            keys=pygame.key.get_pressed()
            side=float(bool(keys[pygame.K_d]))-float(bool(keys[pygame.K_a]))
            depth=float(bool(keys[pygame.K_s]))-float(bool(keys[pygame.K_w]))
            control={"tracked":False,"guard":False,"punch":None,
                     "head_roll":0.0,"head_offset":0.0}
            if worker:
                control,raw_preview,seq=worker.snapshot()
                # Only convert a *new* diagnostic image; worker pose refreshes
                # much more frequently than the webcam preview.
                if raw_preview is not None and raw_preview is not last_preview_frame:
                    cached_preview=make_preview(raw_preview)
                    last_preview_frame=raw_preview

            # Before camera calibration completes, display telemetry and keep
            # combat paused. Manual WASD still works if user needs fallback.
            gameplay_ready=(args.demo or bool(control.get("calibrated") and
                                                  control.get("tracked")))
            if gameplay_ready or (side!=0 or depth!=0 or force_punch):
                fight.update(dt,control,move=(side,depth),force_punch=force_punch)
            scene.render(fight,dt,control)
            scene.draw_hud(
                fight,control,cached_preview,
                mode=("KEYBOARD DEMO" if args.demo else "WEBCAM + HEAD DODGE"),
                fps=clock.get_fps(),
                preview_large=preview_large
            )
            pygame.display.flip()
    finally:
        if worker:
            worker.close()
        if scene:
            scene.close()
        pygame.quit()
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[SOLO 3D ERROR]",exc,file=sys.stderr)
        sys.exit(1)
