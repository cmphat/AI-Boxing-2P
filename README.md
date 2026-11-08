# AI-Boxing-2P

Do an mon Xu ly anh: dieu khien game boxing bang cu dong co the tu webcam.

## Huong phat trien hien tai: Y8 Pose Controller

Thay vi tu viet lai mot game boxing, project dung **Punch Boxing Championship** tren Y8 lam moi truong mo phong 3D:

https://vi.y8.com/games/punch_boxing_championship

Pipeline:

```text
Webcam
  -> OpenCV
  -> MediaPipe Pose Landmarker
  -> EMA smoothing
  -> Gesture state machine
  -> Boxing action
  -> pynput keyboard event
  -> Y8 Punch Boxing Championship
```

Game Y8 chi nhan keyboard o cua so dang focus. Python khong sua game va khong can truy cap source cua Y8; no chi bien cu dong webcam thanh phim bam nhu mot bo dieu khien ngoai.

## Mapping dong tac

| Dong tac nguoi choi | Phim game |
|---|---|
| Dam thang tay trai | Q |
| Dam thang tay phai | A |
| Uppercut trai | Y |
| Uppercut phai | W |
| Hook trai | T |
| Hook phai | E |
| Overhand trai | I |
| Overhand phai | U |
| Dua hai tay len che mat | giu S - Block |
| Nghieng/luon dau sang ben | D - Dodge |

Game goc su dung Q/A cho cross punch, W/Z cho right uppercut, Y left uppercut, E right hook, T left hook, U/I overhand, D dodge va S block.

## Vi sao controller nay it nhan nham hon

Controller khong bam phim ngay khi thay co tay di chuyen. Moi frame duoc xu ly qua:

1. **EMA landmark smoothing** de giam rung.
2. **Visibility gate**: chi nhan khi vai, khuyu va co tay du ro.
3. **Arm state machine**: tay phai co lai/re-arm truoc khi ghi nhan cu dam tiep theo.
4. **Velocity + elbow extension**: phai vua du nhanh vua duoi tay.
5. **Per-arm cooldown**: ngan mot cu dam bi tinh nhieu lan.
6. **Guard priority**: khi dang block thi punch bi khoa.
7. **Dodge hysteresis**: phai tro ve trung tam moi co the dodge lan tiep.

## Cai dat Windows

Khuyen dung Windows 10/11 64-bit va Python 3.11 64-bit.

### Cach nhanh

1. Clone/download repository.
2. Chay:

```bat
setup_y8.bat
```

Script se:
- tao `.venv`
- cai OpenCV, MediaPipe, pynput...
- tai Pose Landmarker model.

3. Sau khi xong, chay:

```bat
run_y8_controller.bat
```

Controller se tu mo trang game Y8.

## Cach choi

1. Trong browser, vao Quick Mode/Tournament/Career va bat dau tran dau bang chuot.
2. Dat webcam sao cho thay **dau, hai vai, hai khuyu tay va hai co tay**.
3. Dung cach webcam khoang 1.5-2.5 m tuy goc camera.
4. Cho debug hien `POSE: OK`.
5. Dung tu the binh thuong mot luc de controller lay neutral pose.
6. Click vao khung game Y8 de game nhan keyboard.
7. Bam **F8** de bat dieu khien pose.
8. Bat dau dam / block / dodge.

### Hotkeys controller

| Phim | Chuc nang |
|---|---|
| F8 | Bat/tat gui phim vao game |
| F9 | Recalibrate neutral pose |
| F10 | Thoat controller |

> Khi control ON, hay de browser/game la cua so dang focus. Cua so webcam chi de debug.

## File moi cho Y8 controller

```text
gesture_engine.py       # MediaPipe + smoothing + gesture classifier
key_output.py           # gui tap/hold keyboard an toan
y8_controller.py        # webcam loop + debug + mo Y8
setup_y8.bat            # cai dat tren Windows
run_y8_controller.bat   # chay controller
download_model.py       # tai pose model
assets/                 # model duoc tai vao day
```

## Source game cu

Cac file `main.py`, `boxing_game.py`, `pose_tracker.py`... van duoc giu trong repository de tham khao va so sanh. Huong demo de nop mon nen dung **Y8 Pose Controller**.

## Tinh chinh do nhay

Trong `gesture_engine.py`, cac nguong chinh gom:

- arm cooldown: `0.34 s`
- elbow extension: `> 146 deg`
- punch speed: `> 1.55` shoulder-width / second
- dodge lean: `> 0.34` shoulder-width

Neu bi tu dam:
- tang punch speed threshold.
- tang elbow extension threshold.

Neu dam that nhung kho nhan:
- giam punch speed threshold tung chut.
- dung xa camera hon de thay tron canh tay.

Khong nen giam cooldown qua thap vi mot cu dam co the tao nhieu key event.

## Luu y

Day la controller phuc vu demo xu ly anh. Khong dam vao nguoi khac, giu khoang trong xung quanh khi choi.

## Bo cuc cua so moi

Khi chay `run_y8_controller.bat`, controller se tu dong chia man hinh:

- Ben trai: Y8 mo bang **app window rieng**, khong co tab va thanh dia chi.
- Ben phai: cua so webcam/debug nho gon.
- Ty le mac dinh: game ~72% chieu rong man hinh, camera ~28%.

Controller uu tien Microsoft Edge, sau do Google Chrome. Trinh duyet duoc mo voi che do `--app`, nen nhin nhu mot ung dung rieng thay vi mot tab trinh duyet.

Neu muon game rong hon, sua trong `y8_controller.py`:

```python
GAME_SCREEN_RATIO = 0.72
```

Vi du:
- `0.78`: game rong hon, camera hep hon.
- `0.68`: camera rong hon.
