# AI BOXING SOLO 3D – First Person + Coordinates + Moving Bot

## Latest: First-person rig V2 – compact arms, visible joints, clearer tracking

- **First-person remains the default.** Tab is only an optional third-person robot debug view.
- The previous arm renderer placed large gloves only 0.38 m from the camera and used 26 cm glove spheres. That made the gloves fill the screen and hid the elbow movement. V2 moves the rig to a stable camera-space depth of about 1.08 m and uses compact gloves and thinner forearms.
- Each arm now has independently smoothed shoulder, elbow and wrist joints. Upper arm, elbow hinge, forearm, wrist cuff, knuckle plate and glove are separate rendered parts.
- The opponent has a smoother procedural body, articulated arms and legs, two-sided guard, left/right punch animation, idle movement and hit recoil. The ring uses a darker canvas, corner pads, audience boards and overhead lights.
- **The HUD reports whether both elbows and wrists are actually visible.** It no longer claims "L/R glove tracking" when the webcam only sees the user's face and shoulders.
- The webcam overlay says **STEP BACK: SHOW BOTH ELBOWS + WRISTS** when arm landmarks are missing.
- The physical RIGHT glove keeps its gold wrist strap; anatomical mapping remains based on the original, unmirrored webcam frame.

### Important webcam framing – this is required for arm movement

1. Put the webcam far enough away to show your head, shoulders, **both elbows and both wrists** at the same time. A face-only or head-and-shoulders crop cannot drive elbow and wrist joints.
2. Stand about 1.5–2 m from the webcam as a starting point; adjust until both arms fit in the preview. Keep the camera around chest/shoulder height and improve room lighting.
3. Keep your upper arms and wrists inside the image while punching. If a wrist leaves the frame or is hidden behind your torso, that arm temporarily falls back to its neutral pose.
4. Press `C` to recalibrate while standing in the final playing position.
5. Raise one arm at a time. The HUD should show `ARMS TRACKED L ✓ R ✓` before expecting both gloves to follow.

### How to verify handedness on Windows

1. Update the `main` branch and run `setup_3d.bat` (existing installations usually only need the source files updated).
2. Run `run_solo_3d.bat`; stand far enough back for the complete upper body and both arms to fit.
3. Check the camera overlay and top HUD. If either arm is not visible, change camera distance/angle before testing the gloves.
4. Raise your right hand: only the right glove with the gold strap should move. Repeat with the left hand.
5. `run_tracking_diagnostics.bat` shows all visible MediaPipe landmarks for deeper troubleshooting.

A single webcam cannot estimate hidden joints. No renderer can animate a wrist that is outside the camera image; V2 makes this limitation explicit instead of pretending the arm is tracked.


## QUAN TRỌNG: kiểm tra chuyển động TRƯỚC khi chơi (Tracking V2)

Bản trước có thể trông như không di chuyển khi hông ra ngoài khung hình. Bản này dùng hai vai để theo dõi tiếp, lấy mẫu hiệu chuẩn 12 frame và vẽ đủ **33 điểm MediaPipe** (chỉ các điểm nhìn thấy được mới hiển thị). Dùng **Pose Full** tự động nếu setup tải được, nếu không dùng Lite.

**Bước 1:** Tải lại source nhánh `main`, chạy `setup_3d.bat` để cài đầy đủ.

**Bước 2:** Chạy `run_tracking_diagnostics.bat` thay vì vào game ngay. Đây là cửa sổ webcam riêng, không cần OpenGL. Nó hiện:
- `CALIBRATING XX%`: đứng yên và hướng mặt vào camera cho tới 100%.
- `TRACKED` + `X, Z`: sang trái thì X giảm; sang phải X tăng; bước gần camera thì Z giảm; lùi thì Z tăng.
- `SCALE`: kích thước cơ thể ước lượng trên ảnh, tăng khi đến gần webcam.
- `HEAD`: góc nghiêng đầu; `QUALITY`: độ tin cậy vai.
- Đầy đủ 33 điểm landmark và các xương nối khi có độ tin cậy phù hợp.
- `C` hiệu chuẩn lại, `S` lưu ảnh, `Q` thoát.
- CSV `motion_log.csv` được lưu tại thư mục bạn chạy tool.

**Bước 3:** Khi X/Z thay đổi trong chẩn đoán, mở `run_solo_3d.bat`. Bấm **B** để làm bot đứng yên, sau đó đi tiến/lùi hoặc trái/phải để tự kiểm tra cảnh 3D có dịch chuyển hay không. Bấm B lần nữa để bot tiếp tục chiến đấu. Bấm V để phóng to/thu nhỏ cửa sổ camera + skeleton ở góc phải. Bấm C để hiệu chuẩn lại khi đứng vị trí mới.

**Lưu ý:** 33 điểm chỉ là tổng số landmark mà model ước lượng; không phải lúc nào nó cũng thấy đủ 33 điểm. Để kiểm tra chân, đầu gối, gót và bàn chân, webcam cần nhìn được toàn thân. Khi chỉ nhìn thấy thân trên, hai vai vẫn đủ để dịch chuyển X/Z tương đối nhưng chất lượng độ sâu có thể kém hơn.

**Khi quay video lỗi:** Hãy gửi ảnh chụp cửa sổ chẩn đoán ở hai vị trí đứng khác nhau hoặc file `motion_log.csv`. Nếu tọa độ không đổi, đó là lỗi Pose/hiệu chuẩn; nếu tọa độ đổi nhưng cảnh 3D không dịch chuyển, đó là lỗi phần render/game. Có thể chọn `--camera 1` nếu Windows chọn nhầm webcam.

