# AI-Boxing-2P

Game boxing 2D cho mon Xu ly anh. Nguoi choi dieu khien nhan vat bang cu dong truoc webcam, su dung OpenCV, MediaPipe Pose Landmarker va Pygame.

## Game modes

### PVE - Player vs Bot
- Mot nguoi choi dieu khien bang webcam.
- Bot tu dong tan cong va phong thu theo state machine.
- Co 3 muc do: Easy, Normal, Hard.
- Do kho thay doi tan suat tan cong, sat thuong va xac suat guard.

### PVP - Player vs Player
- Hai nguoi cung dung truoc mot webcam.
- Player 1 dung ben trai; Player 2 dung ben phai.
- Ca hai nguoi deu duoc nhan dien pose va gesture bang MediaPipe.

## Requirements
- Windows 10/11 64-bit.
- Python 3.11 64-bit.
- Webcam va ket noi Internet trong lan cai dat dau tien.

Tai Python: https://www.python.org/downloads/
Khi cai dat Python, chon **Add Python to PATH**.

## Setup
1. Tai repository bang nut Code > Download ZIP va giai nen.
2. Mo thu muc project.
3. Chay setup.bat.
4. Cho den khi cac thu vien va model MediaPipe duoc cai xong.
5. Chay run.bat.

## Controls
### Main menu
- 1: PVE (Player vs Bot).
- 2: PVP (Player vs Player).
- E: Bot Easy.
- N: Bot Normal.
- H: Bot Hard.
- ESC: Thoat.

### During a match
- Dua tay ra truoc nhanh va duoi khuyu tay de Punch.
- Dua ca hai co tay len cao gan/vuot vai de Guard.
- A: test punch Player 1.
- L: test punch Player 2 (chi dung trong PVP).
- R: Choi lai.
- M: Quay ve menu.
- ESC: Thoat.

## Source layout
- main.py: webcam, OpenCV frame processing va game loop.
- pose_tracker.py: MediaPipe Pose, gan nguoi choi va nhan dien Punch/Guard.
- boxing_game.py: menu, PVE/PVP, bot AI, HP, timer va giao dien 2D.
- download_model.py: tai model Pose Landmarker Lite.
- requirements.txt: cac thu vien Python.
- setup.bat: cai dat tu dong tren Windows.
- run.bat: khoi dong game.

## Image-processing pipeline
1. OpenCV thu frame webcam, mirror, resize va chuyen BGR sang RGB.
2. MediaPipe Pose Landmarker phat hien toi da hai bo landmark.
3. Trong PVP, hai nguoi duoc sap xep trai-phai. Trong PVE, nguoi duy nhat luon duoc gan cho Player 1.
4. He thong theo doi vai, khuyu tay va co tay.
5. Goc khuyu tay va van toc co tay tao heuristic Punch; vi tri hai co tay tao heuristic Guard.
6. Game engine nhan gesture va cap nhat nhan vat, mau, timer va ket qua.
7. Trong PVE, Bot AI su dung state machine don gian de chon tan cong hoac phong thu.

## Gesture recognition notes
Punch hien tai la heuristic dua tren goc khuyu tay, van toc co tay, re-arm va cooldown; day khong phai classifier boxing duoc huan luyen rieng. Nguong co the can tinh chinh theo webcam, anh sang, khoang cach va goc dung.

Bot hien tai la AI theo luat/state machine, khong phai neural network. Ba muc do dieu chinh tan suat tan cong, sat thuong va xac suat phong thu.

## Troubleshooting
- Khong mo duoc webcam: dong Zoom/Teams/OBS; thu doi CAMERA_INDEX = 0 thanh 1 trong main.py.
- Khong tim thay model: chay python download_model.py trong virtual environment.
- Loi thu vien: dung Python 3.11 64-bit va chay lai setup.bat.
- Chi nhan dien mot nguoi trong PVP: tang anh sang, dung cach nhau va dam bao khong che khuat vai/khuu/co tay.

## Safety
Day la game dieu khien bang cu dong, khong phai bai tap boxing that. Khong dam vao nguoi choi khac; giu khoang trong an toan va dung lai neu met hoac chong mat.
