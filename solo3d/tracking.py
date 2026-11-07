"""Pure motion mapping: normalized MediaPipe body landmarks -> stable virtual X/Z.

Separate from MediaPipe/OpenGL so synthetic test data can validate controls.
The output is a *relative virtual displacement*, not measured physical meters.
"""
from __future__ import annotations

import math
from collections import deque


def clamp(value, low, high):
    return max(low, min(high, float(value)))


def exp_lerp(current, target, dt, tau=0.10):
    if current is None:
        return float(target)
    a = 1.0 - math.exp(-clamp(dt, 0, .25) / max(.001, tau))
    return float(current + (target-current)*a)


def signed_deadzone(value, zone):
    return math.copysign(max(0.0, abs(value)-zone), value)


def body_measure(points, visibility, confidence=.35):
    """Returns body center, apparent body scale, signal quality or None.

    As long as shoulders are available movement tracking can work; missing
    hips/legs should NOT block the camera from moving.
    """
    if min(float(visibility[11]),float(visibility[12])) < confidence:
        return None
    sx = (float(points[11][0])+float(points[12][0]))*.5
    sy = (float(points[11][1])+float(points[12][1]))*.5
    width = math.hypot(float(points[12][0]-points[11][0]),
                       float(points[12][1]-points[11][1]))
    width=clamp(width,.045,.75)
    hips_visible=min(float(visibility[23]),float(visibility[24])) >= confidence
    if hips_visible:
        hy=(float(points[23][1])+float(points[24][1]))*.5
        hx=(float(points[23][0])+float(points[24][0]))*.5
        torso=clamp(math.hypot(hx-sx,hy-sy),.07,.8)
        # Torso contributes the scale when the user rotates shoulders.
        scale=.50*width+.50*torso
        center=.75*sx+.25*hx
    else:
        scale=width
        center=sx
    quality=(float(visibility[11])+float(visibility[12]))*.5
    return (center, scale, quality)


class RelativeMovement:
    """Multi-frame calibration, range checks, frame-time smoothing and telemetry.

    Given a front-facing camera, moving closer increases apparent shoulder/torso
    scale and reduces virtual Z. Horizontal center motion maps to virtual X.
    """
    def __init__(self, calibration_frames=12):
        self.calibration_frames=int(calibration_frames)
        self.reset()

    def reset(self):
        self.samples=deque(maxlen=max(self.calibration_frames,1))
        self.baseline=None
        self.center=None
        self.scale=None
        self.x=None
        self.z=None
        self.last_quality=0.

    @property
    def ready(self):
        return self.baseline is not None

    @property
    def progress(self):
        if self.ready:
            return 100
        return round(100*len(self.samples)/self.calibration_frames)

    def update(self, body, dt):
        """body=(center, apparent_scale, confidence) or None."""
        if body is None:
            return self.output(False)
        center,scale,quality=body
        self.last_quality=float(quality)
        if not (math.isfinite(center) and math.isfinite(scale) and .045<scale<.8):
            return self.output(False)
        if self.baseline is None:
            self.samples.append((center,scale))
            if len(self.samples)>=self.calibration_frames:
                self.baseline=(
                    sum(p[0] for p in self.samples)/len(self.samples),
                    sum(p[1] for p in self.samples)/len(self.samples)
                )
                self.center=center
                self.scale=scale
                self.x=0.
                self.z=2.75
            return self.output(True)
        bc,bs=self.baseline
        self.center=exp_lerp(self.center,center,dt,.055)
        self.scale=exp_lerp(self.scale,scale,dt,.095)
        # Relative 3D movement is scaled by baseline body size: this makes
        # the same relative motion work at different distances from the webcam.
        dx=(self.center-bc)/max(.065,bs)
        ratio=clamp(self.scale/max(.065,bs),.6,1.7)
        x_target=clamp(signed_deadzone(dx,.11)*2.2,-2.85,2.85)
        z_target=clamp(2.75-signed_deadzone(ratio-1,.045)*10,.40,3.85)
        self.x=exp_lerp(self.x,x_target,dt,.10)
        self.z=exp_lerp(self.z,z_target,dt,.13)
        return self.output(True)

    def output(self, tracked):
        return {
            "tracked":bool(tracked),
            "calibrated":self.ready,
            "calibration":self.progress,
            "x":float(self.x if self.x is not None else 0),
            "z":float(self.z if self.z is not None else 2.75),
            "center":float(self.center if self.center is not None else .5),
            "scale":float(self.scale if self.scale is not None else 0),
            "baseline_scale":float(self.baseline[1] if self.baseline else 0),
            "quality":float(self.last_quality),
        }
