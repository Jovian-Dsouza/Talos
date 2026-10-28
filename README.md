# bittesnor

A Bittensor subnet for verified simulated robot teleoperation data. People drive a simulated SO-101
arm on a phone or laptop (MuJoCo in the browser). Validators replay every recording in native
MuJoCo, check that it really succeeded, score quality and novelty, and set weights. Accepted
episodes export as LeRobot datasets for VLA labs.

Plan and decisions: [teleop-subnet-plan.md](teleop-subnet-plan.md). Findings from the determinism
spike: [docs/m0-findings.md](docs/m0-findings.md). How to run everything: [docs/runbook.md](docs/runbook.md).

```
common/      shared Python: seed, scene generator, MJCF builder, success checker, bundle, ticket, chain adapter
assets/      SO-101 model (MuJoCo Menagerie, Apache-2.0)
miner/       open-pool miner service (FastAPI): tickets, uploads, signed serving to validators
validator/   replay, scoring, dedup, weights, epoch Merkle roots
web/         browser teleop app (Vite, three.js, MuJoCo WASM 3.17.0)
export/      LeRobotDataset export with server-side rendered frames
realarm/     replay an accepted episode on a physical SO-101
scripts/     localnet and testnet setup, dev tools, demo helpers
deploy/      Dockerfile and compose file for a VM
docs/        runbook, real-arm calibration, demo script, outreach, pitch
```
