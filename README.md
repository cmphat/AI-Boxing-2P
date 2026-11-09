# AI-Boxing-2P — Y8 Pose Controller (Fast V3)

## What this version fixes

- Opens the official Punch Boxing Championship page automatically in a dedicated Edge/Chrome kiosk window.
- Resolves the browser window using its process ID first, with a Y8 page-title fallback. It no longer depends on one exact window title.
- Gives the game the full desktop viewport. The old split-screen layout could make Y8 display "Your screen is too small to play this game".
- Floats the camera controller above the game. Press F6 to hide/show the camera panel while keeping the controller active.
- Uses MediaPipe Pose Landmarker LITE, one tracked person, 480x270 camera input and 15 FPS inference target.
- Reads webcam frames on a separate worker thread, so the Tk UI is not blocked by camera reads.
- Filters only the nine landmarks used by boxing, with low-latency One Euro settings.
- Starts Y8 before webcam/model initialization, so a webcam error cannot block the game from opening.
- Caps camera preview rendering at 20 FPS and avoids copying the webcam frame on every UI tick.
- Displays actual pose-inference latency in milliseconds.

## Requirements

- Windows 10/11 64-bit
- Python 3.11 64-bit
- Webcam
- Microsoft Edge or Google Chrome recommended

## First run

1. Extract the ZIP.
2. Double-click run.bat.
3. On first run, it automatically creates .venv, installs dependencies and downloads the LITE pose model.
4. It then opens the Y8 game and the camera controller.

You can also run setup.bat once manually, then use run.bat for later launches.

## Play

1. Wait for the Y8 page to load.
2. Choose Quick Mode in the game. A first click is still required inside the game page because the browser requires a user gesture to activate the WebGL game.
3. Click the game area once to give it keyboard focus.
4. Press F8 or click the enable-control button.
5. Perform punches in front of the camera.

The game opens maximized so Y8 receives a full-width desktop viewport. The camera panel floats above the game. Press F6 to hide/show the panel if it covers part of the game.

## Hotkeys

- F6: hide/show camera panel
- F7: test Q key (game must be focused)
- F8: enable/disable motion control
- F9: recalibrate neutral pose
- F10: exit

The blue MO LAI Y8 GAME button retries the game launch if the browser was closed.

## Performance

- Pose model: LITE
- Pose count: 1
- Camera input: 480x270
- Inference target: 24 FPS
- Camera capture: independent worker thread
- Pose latency is shown in the camera panel

## Troubleshooting

- If Y8 does not open, press MO LAI Y8 GAME. If it still fails, check Edge/Chrome installation and network access to Y8.
- If Y8 says the screen is too small, keep the game maximized and hide the camera panel with F6.
- If F7 does not punch, click the game area and test again.
- If the camera is black, close other apps using the webcam or change CAMERA_INDEX in main.py.


## V3.1 performance/startup notes

The launcher uses a dedicated Edge/Chrome profile in kiosk mode and waits for the Punch Boxing Championship page title before reporting success. The Y8 browser starts independently from camera initialization. If the webcam is unavailable, the game still opens and the controller displays the camera error instead of exiting.
