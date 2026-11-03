# AI-Boxing-2P

Game boxing 2D cho hai nguoi choi, dieu khien bang cu dong qua webcam, su dung OpenCV, MediaPipe Pose Landmarker va Pygame.

## Source code

Toan bo source code goc duoc dong goi trong file **AI_Boxing_2P_Windows.zip** tai repository nay. Giai nen file ZIP de lay thu muc `AI_Boxing_2P/` gom:

- `main.py` — webcam, xu ly frame va game loop.
- `pose_tracker.py` — MediaPipe Pose, gan nguoi choi va nhan dien punch/guard.
- `boxing_game.py` — giao dien, thanh mau, thoi gian va logic tran dau.
- `download_model.py` — tai model Pose Landmarker Lite.
- `requirements.txt` — cac thu vien Python.
- `setup.bat` — tao virtual environment, cai thu vien va tai model.
- `run.bat` — khoi dong game.
- `README.md` — huong dan su dung trong goi source.

## Yeu cau

- Windows 10/11 64-bit.
- Python 3.11 64-bit va da chon **Add Python to PATH** khi cai dat.
- Webcam nhin thay ca hai nguoi choi.
- Ket noi Internet trong lan cai dat dau tien.

## Cai dat va chay

1. Tai `AI_Boxing_2P_Windows.zip` tu repository va giai nen.
2. Mo thu muc `AI_Boxing_2P`.
3. Chay `setup.bat` va cho qua trinh cai dat hoan tat.
4. Chay `run.bat` de mo game.

## Cach choi

- Player 1 dung ben trai khung hinh; Player 2 dung ben phai.
- Dua mot tay ra truoc nhanh de punch.
- Dua ca hai co tay len cao gan/vuot vai de guard.
- `A`: test punch Player 1; `L`: test punch Player 2.
- `R`: restart; `ESC`: thoat.

## Luu y ky thuat

Nhan dien punch hien tai la heuristic dua tren goc khuyu tay, toc do co tay va co che re-arm/cooldown; day khong phai classifier boxing da duoc huan luyen. Ket qua phu thuoc vao anh sang, goc webcam, khoang cach va kha nang nhin thay landmark.

Model `pose_landmarker_lite.task` duoc tai tu dong boi `setup.bat`/`download_model.py`, khong can commit model vao repository.

## An toan

Day la game dieu khien bang cu dong, khong phai bai tap boxing that. Giu khoang cach an toan, khong dam vao nguoi choi khac va dung lai neu thay dau hoac met.