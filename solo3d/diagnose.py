"""Standalone webcam diagnostic: 33-landmark skeleton, raw motion metrics.

Run: .venv\\Scripts\\python.exe -m solo3d.diagnose
No Pygame, no OpenGL: isolates the real camera/pose issue from the game.
"""
from __future__ import annotations
import argparse
import csv
import time
from pathlib import Path

import cv2
from .pose import SoloPose, draw_overlay


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--camera",type=int,default=0)
    parser.add_argument("--record",action="store_true",help="Write motion_log.csv")
    args=parser.parse_args()

    cap=cv2.VideoCapture(args.camera,cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap=cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Webcam cannot be opened. Close Zoom/Teams and try --camera 1")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,540)
    cap.set(cv2.CAP_PROP_FPS,30)

    tracker=SoloPose()
    fh=None
    try:
        if args.record:
            fh=open("motion_log.csv","w",newline="",encoding="utf-8")
            writer=csv.writer(fh)
            writer.writerow(["time","tracked","calibration","x","z","scale","baseline_scale",
                             "head_roll","head_offset","confidence","shoulder_px","punch"])
        last_ts=-1
        print("Full-body pose diagnostic: move LEFT/RIGHT, FRONT/BACK; tilt HEAD.")
        print("C=calibrate, Q/ESC=exit, S=save screenshot, --record=CSV measurements")
        while True:
            ok,frame=cap.read()
            if not ok:
                print("Camera read failed; retrying")
                time.sleep(.1)
                continue
            # Inference uses unmirrored image for left/right correctness.
            last_ts=max(last_ts+1,int(time.monotonic()*1000))
            ctl=tracker.process(frame,last_ts)
            overlay=draw_overlay(frame,ctl,mirrored=True)
            cv2.putText(overlay,"C CALIBRATE | Q QUIT | S SAVE IMAGE",
                        (8,overlay.shape[0]-13),cv2.FONT_HERSHEY_SIMPLEX,.67,(255,255,255),2)
            cv2.imshow("AI Boxing - 33 Landmark Tracking Diagnosis",overlay)
            if fh is not None:
                writer.writerow([round(time.monotonic(),3),int(ctl["tracked"]),
                     ctl.get("calibration",0),round(ctl.get("x",0),3),
                     round(ctl.get("z",0),3),round(ctl.get("scale",0),4),
                     round(ctl.get("baseline_scale",0),4),
                     round(ctl.get("head_roll",0),2),round(ctl.get("head_offset",0),3),
                     round(ctl.get("confidence",0),3),round(ctl.get("shoulder_px",0),1),
                     ctl.get("punch") or ""])
            key=cv2.waitKey(1)&0xFF
            if key in (27,ord("q")):
                break
            if key==ord("c"):
                tracker.calibrate()
                print("Recalibration requested. Stand neutral until 100%.")
            if key==ord("s"):
                filename=Path.cwd()/f"tracking_{int(time.time())}.png"
                cv2.imwrite(str(filename),overlay)
                print("Saved:",filename)
    finally:
        if fh: fh.close()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__=="__main__":
    main()
