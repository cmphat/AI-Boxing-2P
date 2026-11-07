"""Map anatomical 33-point MediaPipe pose to a humanoid robot skeleton.

This is a pose-retargeting prototype with procedural articulated armor.
All geometry comes from landmarks, not from canned punch animation.
"""
from __future__ import annotations
import math


BONES = (
    ("left_shoulder","left_elbow"),("left_elbow","left_wrist"),
    ("right_shoulder","right_elbow"),("right_elbow","right_wrist"),
    ("left_hip","left_knee"),("left_knee","left_ankle"),
    ("right_hip","right_knee"),("right_knee","right_ankle"),
    ("left_shoulder","right_shoulder"),("left_hip","right_hip"),
    ("left_shoulder","left_hip"),("right_shoulder","right_hip"),
    ("hip_center","neck"),("neck","head"),
)
POSE_INDICES = {
    "head":0,
    "left_shoulder":11,"right_shoulder":12,
    "left_elbow":13,"right_elbow":14,
    "left_wrist":15,"right_wrist":16,
    "left_hip":23,"right_hip":24,
    "left_knee":25,"right_knee":26,
    "left_ankle":27,"right_ankle":28,
}
REST = {
    "head":(0.,2.30,0.),
    "neck":(0.,1.93,0.),
    "left_shoulder":(-.47,1.84,0.),
    "right_shoulder":(.47,1.84,0.),
    "left_elbow":(-.70,1.42,.04),
    "right_elbow":(.70,1.42,.04),
    "left_wrist":(-.45,1.42,.42),
    "right_wrist":(.45,1.42,.42),
    "left_hip":(-.24,.97,0.),
    "right_hip":(.24,.97,0.),
    "left_knee":(-.25,.53,.04),
    "right_knee":(.25,.53,.04),
    "left_ankle":(-.25,.14,.07),
    "right_ankle":(.25,.14,.07),
    "hip_center":(0.,.97,0.),
}
def clamp(v,lo,hi):
    return max(lo,min(hi,float(v)))


def retarget_pose(landmarks, visibility, mirror=False, min_conf=.36):
    """Return stable anatomical joints in robot meters or a rest pose.

    Convention: player-right is positive X, upward is positive Y, cameraward
    is positive Z. MediaPipe receives original (non-selfie-flipped) video.
    """
    out=dict(REST)
    if landmarks is None or visibility is None:
        return out
    pts=landmarks
    vis=visibility
    valid=lambda i: i<len(pts) and float(vis[i])>=min_conf
    anchors=[i for i in (11,12,23,24) if valid(i)]
    if 11 not in anchors or 12 not in anchors:
        return out
    shoulder_c=((float(pts[11][0])+float(pts[12][0]))*.5,
                (float(pts[11][1])+float(pts[12][1]))*.5,
                (float(pts[11][2])+float(pts[12][2]))*.5)
    hips_available=23 in anchors and 24 in anchors
    if hips_available:
        hip_c=tuple((float(pts[23][j])+float(pts[24][j]))*.5 for j in range(3))
        unit=max(.13,math.dist(shoulder_c[:2],hip_c[:2]))
    else:
        hip_c=(shoulder_c[0],shoulder_c[1]+.23,shoulder_c[2])
        unit=.23
    # Map torso hip centroid to (0,.97,0); camera X is inverted to person X.
    side=1. if mirror else -1.
    for name,idx in POSE_INDICES.items():
        if not valid(idx):
            continue
        p=pts[idx]
        x=side*(float(p[0])-hip_c[0])/unit*.90
        y=.97-(float(p[1])-hip_c[1])/unit*.90
        z=-(float(p[2])-hip_c[2])/unit*.48
        if name=="head":
            y+=.13
        out[name]=(clamp(x,-1.8,1.8),clamp(y,.08,3.0),clamp(z,-1.1,1.4))
    ls,rs=out["left_shoulder"],out["right_shoulder"]
    out["neck"]=tuple((ls[j]+rs[j])*.5 for j in range(3))
    lh,rh=out["left_hip"],out["right_hip"]
    out["hip_center"]=tuple((lh[j]+rh[j])*.5 for j in range(3))
    # Do not allow a left/right swap caused by image mirroring: semantic
    # joint names remain fixed, regardless of the user's image-space side.
    return out


class SmoothRobotPose:
    def __init__(self):
        self.joints=dict(REST)
        self.initialized=False

    def update(self, targets, dt):
        alpha=1.0-math.exp(-clamp(dt,0,.20)/.075)
        for key,value in targets.items():
            prev=self.joints[key]
            self.joints[key]=tuple(prev[i]+(float(value[i])-prev[i])*alpha for i in range(3))
        self.initialized=True
        return self.joints
