"""Asynchronous webcam + MediaPipe worker.

The OpenGL/Pygame render thread is never blocked by camera capture or pose
inference. Only the newest frame is kept to avoid accumulating input lag.
"""
from __future__ import annotations

import threading
import time

import cv2

from .pose import SoloPose, draw_overlay


class PoseWorker:
    def __init__(self, camera=0, sensitivity=1.15):
        self.camera=camera
        self.sensitivity=sensitivity
        self.lock=threading.Lock()
        self.stop_flag=threading.Event()
        self.thread=None
        self.latest=None
        self.preview=None
        self.sequence=0
        self.pending_punch=None
        self.calibrate_requested=False
        self.error=None

    def start(self):
        self.thread=threading.Thread(target=self._run,name="webcam-pose",daemon=True)
        self.thread.start()

    def close(self):
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def request_calibrate(self):
        with self.lock:
            self.calibrate_requested=True

    def set_sensitivity(self, value):
        with self.lock:
            self.sensitivity=max(.70,min(2.0,float(value)))

    def snapshot(self):
        """Read the newest pose; consume a punch event only once."""
        with self.lock:
            if self.error:
                raise RuntimeError("Pose webcam worker failed: "+str(self.error))
            now=time.monotonic()
            if self.latest is None:
                return {"tracked":False,"head_roll":0.0,"head_offset":0.0,
                        "punch":None,"guard":False},None,self.sequence
            pose,received=self.latest
            control=pose.copy()
            if now-received>.32:
                control.update({"tracked":False,"punch":None,"guard":False,
                                "head_roll":0.0,"head_offset":0.0})
            else:
                control["punch"]=self.pending_punch
            self.pending_punch=None
            return control,self.preview,self.sequence

    def _open_camera(self):
        cap=cv2.VideoCapture(self.camera,cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap=cv2.VideoCapture(self.camera)
        if not cap.isOpened():
            raise RuntimeError("Webcam unavailable; close Zoom or try --camera 1")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,360)
        cap.set(cv2.CAP_PROP_FPS,30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        return cap

    def _run(self):
        cap=None
        tracker=None
        try:
            cap=self._open_camera()
            tracker=SoloPose(self.sensitivity)
            last_ts=-1
            last_preview=0.
            while not self.stop_flag.is_set():
                ok,frame=cap.read()
                if not ok:
                    if self.stop_flag.wait(.05):
                        break
                    continue
                # Use original camera orientation for reliable anatomical hand labels.
                # Mirror only the diagnostic preview AFTER inference.
                ts=max(int(time.monotonic()*1000),last_ts+1)
                last_ts=ts
                with self.lock:
                    cal=self.calibrate_requested
                    self.calibrate_requested=False
                    tracker.sensitivity=self.sensitivity
                if cal:
                    tracker.calibrate()
                control=tracker.process(frame,ts)
                now=time.monotonic()
                mini=None
                if now-last_preview>.095:
                    mini=cv2.flip(draw_overlay(frame,control),1)
                    last_preview=now
                with self.lock:
                    self.latest=(control,now)
                    if control.get("punch") is not None:
                        self.pending_punch=control["punch"]
                    if mini is not None:
                        self.preview=mini
                    self.sequence+=1
        except Exception as exc:
            with self.lock:
                self.error=exc
        finally:
            if tracker is not None:
                tracker.close()
            if cap is not None:
                cap.release()
