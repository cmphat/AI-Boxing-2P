"""Single-player immersive 3D boxing with webcam locomotion and bot opponent.

Run: python -m solo3d.main
Preview without a webcam: python -m solo3d.main --demo
"""
from __future__ import annotations
import argparse
import sys
import time

import cv2
import numpy as np
import pygame

from solo3d.fight import Fight
from solo3d.visual import SoloScene


def parse():
    p=argparse.ArgumentParser(description="AI Boxing: solo first-person 3D")
    p.add_argument("--demo",action="store_true",help="Keyboard controls, no camera and no MediaPipe model")
    p.add_argument("--camera",type=int,default=0)
    p.add_argument("--difficulty",choices=["easy","normal","hard"],default="normal")
    p.add_argument("--sensitivity",type=float,default=1.15)
    return p.parse_args()


def open_cam(index):
    cap=cv2.VideoCapture(index,cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap=cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam. Try --camera 1 or --demo.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,450)
    cap.set(cv2.CAP_PROP_FPS,30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
    return cap


def main():
    args=parse()
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER,1)
    pygame.display.set_mode((1280,720),pygame.OPENGL|pygame.DOUBLEBUF)
    pygame.display.set_caption("AI Boxing | Solo 3D | Webcam Movement")
    scene=None
    tracker=None
    cap=None
    try:
        scene=SoloScene()
        fight=Fight(args.difficulty)
        if not args.demo:
            from solo3d.pose import SoloPose,draw_overlay
            tracker=SoloPose(args.sensitivity)
            cap=open_cam(args.camera)
        clock=pygame.time.Clock()
        ts=-1
        running=True
        last_pose_time=0.0
        last_preview_time=0.0
        cached_control=None
        cached_preview=None
        while running:
            dt=min(.07,max(.001,clock.tick(60)/1000))
            force_punch=None
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: running=False
                elif ev.type==pygame.KEYDOWN:
                    if ev.key==pygame.K_ESCAPE:running=False
                    elif ev.key==pygame.K_r:fight.reset()
                    elif ev.key==pygame.K_c and tracker:
                        tracker.calibrate()
                        cached_control=None
                        print("[CALIBRATED] Stand neutral, face camera, then tilt head to dodge.")
                    elif ev.key==pygame.K_j:force_punch="left"
                    elif ev.key==pygame.K_k:force_punch="right"
                    elif ev.key==pygame.K_1:fight=Fight("easy")
                    elif ev.key==pygame.K_2:fight=Fight("normal")
                    elif ev.key==pygame.K_3:fight=Fight("hard")
                    elif ev.key==pygame.K_LEFTBRACKET and tracker:
                        tracker.sensitivity=max(.7,tracker.sensitivity-.1)
                    elif ev.key==pygame.K_RIGHTBRACKET and tracker:
                        tracker.sensitivity=min(2.0,tracker.sensitivity+.1)
            keys=pygame.key.get_pressed()
            sideways=float(bool(keys[pygame.K_d]))-float(bool(keys[pygame.K_a]))
            forward=float(bool(keys[pygame.K_s]))-float(bool(keys[pygame.K_w]))
            # W forward decreases player Z; S backward increases Z.
            control={"tracked":False,"x":fight.player["x"],"z":fight.player["z"],
                     "guard":False,"punch":None,"head_roll":0.,"head_offset":0.}
            preview=cached_preview
            if cap and (time.monotonic()-last_pose_time)>=1.0/28.0:
                ok,frame=cap.read()
                if ok:
                    frame=cv2.flip(frame,1)
                    ts=max(int(time.monotonic()*1000),ts+1)
                    cached_control=tracker.process(frame,ts)
                    last_pose_time=time.monotonic()
                    if last_pose_time-last_preview_time>=1.0/12.0:
                        overlay=draw_overlay(frame,cached_control)
                        h,w=overlay.shape[:2]
                        cached_preview=pygame.image.frombuffer(
                            cv2.cvtColor(overlay,cv2.COLOR_BGR2RGB).tobytes(),(w,h),"RGB").copy()
                        last_preview_time=last_pose_time
                    preview=cached_preview
            if cached_control is not None:
                control=cached_control.copy()
                # Punches are discrete events: do not fire repeatedly when
                # the render loop runs faster than the webcam detection.
                cached_control["punch"]=None
                if time.monotonic()-last_pose_time>.30:
                    control.update({"tracked":False,"guard":False,
                                    "punch":None,"head_roll":0.,"head_offset":0.})
            fight.update(dt,control,move=(sideways,forward),force_punch=force_punch)
            scene.render(fight,dt,control)
            scene.draw_hud(fight,control,preview,mode=("KEYBOARD DEMO" if args.demo else "WEBCAM"),
                           fps=clock.get_fps())
            pygame.display.flip()
    finally:
        if tracker:tracker.close()
        if cap:cap.release()
        if scene:scene.close()
        pygame.quit()
    return 0


if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        print("[SOLO 3D ERROR]",exc,file=sys.stderr)
        sys.exit(1)
