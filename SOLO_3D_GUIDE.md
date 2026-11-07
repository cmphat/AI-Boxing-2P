# AI BOXING SOLO 3D – First Person + Coordinates + Moving Bot

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
