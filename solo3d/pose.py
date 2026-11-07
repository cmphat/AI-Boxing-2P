"""Single-player camera pose controls with calibration and stable physical coordinates.

The depth estimate uses apparent shoulder width, NOT metric depth. One webcam
cannot recover absolute translation reliably; shoulder yaw/occlusion can bias it.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np

from .motion import HeadController, head_measure, smooth_value, deadband

MODEL = Path(__file__).resolve().parents[1] / "assets" / "pose_landmarker_lite.task"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def joint_angle(a, b, c):
    v1, v2 = a-b, c-b
    norm = np.linalg.norm(v1)*np.linalg.norm(v2)
    return math.degrees(math.acos(clamp(float(np.dot(v1,v2)/norm),-1,1))) if norm>1e-6 else 0.0


class SoloPose:
    def __init__(self, sensitivity=1.2):
        if not MODEL.is_file():
            raise FileNotFoundError("Missing MediaPipe model. Run setup_3d.bat first.")
        opts = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1, min_pose_detection_confidence=.50,
            min_pose_presence_confidence=.50, min_tracking_confidence=.50,
        )
        self.engine=mp.tasks.vision.PoseLandmarker.create_from_options(opts)
        self.sensitivity=sensitivity
        self.baseline=None
        self.smooth_pos=None
        self.smooth_scale=None
        self.previous_wrist=[None,None]
        self.last_fire=[-100.,-100.]
        self.rearmed=[True,True]
        self.last_ts=-1
        self.head=HeadController()
        self.smooth_x=None
        self.smooth_z=None

    def close(self):
        self.engine.close()

    def calibrate(self):
        self.baseline=None
        self.smooth_pos=None
        self.smooth_scale=None
        self.smooth_x=None
        self.smooth_z=None
        self.head.reset()

    def process(self, bgr, timestamp_ms):
        timestamp_ms=max(timestamp_ms,self.last_ts+1)
        dt=clamp((timestamp_ms-self.last_ts)/1000 if self.last_ts>=0 else 1/30,.008,.12)
        self.last_ts=timestamp_ms
        rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        frame=mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb))
        result=self.engine.detect_for_video(frame,timestamp_ms)
        control={"tracked":False,"calibrated":self.baseline is not None,
                 "x":0.,"z":2.9,"guard":False,"punch":None,"confidence":0.,
                 "landmarks":None,"vis":None,"depth_ratio":1.0,"shoulder_px":0.,
                 "fist_speed":0.0,"head_roll":0.0,"head_offset":0.0}
        if not result.pose_landmarks:
            self.previous_wrist=[None,None]
            control['head_roll'],control['head_offset']=self.head.update(None,dt)
            return control

        pose=result.pose_landmarks[0]
        pts=np.array([(p.x,p.y,p.z) for p in pose],dtype=np.float32)
        vis=np.array([float(getattr(p,"visibility",1.0) or 0) for p in pose],dtype=np.float32)
        control["landmarks"]=pts
        control["vis"]=vis
        tracked_quality=min(float(vis[11]),float(vis[12]),float(vis[23]),float(vis[24]))
        if tracked_quality<.42:
            control['head_roll'],control['head_offset']=self.head.update(None,dt)
            return control
        center=float((pts[23,0]+pts[24,0]+pts[11,0]+pts[12,0])*.25)
        width=float(abs(pts[11,0]-pts[12,0]))
        height=float(abs(np.mean(pts[[23,24],1])-np.mean(pts[[11,12],1])))
        # Use width/height blended proxy to mitigate turning slightly.
        scale=clamp(.65*width+.35*height,.055,.60)
        control["shoulder_px"]=width*bgr.shape[1]
        control["confidence"]=tracked_quality
        control["tracked"]=True
        if self.baseline is None:
            self.baseline=(center,scale)
            self.smooth_pos=np.array([center,scale],dtype=np.float32)
        raw=np.array([center,scale],dtype=np.float32)
        alpha=1.0-math.exp(-dt/.095)
        self.smooth_pos=alpha*raw+(1.0-alpha)*self.smooth_pos
        c,sc=map(float,self.smooth_pos)
        origin,base_scale=self.baseline
        ratio=clamp(sc/max(.055,base_scale),.67,1.45)
        control["depth_ratio"]=ratio
        # Depth: walking physically closer increases apparent body size.
        # X: shift from your calibrated standing location. Dead zones
        # prevent skeleton jitter from moving the virtual player.
        x_raw=deadband((c-origin)*7.0, .10)
        z_raw=2.95-deadband((ratio-1.0)*8.5, .14)
        self.smooth_x=smooth_value(self.smooth_x,clamp(x_raw,-2.5,2.5),dt,.13)
        self.smooth_z=smooth_value(self.smooth_z,clamp(z_raw,.55,3.55),dt,.16)
        control["x"]=self.smooth_x
        control["z"]=self.smooth_z
        # Only the head relative to shoulders controls camera dodge;
        # whole-body sidestepping still controls world X.
        measured=head_measure(pts,vis)
        control["head_roll"],control["head_offset"]=self.head.update(measured,dt)
        control["calibrated"]=True

        shoulder_y=float(np.mean(pts[[11,12],1]))
        wleft,wright=pts[15],pts[16]
        guard=(min(vis[15],vis[16])>.48 and
               wleft[1]<shoulder_y+.05 and wright[1]<shoulder_y+.05)
        control["guard"]=bool(guard)
        now=time.monotonic()
        for a,(sh,el,wr) in enumerate(((11,13,15),(12,14,16))):
            if min(vis[sh],vis[el],vis[wr])<.45:
                self.previous_wrist[a]=None
                continue
            wrist=pts[wr].copy()
            prev=self.previous_wrist[a]
            velocity=(wrist-prev)/dt if prev is not None else np.zeros(3)
            speed=float(np.linalg.norm(velocity[:2])/max(width,.08))
            depth_speed=float(-velocity[2]/max(width,.08))
            control["fist_speed"]=max(control["fist_speed"],speed)
            ang=joint_angle(pts[sh],pts[el],wrist)
            if ang<125:
                self.rearmed[a]=True
            if (self.rearmed[a] and ang>144 and now-self.last_fire[a]>.34
                and (speed>2.3/self.sensitivity or
                     (depth_speed>1.35/self.sensitivity and speed>.65))):
                control["punch"]="left" if a==0 else "right"
                self.rearmed[a]=False
                self.last_fire[a]=now
            self.previous_wrist[a]=wrist
        return control


POSE_LINES=((11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24))


def draw_overlay(frame,control):
    out=frame.copy()
    pts=control.get("landmarks")
    vis=control.get("vis")
    if pts is None:
        cv2.putText(out,"NO POSE",(12,26),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,70,240),2)
        return out
    h,w=out.shape[:2]
    for a,b in POSE_LINES:
        if vis[a]<.35 or vis[b]<.35: continue
        p=tuple((pts[a,:2]*[w,h]).astype(int))
        q=tuple((pts[b,:2]*[w,h]).astype(int))
        cv2.line(out,p,q,(60,240,100),3,cv2.LINE_AA)
    for i in (0,11,12,13,14,15,16,23,24):
        if vis[i]<.35: continue
        x,y=(pts[i,:2]*[w,h]).astype(int)
        cv2.circle(out,(int(x),int(y)),5,(220,230,240),-1,cv2.LINE_AA)
    cv2.putText(out,f"X {control['x']:+.1f} Z {control['z']:.1f} HEAD {control['head_roll']:+.0f}deg",
                (12,26),cv2.FONT_HERSHEY_SIMPLEX,.58,(80,250,210),2)
    return out
