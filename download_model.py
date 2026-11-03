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
        print(f"[OK] Model da co: {MODEL_PATH}")
        return

    print("[INFO] Dang tai MediaPipe Pose Landmarker Lite...")
    try:
        urlretrieve(MODEL_URL, MODEL_PATH)
    except Exception as exc:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        raise SystemExit(
            "Khong tai duoc model. Kiem tra Internet va chay lai "
            "python download_model.py\nChi tiet: " + str(exc)
        )

    if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size < 1_000_000:
        raise SystemExit("File model tai ve khong hop le. Hay tai lai.")
    print(f"[OK] Da tai model: {MODEL_PATH}")
    print(f"[INFO] Kich thuoc: {MODEL_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