Đây vẫn là mô hình một camera, nên chiều sâu dựa vào **kích thước cơ thể tương đối**, không phải đo khoảng cách chính xác theo mét. Không nên báo cáo tọa độ này như đo đạc vật lý chính xác.


## Smoother camera + head dodge (latest)

- **Tilt head left/right:** the first-person horizon rolls with your head by up to 22 degrees. The camera also moves sideways relative to your shoulders for a real parallax dodge.
- **Dodge detection:** sufficiently pronounced head lean can avoid a bot attack. Tiny tracking noise is ignored by a continuous deadzone and frame-time-aware smoothing.
- **Smooth gameplay:** webcam capture and MediaPipe inference run on a background thread. Graphics render independently, targeting 60 FPS (actual FPS depends on computer/GPU); preview updates around 10 FPS.
- **Calibrate with C:** stand neutrally and look forward when you press C. The current head orientation becomes zero, so you can dodge relative to your own neutral position.
- **Keep shoulders visible:** left/right head orientation uses the eye/ear line and nose position relative to the shoulder midpoint. One webcam is approximate; head twist and occlusion may cause errors.

## What changed
- **PvE only**: one full-screen first-person 3D view instead of two PvP viewports.
- Refined 3D boxer with gloves, face, arms, legs; arena floor, lights and depth.
- Both fighters have actual virtual world **X and Z coordinates**. Bot world X/Z is drawn over its head (position projected from 3D) and player X/Z shown at bottom-left.
- Player moves left/right and forward/back via MediaPipe pose; bot approaches, retreats and sidesteps.
- Punches only damage inside the 2.35 virtual-distance reach radius.
- Camera preview shows pose skeleton for troubleshooting and tuning.

## Install on Windows
Requires Windows 10/11, Python 3.11 64-bit, webcam and OpenGL-capable driver.

1. Pull latest source from the GitHub **main** branch (or download ZIP).
2. Double-click **setup_3d.bat**. It installs existing dependencies and PyOpenGL.
3. Double-click **run_solo_3d_demo.bat** to test the graphics **without a camera**.
4. Double-click **run_solo_3d.bat** to play using camera and pose tracking.

## Controls
| Input | Action |
|---|---|
| Move physical body toward camera | Move forward (Z decreases) |
| Step away from camera | Move backward (Z increases) |
| Step left / right | Move X left / right |
| Tilt your head left / right | Camera tilts and shifts sideways; large lean can dodge a bot punch |
| Straighten arm rapidly | Punch |
| Both wrists near shoulder / face | Guard |
| C | Reset neutral standing and **head pose** calibration |
| W / S | Keyboard forward / backward |
| A / D | Keyboard strafe left / right |
| J / K | Keyboard left / right punch |
| [ / ] | Gesture sensitivity down / up |
| 1 / 2 / 3 | Easy / Normal / Hard bot |
| R | Restart |
| Escape | Quit |

## Calibrate coordinates
1. Stand so your **upper body** is clearly visible, both shoulders and hips.
2. Start the game standing in a **neutral starting position** at about 1.5–2.5 meters away from camera.
3. The first valid pose frame initializes the baseline. Press **C** to recalibrate from your current neutral position if desired.
4. After baseline is set, move about 15–30 cm forward and backward, watching the X/Z display. Since this is monocular image-scale estimation, actual meters are not calibrated.
5. Increase ambient light and avoid rotating your torso strongly when testing depth (turning changes apparent shoulder width).
6. If bot is out of range, move forward in the virtual arena or use W in demo mode.

## Details of movement mapping
- **X**: horizontal shoulder/hip center displacement from calibration.
- **Z**: approximate distance inferred from combined apparent shoulder width + torso height relative to calibration. Closer to camera -> larger apparent body -> lower virtual Z.
- MediaPipe outputs normalized landmarks, not physically accurate depth. Position is smoothed with EMA and a dead-zone against jitter.
- Virtual distances and coordinates are for gameplay only; values shown are **not measured real-world meters**.

## Notes on first-person view
This is a desktop virtual first-person camera, not an AR/VR headset. One webcam cannot track real 6-DoF head positions or physical punches accurately without additional sensor/depth calibration. The prototype uses heuristic recognition and 3D primitives rather than photorealistic animated character models.

## Architecture
```
Webcam -> OpenCV -> MediaPipe Pose -> SoloPose
           -> (X/Z movement, punch, guard)
           -> Fight (bot pursuit, range-based damage)
           -> SoloScene OpenGL renderer (world, 3D boxer, floating XYZ HUD)
```

## Troubleshooting
- Webcam unavailable: close Teams/Zoom, use `.venv\Scripts\python.exe -m solo3d.main --camera 1`.
- Pose skeleton jitter: brighter lighting, arms clearly visible, recalibrate C. Camera roll is interpolated and tiny tilt noise is ignored.
- Camera not working: start `run_solo_3d_demo.bat`.
- Frame rate poor: close resource-heavy apps, update GPU drivers.
- Setup not completed: rerun `setup_3d.bat`.
- Coordinates unexpectedly jump: recalibrate and face the webcam instead of rotating sideways.

## Research/coursework notes
This is a useful prototype for image processing because it makes it easy to document landmark extraction, temporal smoothing, angle and velocity estimation, perspective-size movement inference, and visually comparing observed pose with intended movement. It is *not* a validated movement tracking system. Test and log recognition false positives before reporting accuracy.
