# Real SO-101 replay

Goal: take a recording the network accepted and replay it on your physical SO-101 follower arm.

## One-time calibration of the sim to real mapping

The simulator's joint zero is not the real arm's calibrated zero, so each joint needs a sign and an
offset in `realarm/mapping.json`. The gripper maps linearly: simulator closed (0.05 rad) to 0 and
open (1.3 rad) to 100.

1. Calibrate the follower with LeRobot as usual (`lerobot-calibrate`, id `taunet_follower`).
2. Put the real arm in the simulator's start pose: shoulder_pan 0, shoulder_lift -1.2 rad (-68.8 deg),
   elbow_flex 1.2 rad (68.8 deg), wrist_flex 0.8 rad (45.8 deg), wrist_roll 0. Read the real joint
   values (`robot.get_observation()`).
3. For each joint, offset_deg = real_reading - sign * sim_degrees. Pick the sign by moving one joint
   a little and checking that the real and simulated directions agree (flip the sign if not).
4. Write the five signs and offsets to `realarm/mapping.json`.

Check with `DRY_RUN=1 python -m realarm.replay_episode BUNDLE.json /dev/null` that the mapped ranges
stay inside the real arm's calibrated ranges.

## Replay

```
SPEED=0.5 uv run --python 3.12 --extra realarm python -m realarm.replay_episode data/accepted/<bundle>.json /dev/tty.usbmodemXXXX
```

The arm glides to the first pose over three seconds, then plays the recorded actions at half speed.
Every command is limited to `MAX_STEP_DEG` (default 8) from the current pose. Keep the workspace
clear and a hand on the power switch for the first runs. Place a cube and bowl roughly where the
scene shows (the table plane is the simulator floor) if you want the real arm to do the task.
