"""Anatomical left/right hand mapping from an UNMIRRORED camera image.

MediaPipe Pose:
  LEFT_SHOULDER=11, LEFT_ELBOW=13, LEFT_WRIST=15
  RIGHT_SHOULDER=12, RIGHT_ELBOW=14, RIGHT_WRIST=16

Tracking runs BEFORE the webcam preview is horizontally mirrored.
Only the preview is mirrored for a natural selfie display.

Returned positions are offsets in first-person camera coordinates:
X positive -> physical right, Y positive -> higher, Z positive -> reach forward.
"""
from __future__ import annotations
import math


def clamp(x, a, b):
    return max(a, min(b, float(x)))


ARMS={"left":(11,13,15), "right":(12,14,16)}


def pose_hands(points, visibility, minimum_visibility=.42):
    """Create independent targets, returning None for an occluded arm."""
    a,b=points[11],points[12]
    shoulder_width=max(math.hypot(float(a[0]-b[0]),float(a[1]-b[1])),.085)
    result={}
    for hand,(shoulder_i,elbow_i,wrist_i) in ARMS.items():
        if min(float(visibility[i]) for i in (shoulder_i,elbow_i,wrist_i))<minimum_visibility:
            result[hand]=None
            continue
        shoulder=points[shoulder_i]
        wrist=points[wrist_i]
        # A front-facing unmirrored camera sees a player's real right hand
        # on image-left. Reverse camera image X for first-person local X.
        horizontal=-(float(wrist[0]-shoulder[0]))/shoulder_width
        vertical=-(float(wrist[1]-shoulder[1]))/shoulder_width
        depth=-(float(wrist[2]-shoulder[2]))/shoulder_width
        result[hand]=(
            clamp(horizontal*.25,-.28,.28),
            clamp(vertical*.25,-.24,.31),
            clamp(depth*.25,-.15,.55),
        )
    return result


def flip_world_controls(control):
    """Camera faces the player; convert its image X to player-local X."""
    c=dict(control)
    for k in ("x","head_offset","head_roll"):
        if k in c:
            c[k]=-float(c[k])
    return c
