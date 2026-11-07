"""Download optional higher-accuracy full Pose Landmarker model.

The original lite model remains available as a speed-focused fallback.
"""
from pathlib import Path
from urllib.request import urlretrieve

DEST = Path(__file__).resolve().parent / "assets" / "pose_landmarker_full.task"
URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"


def main():
    DEST.parent.mkdir(parents=True,exist_ok=True)
    if DEST.is_file() and DEST.stat().st_size > 1000000:
        print("[OK] Full model exists:",DEST)
        return
    print("[INFO] Downloading MediaPipe Pose Landmarker FULL model")
    try:
        urlretrieve(URL, DEST)
    except Exception:
        DEST.unlink(missing_ok=True)
        raise
    if DEST.stat().st_size < 1000000:
        DEST.unlink(missing_ok=True)
        raise RuntimeError("Model file is incomplete")
    print("[OK] FULL model ready:",DEST)


if __name__=="__main__":
    main()
