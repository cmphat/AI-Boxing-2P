# Shadow Robot Mode – Full-Body Pose Mimicry

This is an original articulated robot design inspired by the general *shadow mimicry* idea from robot-boxing fiction. **It is not a licensed Atom/Real Steel model.** The game prototype is rendered with procedural OpenGL parts, so it will not look photorealistic.

## Changes in this prototype
- The game starts in **FIRST PERSON BOXING**. Both arms are rendered from shoulder, elbow and wrist tracking.
- **Tab** toggles the optional **SHADOW ROBOT debug view** (third person) so you can inspect full-body pose retargeting. Press Tab again to return to the actual boxing view.
- The robot's **right wrist always uses anatomical landmark 16**, and left wrist uses landmark 15.
- Skeleton retargeting uses the shoulder-to-hip body scale; the robot pose is interpolated every rendered frame for smoother movement.
- Occluded joints fall back to a neutral pose. The 33-landmark diagnostic still helps distinguish image detection problems from 3D rendering problems.

## Windows startup
1. Pull latest GitHub main or download a fresh ZIP.
2. Run `setup_3d.bat` once if libraries are not installed.
3. Run `run_tracking_diagnostics.bat` to verify all body joints in the webcam.
4. Run `run_solo_3d.bat` for the 3D game; first-person is the default.
5. Press **Tab** only to inspect the optional full-body robot debug view. **C** recalibrates body position. **B** freezes the opponent so you can test movements clearly. **V** changes camera diagnostic size.

## Recommended 1-minute verification
1. Show your **whole body** to the webcam, including feet and knees. Stand facing it with decent lighting.
2. Raise your anatomical right arm: the robot's right upper/lower arm should move.
3. Bend the left elbow while the right arm stays still.
4. Squat or bend one knee to confirm that the robot's knees respond.
5. Move left/right and forward/back, checking game X/Z movement.
6. Switch to first-person mode and verify the gloves and head dodge.

## Technical limits
- A single RGB webcam provides projected pose **estimates**, not tracked biomechanical joint angles or absolute depth. Crossing arms, fast punches, occluded knees, and head turns can produce inaccurate joints.
- 33 landmarks are *not* 33 independent bones: joints are connected by a custom rig, and finger pose needs a separate hand-landmark model.
- This version does not use a rigged Blender/Unity `.glb` character or complex inverse-kinematics. For cinematic realism, the next stage is to import a legally licensed **rigged robot asset** with PBR materials and skinning, perform per-bone orientation retargeting, and validate camera-to-avatar latency. A 3D engine such as Godot, Unity, or Panda3D is more suitable for that level of graphics.
- Keep clear space when playing. Do not actually strike another person.
