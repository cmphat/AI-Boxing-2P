# AI-Boxing-2P — Y8 Pose Controller

Ban chay chinh da duoc viet lai doc lap. main.py khong import cac module game Pygame cu.

## Giao dien
- Game mo trong cua so Edge/Chrome App: khong tab, khong thanh dia chi.
- Game nam ben trai.
- Camera nam trong cua so Tkinter co kich thuoc co dinh, nho gon ben phai.
- Camera hien skeleton, Pose, action va FPS.
- Dung trang toan cau: https://www.y8.com/games/punch_boxing_championship

## Cai dat
Yeu cau Windows 10/11, Python 3.11 64-bit, Edge hoac Chrome va webcam.

1. Tai ZIP repository va giai nen.
2. Chay setup.bat.
3. Chay run.bat.

setup.bat tao .venv, cai OpenCV, MediaPipe, pynput, Pillow va tai model Pose Landmarker Lite.

## Cach choi
1. Game Y8 mo ben trai.
2. Dung chuot chon Quick Mode va bat dau tran.
3. Dung truoc webcam sao cho thay dau, hai vai, khuyu tay va co tay.
4. Dung thang khoang 1 giay de controller lay neutral pose.
5. Click vao game de game nhan ban phim.
6. Bam F8 hoac nut BAT DIEU KHIEN tren cua so camera.

## Mapping
- Dam thang trai: Q
- Dam thang phai: A
- Uppercut trai: Y
- Uppercut phai: W
- Hook trai: T
- Hook phai: E
- Overhand trai: I
- Overhand phai: U
- Hai tay che dau: giu S (Block)
- Nghieng dau sang ben: D (Dodge)

Hotkeys:
- F8 bat/tat dieu khien.
- F9 hieu chinh lai tu the.
- F10 thoat controller.

## Cai gi da duoc sua
- main.py duoc thay the hoan toan bang controller Y8 doc lap.
- run.bat va run_y8_controller.bat deu chay main.py moi, khong con mo game Pygame cu.
- Doi URL tu vi.y8.com sang www.y8.com.
- Bo cua so cv2.imshow co the phong to tran man hinh; camera hien trong panel Tkinter co dinh 460 x 390.
- Camera khong con phu thuoc vao cac module cu.

## Tinh chinh
Trong main.py:
- CAMERA_PANEL_W: do rong cua so camera.
- CAMERA_PANEL_H: chieu cao cua so camera.
- speed > 1.35: nguong toc do cu dam.
- punch_cooldown = 0.38: chong nhan lap.

Neu nhan dam nham, tang speed threshold len 1.6-1.9. Neu kho nhan cu dam, giam xuong 1.1-1.2.

Luu y: Khi F8 bat, cua so game phai duoc focus de nhan phim. Hieu qua phu thuoc camera, anh sang va vi tri dung.
