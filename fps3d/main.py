"""Entry point for the real 3D first-person build.

Examples:
    python -m fps3d.main --mode pvp
    python -m fps3d.main --mode pve
    python -m fps3d.main --demo --mode pvp  # no camera/model required
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np
import pygame

from .game import Match
from .renderer import Scene, WIDTH, HEIGHT


POSE_CONNECTIONS = (
    (11,12),(11,13),(13,15),(12,14),(14,16),
    (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
)


def camera_open(index):
    cap=cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap=cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError("Webcam unavailable; close other programs, try --camera 1, or use --demo.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,540)
    cap.set(cv2.CAP_PROP_FPS,30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
    return cap


def camera_preview(frame, pose_data):
    img=frame.copy()
    h,w=img.shape[:2]
    for index,g in enumerate(pose_data):
        points=g.get("landmarks")
        visibility=g.get("visibility")
        if points is None:
            continue
        col=(255,180,50) if index==0 else (55,80,255)
        for a,b in POSE_CONNECTIONS:
            if visibility[a]<0.35 or visibility[b]<0.35:
                continue
            pa=tuple((points[a,:2]*[w,h]).astype(int))
            pb=tuple((points[b,:2]*[w,h]).astype(int))
            cv2.line(img,pa,pb,col,2,cv2.LINE_AA)
        for i in (0,11,12,13,14,15,16,23,24):
            if visibility[i]<0.35:
                continue
            p=tuple((points[i,:2]*[w,h]).astype(int))
            cv2.circle(img,p,4,(255,255,255),-1,cv2.LINE_AA)
            cv2.circle(img,p,2,col,-1,cv2.LINE_AA)
    image=pygame.image.frombuffer(cv2.cvtColor(img,cv2.COLOR_BGR2RGB).tobytes(),(w,h),"RGB")
    return image.copy()


def parse(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["pvp","pve"],default="pvp")
    parser.add_argument("--camera",type=int,default=0)
    parser.add_argument("--sensitivity",type=float,default=1.15)
    parser.add_argument("--difficulty",choices=["easy","normal","hard"],default="normal")
    parser.add_argument("--demo",action="store_true",help="Keyboard-only OpenGL demo, no webcam needed.")
    return parser.parse_args(argv)


def main(argv=None):
    args=parse(argv)
    cap=None
    pose=None
    scene=None
    pygame.init()
    try:
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER,1)
        pygame.display.set_mode((WIDTH,HEIGHT),pygame.DOUBLEBUF|pygame.OPENGL)
        pygame.display.set_caption("AI Boxing 3D | First Person | PvP / PvE")
        scene=Scene()
        match=Match(args.mode,args.difficulty)
        if not args.demo:
            from .pose_control import PoseControl
            cap=camera_open(args.camera)
            pose=PoseControl(args.sensitivity)

        prev=time.monotonic()
        ts=-1
        t=0.0
        running=True
        while running:
            now=time.monotonic()
            dt=min(0.075,max(0.001,now-prev))
            prev=now
            t+=dt
            inputs=[{"tracked":False,"guard":False,"lean":0.0,"punch":None},
                    {"tracked":False,"guard":False,"lean":0.0,"punch":None}]
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    running=False
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        running=False
                    elif event.key==pygame.K_r:
                        match.reset()
                    elif event.key==pygame.K_1:
                        match=Match("pve",args.difficulty)
                    elif event.key==pygame.K_2:
                        match=Match("pvp",args.difficulty)
                    elif event.key==pygame.K_a:
                        match.punch(0,"left")
                    elif event.key==pygame.K_s:
                        match.punch(0,"right")
                    elif event.key==pygame.K_k:
                        match.punch(1,"left")
                    elif event.key==pygame.K_l:
                        match.punch(1,"right")
                    elif event.key==pygame.K_LEFTBRACKET and pose:
                        pose.sensitivity=max(.7,pose.sensitivity-.1)
                    elif event.key==pygame.K_RIGHTBRACKET and pose:
                        pose.sensitivity=min(2.0,pose.sensitivity+.1)
            preview=None
            if cap:
                ok,frame=cap.read()
                if ok:
                    frame=cv2.flip(frame,1)
                    rgb=np.ascontiguousarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                    ts=max(int(time.monotonic()*1000),ts+1)
                    inputs=pose.process(rgb,ts,pvp=(match.mode=="pvp"))
                    preview=camera_preview(frame,inputs)
                else:
                    print("Webcam frame unavailable; retrying",file=sys.stderr)
            match.update(dt,inputs)
            count=1 if match.mode=="pve" else 2
            for i in range(count):
                scene.view(i,match.players[i],match.players[1-i],t,solo=(count==1))
            scene.overlay(match.players,match.mode,match.seconds,inputs,camera=preview,
                          finished=match.finished,
                          help_message="A/S: P1 punch | K/L: P2 punch | 1: Bot | 2: PvP | [ ]: sensitivity | R: reset | Esc: exit")
            pygame.display.flip()
            pygame.time.Clock().tick(60)
    finally:
        if scene:
            scene.close()
        if pose:
            pose.close()
        if cap:
            cap.release()
        pygame.quit()
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[AI BOXING 3D ERROR]",str(exc),file=sys.stderr)
        sys.exit(1)
