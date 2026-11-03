# AI BOXING - 2 PLAYERS (OpenCV + MediaPipe Pose + Pygame)

Game boxing 2D cho mon Xu ly anh. Hai nguoi dung truoc mot webcam:
- Player 1 dung o nua trai khung hinh.
- Player 2 dung o nua phai khung hinh.
- Dua tay ra truoc de thuc hien punch.
- Dua ca hai tay len cao de guard/block.
- Phim A va L co the dung de kiem tra game khi chua can webcam.

## 1. Yeu cau

- Windows 10/11 64-bit.
- Python 3.11 64-bit.
- Webcam co the nhin thay ca hai nguoi.
- Internet trong lan cai dat dau tien de tai thu vien va model MediaPipe.

Tai Python 3.11 tai: https://www.python.org/downloads/
Khi cai Python, tick **Add Python to PATH**.

## 2. Cai dat

1. Giai nen thu muc AI_Boxing_2P.
2. Mo thu muc vua giai nen.
3. Nhan dup setup.bat.
4. Cho den khi cai xong MediaPipe, Pygame va model Pose Landmarker.

Neu Windows hoi Firewall/camera permission, cho phep ung dung Python truy cap webcam.

## 3. Chay game

Nhan dup run.bat.

Hoac mo CMD tai thu muc project va chay:

~~~bat
.venv\Scripts\python.exe main.py
~~~

## 4. Cach choi

1. Dat webcam ngang tam nguc, cach hai nguoi khoang 2-3 met (tuy goc camera).
2. Hai nguoi dung canh nhau, khong che khuoc nhau:
   - Player 1 ben trai.
   - Player 2 ben phai.
3. Dam bao webcam thay ro vai, khuyu tay va co tay cua ca hai nguoi.
4. Dua mot tay ra truoc nhanh va duoi khuyu tay de tao punch.
5. Dua ca hai tay len cao de guard/block.
6. Nhan R de choi lai; ESC de thoat.

Phim test:
- A: Player 1 punch.
- L: Player 2 punch.
- R: restart.
- ESC: quit.

## 5. Cau truc source code

~~~text
AI_Boxing_2P/
|-- main.py
|-- pose_tracker.py
|-- boxing_game.py
|-- download_model.py
|-- requirements.txt
|-- setup.bat
|-- run.bat
|-- README.md
|-- assets/
    |-- pose_landmarker_lite.task  # Tu dong tai khi setup
~~~

## 6. Nguyen ly xu ly anh

1. OpenCV lay tung frame tu webcam va lat ngang de tao hinh anh nhu guong.
2. MediaPipe Pose Landmarker phat hien toi da 2 bo landmark trong cung frame.
3. Moi nguoi duoc gan theo vi tri ngang: trai = Player 1, phai = Player 2.
4. He thong theo doi landmark vai, khuyu tay va co tay.
5. Goc khuyu tay va toc do thay doi vi tri co tay duoc dung lam heuristic nhan dien punch.
6. Khi hai co tay duoc dua len cao, game nhan dien guard.
7. Pygame nhan su kien va cap nhat mau, hieu ung, thoi gian va ket qua.

## 7. Tinh chinh do nhay

Mo pose_tracker.py, tim doan dieu kien:
- elbow_angle > 148.0
- speed > 0.45

Giam speed neu phai dam rat manh moi nhan. Tang speed neu game tu nhan nham khi dang di chuyen tay thong thuong. Giam elbow_angle neu camera/goc dung khien khuyu tay khong duoc duoi gan thang.

Day la nguong heuristic ban dau, khong phai mo hinh phan loai boxing da duoc huan luyen. Hieu nang phu thuoc webcam, anh sang, khoang cach va tu the.

## 8. Loi thuong gap

### Khong mo duoc webcam
- Dong Zoom, Teams, OBS va ung dung Camera dang dung webcam.
- Trong main.py, doi CAMERA_INDEX = 0 thanh 1 neu webcam la camera thu hai.

### Khong tim thay model
Chay:
~~~bat
.venv\Scripts\python.exe download_model.py
~~~

### Loi import mediapipe / DLL
- Dung Python 3.11 64-bit.
- Chay lai setup.bat.
- Neu van loi, cai Microsoft Visual C++ Redistributable x64.

### Chi nhan dien duoc mot nguoi
- Hai nguoi can dung cach nhau, khong bi che khuat.
- Tang anh sang.
- Dam bao ca hai than tren va hai canh tay nam trong khung hinh.
- Pose Landmarker duoc cau hinh num_poses=2; tuy nhien chat luong nhan dien van phu thuoc model va camera.

## 9. Luu y an toan

Day la game dieu khien bang cu dong, khong phai bai tap boxing that. Khong dam vao nguoi choi khac, giu khoang trong xung quanh va dung lai neu thay dau, chong mat hoac met.
