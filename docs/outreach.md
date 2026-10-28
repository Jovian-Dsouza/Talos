# Cold outreach (draft)

Goal this week: one reply, quote or pilot request from a VLA or robot foundation model team. The
price of browser-sim trajectories is the biggest unknown in the plan, so ask for it directly.

## Who to approach

Pick people by role, not by guessing addresses. Look for data leads, research engineers who post
about data mixes, and founders. Starting organizations: Physical Intelligence, Skild AI, Hugging
Face LeRobot team, Generalist AI, Dyna Robotics, Genesis AI, Toyota Research Institute, NVIDIA GEAR,
Google DeepMind robotics, Figure, 1X, plus Bittensor teams that need training data (OpenRoboto SN80,
Kinitro, Nepher).

## Message (short version)

Subject: language-conditioned SO-101 teleop data, free sample

Hi NAME, I run a small project that collects human teleoperation demos on a simulated SO-101 from
phones and browsers, then has independent validators replay each one in native MuJoCo so the success
labels and timing are not taken on trust. Every episode has a language instruction, randomized scene
(seeded, so it cannot be pre-recorded), a verified success label, and the same action space as the
LeRobot SO-101 datasets.

There is an open LeRobotDataset sample here: LINK. If it is close to useful, I would like to ask two
things: what tasks or failure cases you would want more of, and what you would pay per usable hour
for verified sim demonstrations like these. We can collect a custom task to a quota.

Thanks, NAME

## Follow-up questions for a call

What data did you buy last quarter, and what was wrong with it? Which sim to real gap hurts most?
Would you pay for correction data on your own policy's failures? What do you pay per usable hour
today for real teleop and for sim data?
