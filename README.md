# AI-Boxing-2P — Pose Controller V2

Ban V2 la bo dieu khien webcam cho Punch Boxing Championship tren Y8. main.py doc lap, khong import game Pygame cu.

## Pipeline xu ly anh

Webcam -> OpenCV -> MediaPipe Pose Landmarker FULL -> 3D landmarks -> body-relative coordinates -> temporal velocity -> gesture state machine -> Win32 SendInput -> Y8.

## Diem moi

- Dung model Pose Landmarker FULL thay cho LITE.
- MediaPipe LIVE_STREAM chay bat dong bo de khong lam dung khung hinh camera.
- Theo doi toi da 2 pose va uu tien nguoi gan camera/co vai ro nhat.
- Hien skeleton vai, khuyu, co tay, dau va than tren preview.
- Dung world landmarks 3D va toa do tuong doi theo chieu rong vai.
- Tinh van toc tren cua so thoi gian ngan, khong lay sai khac 1 frame don le.
- State machine bat buoc rut tay ve truoc khi nhan cu dam tiep theo.
- Dung Win32 SendInput de gui phim, co test Q va kiem tra cua so game dang focus.
- Cua so camera nho, Always on Top, nam ben phai; game duoc ep ve ben trai.

## Cai dat

Windows 10/11, Python 3.11 64-bit, webcam, Edge/Chrome hoac Firefox.

1. Tai ZIP va giai nen.
2. Chay setup.bat (tai model FULL, co the mat vai phut).
3. Chay run.bat.

## Cach choi

1. Game Punch Boxing Championship mo o ben trai.
2. Chon Quick Mode va bat dau tran.
3. Dat webcam cach nguoi khoang 1.5-2.5 m. Khung hinh can thay dau, vai, khuyu tay, co tay va toi thieu den eo.
4. Chi de mot nguoi trong khung hinh. Neu co nguoi khac dung gan camera hon, model co the chon nham nguoi.
5. Dung thang, hai tay tha long trong 1 giay de lay moc dau.
6. Click vao vung game.
7. Nhan F8 hoac nut BAT DIEU KHIEN. Khi dang bat, game phai la cua so duoc focus.

## Mapping

- Tay trai dam thang/cross: Q
- Tay phai dam thang/cross: A
- Uppercut trai: Y
- Uppercut phai: W
- Hook trai: T
- Hook phai: E
- Overhand trai: I
- Overhand phai: U
- Hai tay dua len bao dau: giu S
- Nghieng dau sang ben: D

## Hotkeys

- F7: test gui phim Q vao game.
- F8: bat/tat dieu khien.
- F9: can chinh lai moc dau.
- F10: thoat.

## Cach doc trang thai

- GOOD FRAMING: khung hinh co ban dat yeu cau.
- STEP BACK: nguoi dang qua gan camera.
- KEEP BOTH HANDS INSIDE FRAME: co tay ra ngoai khung.
- SHOW BOTH ARMS: landmark vai/khuyu/co tay chua ro.
- CLICK GAME: game chua duoc focus, controller se khong gui phim vao ung dung khac.

## Tinh chinh

Trong main.py:
- PUNCH_COOLDOWN: thoi gian chong lap.
- PUNCH_MIN_ANGLE: nguong duoi khuyu.
- forward_speed > 0.32: nguong tien ve camera cho cross.
- CAMERA_INDEX: doi 0 thanh 1 neu webcam khong phai camera mac dinh.

Luu y: Pose estimation phu thuoc goc camera, anh sang va viec co du ca hai tay trong khung. Nen test F7 truoc; neu Q khong tao cu dam thi can kiem tra focus/game key mapping truoc khi tinh chinh pose.
