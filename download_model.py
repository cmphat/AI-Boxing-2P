from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
MODEL_PATH = ASSET_DIR / "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/"
    "pose_landmarker_lite.task"
)


def main():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        print(f"[OK] Pose Landmarker LITE da co: {MODEL_PATH}")
        return

    print("[INFO] Dang tai MediaPipe Pose Landmarker LITE (nhanh)...")
    try:
        urlretrieve(MODEL_URL, MODEL_PATH)
    except Exception as exc:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        raise SystemExit(
            "Khong tai duoc model LITE. Kiem tra Internet va chay lai setup.bat.\n"
            + str(exc)
        )

    if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size < 1_000_000:
        raise SystemExit("Model LITE tai ve khong hop le. Hay chay lai download_model.py.")

    print(f"[OK] Model LITE: {MODEL_PATH}")
    print(f"[INFO] Size: {MODEL_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
