# Live demo script (about 3 minutes)

Before: web app and miners behind HTTPS, validator running, testnet subnet with at least a day of
history, a second device showing the validator log and the explorer page, open sample on Hugging
Face, fallback recordings on disk.

1. Judge scans the QR code. The page opens, they pick Vial racking (lab automation), type a
   nickname and tap Start. Turning the phone sideways gives the biggest view.
2. They get a seeded task, for example "Rack the purple-cap vial in slot B2", with distractor vials
   and a rack that is partly filled. This is the job lab automation buyers pay for. Say that the
   same data format covers kitting, machine tending and sample prep.
3. Left stick moves the gripper, right stick raises, lowers and rolls the wrist, Grip toggles.
4. They tap Submit. Within seconds the verdict shows: replay matches, task completed, quality,
   novelty, score. Rejections show a clear reason.
5. The leaderboard updates, with the open pool against the second pool. Open the explorer link to
   show the validator's weights extrinsic. Point at the epoch Merkle root commitment.
6. Real arm moment: pick the judge's accepted bundle and run
   `SPEED=0.5 python -m realarm.replay_episode <bundle> <port>`. "Your demo, verified by the network,
   running on a real robot."
7. Close: the accepted data is already a LeRobotDataset. Show the open sample on Hugging Face.

Talking points: trustless replay (a forged recording or a copied one fails), seeds bind each ticket
to a pool and a block so nothing can be pre-recorded, phone controls, same action space as real
SO-101 datasets, buyer demand multiplier steering emissions.

Fallbacks: localnet screen for fast block emissions; recorded video of the real arm; scripted
simulated phones (scripts/dev/sim_phone.py) to fill the leaderboard if the room is quiet.
