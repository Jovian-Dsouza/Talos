# Bittensor × Robotics: Research & Hackathon Ideas


## 1. What is Bittensor?

Bittensor is a decentralized network that turns machine intelligence into an open market. Its native token is **TAO** (supply capped at 21 million). Bittensor was founded in 2019 by Jacob Steeves and Ala Shaabana.

### Core concepts

| Concept | What it means |
|---|---|
| **Subnet** | An independent incentive market built around one AI task (inference, training, robotics, data, etc.). Each subnet is effectively a startup with its own token. |
| **Subnet owner** | Defines the task and the scoring code, and receives a share of the subnet's emissions. |
| **Miners** | Produce the subnet's commodity: models, outputs, compute, data. |
| **Validators** | Score miners' work. Scores are aggregated through **Yuma Consensus**. |
| **Alpha token** | Each subnet's own token. Staking TAO into a subnet swaps it into that subnet's alpha. |
| **dTAO (Dynamic TAO)** | Emissions are allocated by market price of each subnet's alpha token, replacing the old root-validator vote. |

### How a subnet earns

1. **Emissions:** TAO and alpha emissions flow to subnets in proportion to market demand for their alpha token, then to miners, validators and the owner.
2. **External revenue:** Paying customers for the subnet's output (e.g. inference APIs). Many top subnets use this revenue to buy back their alpha token.

### State of the network (2026)

- About **128 active subnets**, with expansion to 256 planned.
- Bittensor is the largest AI-focused token by market cap, with roughly **$17M+ annualized revenue** (Artemis); several subnets track $1M+.
- **Revenue is concentrated.** The top 10 subnets take about 56% of emissions. Targon (SN4) is the highest-revenue subnet; Chutes (SN64) is a top inference provider on OpenRouter.
- **Key weakness:** most of the remaining subnets have no reported external revenue, are pre-product, or depend mainly on emissions. Emission halvings increase pressure to earn real revenue.
- In April 2026, Covenant, an AI lab running several top subnets, left the network, exposing ecosystem fragility.

---

## 2. Robotics on Bittensor

| Subnet | Focus | How it works |
|---|---|---|
| **OpenRoboto (SN80)** | Robot manipulation models | Miners fine-tune the current base model (π0.5 via openpi) and submit weights on-chain. A challenger replaces the base only if it beats it on a shared benchmark (six LIBERO suites in MuJoCo). Launched August 6, 2026. |
| **Swarm (SN124)** | Autonomous drone flight | Miners submit drone pilot models that navigate procedurally generated 3D worlds using a depth camera plus position/speed. Public leaderboard; `swarm champion` downloads the current best model. Open-source reference drone **Langostino** (ROS2, Raspberry Pi, INAV, 3D-printed). |
| **Nepher Robotics (SN48/49, sources disagree)** | Sim-to-real policy tournaments | Tournament platform plus EnvHub environment service; miners package and submit policies. |
| **Kinitro** | Robot policy evaluation | Miners submit agents for robotic tasks; validators run containerized evaluations across robotic environments. Models stored on Hugging Face. |
| **Reboot (SN47)** | Robotics AI services | Small subnet (~0.17% emission) for building and validating robotic systems. |
| **StreetVision by NATIX (SN72)** | Physical-world perception data | Analyzes crowdsourced street-level imagery for mapping and autonomous driving; moving toward classifying driving video into traffic scenarios and rare edge cases. NATIX sells datasets, edge-case extractions and OpenSCENARIO scenarios to AV and logistics companies. |
| **Chutes (SN64) / Targon (SN4)** | Inference | Cheap, scalable inference that a robot can use as a cloud "brain" for vision-language reasoning. |

### The gap

Robotics subnets are good at **producing** models (manipulation policies, drone autopilots, evaluated agents). Almost none have **paying customers**. The winning opportunity is the last mile: connect subnet output to someone who pays, and feed real customer demand back into the subnet.

---

## 3. Hackathon Ideas (ranked)

Judging criteria: working prototype · clear problem and solution · strong five-day execution · meaningful use of Bittensor · credible path forward.



### Idea 5 — Teleoperation demonstration marketplace

- **Problem:** Robot foundation models are bottlenecked on demonstration data.
- **Solution:** Pay remote teleoperators for demos; validators replay them in simulation and score for success and diversity.
- **Revenue:** Sell datasets or route them to SN80 miners.
- **Five-day demo:** Harder to show live; incentive mechanism can be prototyped.

## 6. Sources

- [Bittensor — AI Wiki](https://aiwiki.ai/wiki/bittensor)
- [State of Bittensor — FalconX](https://falconx.io/newsroom/state-of-bittensor-subnet-adoption-trends-network-mechanics-and-covenants-departure)
- [The Bear Case for Bittensor — Pine Analytics](https://pineanalytics.substack.com/p/the-bear-case-for-bittensor-tao)
- [How to Build on Bittensor in 2026 — Avark](https://avark.agency/learn/how-to-build-on-bittensor-in-2026-the-complete-guide-to-launching-on-the-decentralized-ai-network)
- [OpenRoboto launch coverage — EdgeX](https://pro.edgex.exchange/en-US/news/article/bittensor-tao-bullish-reversal-openroboto-subnet-80)
- [Swarm README](https://raw.githubusercontent.com/swarm-subnet/swarm/main/README.md)
- [NATIX StreetVision launch — The Defiant](https://thedefiant.io/news/press-releases/natix-launches-decentralized-ai-subnet-on-bittensor-to-advance-autonomous-driving-and-physical-ai)
- [NATIX Network — Solana Compass](https://solanacompass.com/projects/natix_network)
- [Reboot subnet — Learn Bittensor](https://learnbittensor.org/subnets/47)