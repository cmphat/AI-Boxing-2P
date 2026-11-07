# AI Boxing 3D – first-person OpenGL extension

This is **real depth-tested OpenGL 3D geometry**, not a 2D image styled to look 3D. It is a prototype made from procedural primitives, not photorealistic character models.

## Windows installation
1. Install Python 3.11 (64-bit) and an OpenGL-capable graphics driver.
2. Run `setup_3d.bat`. It installs the existing OpenCV/MediaPipe/Pygame dependencies plus PyOpenGL and fetches MediaPipe's Pose Landmarker Lite model.
3. Run `run_3d.bat` for the webcam PvP split-screen.
4. To test without a webcam or model, run `run_3d_demo.bat` (requires Python dependencies only).

## Commands
```powershell
.venv\Scripts\python.exe -m fps3d.main --mode pvp
.venv\Scripts\python.exe -m fps3d.main --mode pve
.venv\Scripts\python.exe -m fps3d.main --demo
.venv\Scripts\python.exe -m fps3d.main --mode pvp --camera 1 --sensitivity 1.4
```

- `1`: Player vs Bot full-screen
- `2`: Two-player split-screen first-person view
- `A/S`: simulated P1 left/right punch
- `K/L`: simulated P2 left/right punch
- `[` / `]`: lower / raise pose sensitivity
- `R`: restart
- `Esc`: exit

## Camera and player placement
- Use a single wide-angle webcam in front of the two players, at chest height.
- PvP: P1 stands on the **left** side of the mirrored camera, P2 on the **right**.
- Keep a clear space around each player. **Never hit the other player**.
- Do not cross from one half of the frame to the other. With one camera, crossing causes identity switches.
- Keep the face, shoulders, elbows, hands and upper body visible.

## How it works

Webcam → OpenCV (flip / BGR to RGB) → MediaPipe (up to 2 poses; 33 landmarks each) → smoothing + arm angles + wrist velocity + weak depth cue → attack/guard inputs → OpenGL render.

**Limitations**: Pose z is an estimated camera-relative depth, not a true 3D physical punch measurement. Landmark smoothing and normalized speed are adjustable heuristics, not validated punch-classification accuracy. Gameplay health reduction is triggered by gesture events, not real-world glove/face contact. The 3D view is a virtual first-person camera; it is NOT VR/AR and is not the user's actual eye camera.

### Why the 3D prototype is split-screen

A single desktop monitor cannot display two independent full-screen first-person camera views simultaneously. The PvP mode draws each camera in one half of the screen using OpenGL `glViewport` and `glScissor`. PvE uses one full-width viewport.

### Diagnostics
- Small webcam overlay shows the detected pose skeleton.
- Each viewport shows TRACKED / NO POSE.
- In case of poor responsiveness, increase sensitivity with `]` and use brighter light.
- For smoother frame rate, lower webcam capture resolution in `fps3d/main.py`.
- You can run the keyboard-only demo to isolate graphics issues from webcam issues.

## Sources
- Google MediaPipe Pose Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- Pygame display: https://www.pygame.org/docs/ref/display.html
- PyOpenGL: https://pyopengl.sourceforge.net/

## Status

Prototype. Python syntax and basic game-state logic should be tested locally; webcam latency, Windows graphics drivers and pose tracking accuracy require testing on the target machine.
