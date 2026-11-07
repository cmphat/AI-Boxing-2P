"""Time-aware smoothing and head-dodge geometry.

Math is independent of camera and renderer so it can be unit tested.
Inputs are MediaPipe normalized image coordinates.
"""
from __future__ import annotations
import math

def clamp(v, low, high):
    return max(low, min(high, v))

def smooth_value(current, target, dt, tau=.09):
    """Exponential response, independent of FPS."""
    if current is None:
        return float(target)
    alpha = 1.0 - math.exp(-clamp(dt, 0.0, .20) / max(.001, tau))
    return float(current + alpha * (target - current))

def deadband(v, threshold):
    """Continuous dead zone: no step discontinuity at threshold."""
    return math.copysign(max(0.0, abs(v) - threshold), v)

def head_measure(pts, vis):
    """Return (roll_deg, lateral_head_shift_in_shoulder_widths) or None.

    Image y increases downward; roll from eye line, or ear line if available.
    Relative head displacement is separated from torso translation.
    """
    if min(float(vis[11]), float(vis[12]), float(vis[0])) < .50:
        return None
    sx = (float(pts[11,0]) + float(pts[12,0])) * .5
    span = max(abs(float(pts[11,0]-pts[12,0])), .08)
    # Prefer eye corners (33-pose landmarks 2,5) for a stable tilt;
    # fall back to ears 7/8 when the eyes are hidden.
    if min(float(vis[2]), float(vis[5])) > .55:
        a, b = 2, 5
    elif min(float(vis[7]), float(vis[8])) > .55:
        a, b = 7, 8
    else:
        a, b = 11, 12
    # Use the magnitude of eye-line roll and preserve left/right sign.
    angle = math.degrees(math.atan2(float(pts[b,1]-pts[a,1]),
                                    float(pts[b,0]-pts[a,0])))
    if angle > 90.0:
        angle -= 180.0
    if angle < -90.0:
        angle += 180.0
    tilt = clamp(angle, -32.0, 32.0)
    relative_x = clamp((float(pts[0,0])-sx)/span, -1.6, 1.6)
    return tilt, relative_x

class HeadController:
    def __init__(self):
        self.base = None
        self.roll = 0.0
        self.offset = 0.0

    def reset(self):
        self.base = None
        self.roll = 0.0
        self.offset = 0.0

    def update(self, measurement, dt):
        if measurement is None:
            # Tracking lost: return the virtual camera gently to neutral.
            self.roll = smooth_value(self.roll, 0.0, dt, .30)
            self.offset = smooth_value(self.offset, 0.0, dt, .26)
        else:
            if self.base is None:
                self.base = measurement
            raw_roll, raw_offset = measurement
            base_roll, base_offset = self.base
            target_roll = clamp(deadband(raw_roll-base_roll, 2.0), -22.0, 22.0)
            target_offset = clamp(deadband(raw_offset-base_offset, .09) * .42, -.42, .42)
            self.roll = smooth_value(self.roll, target_roll, dt, .11)
            self.offset = smooth_value(self.offset, target_offset, dt, .12)
        return self.roll, self.offset
