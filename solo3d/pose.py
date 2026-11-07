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
from .tracking import RelativeMovement, body_measure
from .hands import pose_hands, flip_world_controls, arm_tracking_status

MODEL = Path(__file__).resolve().parents[1] / "assets" / "pose_landmarker_lite.task"
FULL_MODEL = MODEL.with_name("pose_landmarker_full.task")


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def joint_angle(a, b, c):
    v1, v2 = a-b, c-b
    norm = np.linalg.norm(v1)*np.linalg.norm(v2)
    return math.degrees(math.acos(clamp(float(np.dot(v1,v2)/norm),-1,1))) if norm>1e-6 else 0.0


class SoloPose:
    def __init__(self, sensitivity=1.2, model="auto"):
        model_path = FULL_MODEL if model in ("auto", "full") and FULL_MODEL.is_file() else MODEL
        if model == "full" and not FULL_MODEL.is_file():
            raise FileNotFoundError("Full pose model missing. Run download_full_model.py")
        if not model_path.is_file():
            raise FileNotFoundError("Missing MediaPipe model. Run setup_3d.bat first.")
        self.model_name="full" if model_path==FULL_MODEL else "lite"
        print("[POSE] Loaded MediaPipe model:",self.model_name,flush=True)
        opts = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
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
        self.movement=RelativeMovement(calibration_frames=12)
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
        self.movement.reset()

    def process(self, bgr, timestamp_ms):
        timestamp_ms=max(timestamp_ms,self.last_ts+1)
        dt=clamp((timestamp_ms-self.last_ts)/1000 if self.last_ts>=0 else 1/30,.008,.12)
        self.last_ts=timestamp_ms
        rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        frame=mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb))
        result=self.engine.detect_for_video(frame,timestamp_ms)
        control={"tracked":False,"calibrated":False,
                 "x":0.,"z":2.75,"guard":False,"punch":None,"confidence":0.,
                 "landmarks":None,"vis":None,"depth_ratio":1.0,"shoulder_px":0.,
                 "fist_speed":0.0,"head_roll":0.0,"head_offset":0.0,
                 "calibration":0,"center":.5,"scale":0.,"baseline_scale":0.,
                 "model":self.model_name,"hands":{"left":None,"right":None},
                 "arm_tracking":{"left":False,"right":False}}
        if not result.pose_landmarks:
            self.previous_wrist=[None,None]
            control.update(self.movement.update(None,dt))
            control['head_roll'],control['head_offset']=self.head.update(None,dt)
            return control

        pose=result.pose_landmarks[0]
        pts=np.array([(p.x,p.y,p.z) for p in pose],dtype=np.float32)
        vis=np.array([float(getattr(p,"visibility",1.0) or 0) for p in pose],dtype=np.float32)
        control["landmarks"]=pts
        control["vis"]=vis
        measure=body_measure(pts,vis,confidence=.34)
        control.update(self.movement.update(measure,dt))
        if measure is None:
            control["head_roll"],control["head_offset"]=self.head.update(None,dt)
            return control
        control["confidence"]=float(measure[2])
        control["hands"]=pose_hands(pts,vis)
        control["arm_tracking"]=arm_tracking_status(pts,vis)
        control["shoulder_px"]=float(abs(pts[11,0]-pts[12,0])*bgr.shape[1])
        control["depth_ratio"]=(
            control["scale"]/max(.04,control["baseline_scale"])
            if control["calibrated"] else 1.)
        measured=head_measure(pts,vis)
        control["head_roll"],control["head_offset"]=self.head.update(measured,dt)

        width=max(float(np.linalg.norm(pts[11,:2]-pts[12,:2])),0.08)
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
        # Preserve anatomical L/R from ORIGINAL, unflipped camera input.
        # Convert front-camera horizontal controls to player viewpoint.
        return flip_world_controls(control)


# Full 33-point MediaPipe skeleton (not upper body only).
POSE_LINES=(
    (11,12),(11,13),(13,15),(15,17),(15,19),(15,21),
    (17,19),(12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(25,27),(27,29),(29,31),(27,31),
    (24,26),(26,28),(28,30),(30,32),(28,32),
    (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),
    (9,10),
)


def draw_overlay(frame,control,mirrored=False):
    """Draw all 33 pose markers, connections, calibration progress and movement."""
    out=cv2.flip(frame,1) if mirrored else frame.copy()
    h,w=out.shape[:2]
    pts=control.get("landmarks")
    vis=control.get("vis")
    if pts is not None:
        for a,b in POSE_LINES:
            if min(vis[a],vis[b])<.28:
                continue
            pa=(int((1.-pts[a,0] if mirrored else pts[a,0])*w),int(pts[a,1]*h))
            pb=(int((1.-pts[b,0] if mirrored else pts[b,0])*w),int(pts[b,1]*h))
            cv2.line(out,pa,pb,(45,230,110),2,cv2.LINE_AA)
        for i in range(min(33,len(pts))):
            if vis[i]<.28:
                continue
            x=int((1.-pts[i,0] if mirrored else pts[i,0])*w)
            y=int(pts[i,1]*h)
            cv2.circle(out,(int(x),int(y)),4,(10,20,25),-1,cv2.LINE_AA)
            cv2.circle(out,(int(x),int(y)),2,(0,235,255),-1,cv2.LINE_AA)
    dark=out[:124,:]
    cv2.rectangle(dark,(0,0),(min(w-1,620),123),(12,18,24),-1)
    status="TRACKED" if control.get("tracked") else "NO POSE - SHOW SHOULDERS"
    if not control.get("calibrated"):
        status=f"CALIBRATING {control.get('calibration',0)}% - HOLD STILL"
    cv2.putText(out,status,(10,22),cv2.FONT_HERSHEY_SIMPLEX,.58,
                (65,250,125) if control.get("tracked") else (0,180,255),2,cv2.LINE_AA)
    cv2.putText(out,f"X:{control.get('x',0):+.2f}  Z:{control.get('z',2.75):.2f}  SCALE:{control.get('scale',0):.3f}",
                (10,49),cv2.FONT_HERSHEY_SIMPLEX,.56,(245,235,205),1,cv2.LINE_AA)
    cv2.putText(out,f"HEAD:{control.get('head_roll',0):+.0f}deg  QUALITY:{control.get('confidence',0):.2f}  LANDMARKS:33",
                (10,76),cv2.FONT_HERSHEY_SIMPLEX,.54,(80,225,250),1,cv2.LINE_AA)
    arms=control.get("arm_tracking",{})
    if arms.get("left") and arms.get("right"):
        arm_text="ARMS OK: BOTH ELBOWS + WRISTS VISIBLE"
        arm_color=(65,245,135)
    else:
        arm_text="STEP BACK: SHOW BOTH ELBOWS + WRISTS"
        arm_color=(0,185,255)
    cv2.putText(out,arm_text,(10,105),cv2.FONT_HERSHEY_SIMPLEX,.50,arm_color,1,cv2.LINE_AA)
    return out
