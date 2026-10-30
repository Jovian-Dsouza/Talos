# Robotics Training Data: Startup Research Notes

*Compiled October 26, 2026*

---

## 1. How to find and validate a customer problem

### Finding real problems
- **Start from your own pain or industry.** The best problems are ones you've lived or seen up close.
- **Ask about the past, not the future.** "Tell me about the last time you dealt with X. What did you try? What did it cost you?" Avoid "Would you use an app that…?" (see *The Mom Test* by Rob Fitzpatrick).
- **Look for workarounds.** Spreadsheets, WhatsApp groups, freelancers, duct-taped tools. If people already spend money or time patching a problem, that's the strongest signal.
- **Scan complaints.** Reddit, 1–3 star app reviews, G2/Capterra reviews of competitors, niche forums.

### Validating the idea
- Interview **15–30 target customers** and look for the same pain repeating unprompted.
- **Urgency test:** Is it frequent, painful, and already being paid for?
- **Ask for commitment, not compliments:** pre-orders, deposits, LOIs, pilots.
- **Fake it before building:** landing page with a buy/waitlist button, a manual "concierge" version, or a no-code prototype. Measure conversion, not likes.
- **Set a kill criterion upfront** (e.g., "fewer than 10 of 100 visitors sign up → pivot").

### Estimating revenue
- **Bottom-up sizing:** reachable customers × realistic price × expected conversion.
  - Example: 50,000 clinics × ₹2,000/month × 2% adoption ≈ ₹2 crore/year.
- **Price on value:** charge a fraction of what the problem costs the customer.
- **Unit economics:** aim for LTV ≥ 3× CAC, with CAC payback under 12 months.

### Judging scalability
- **Distribution:** Is there a repeatable, cheap channel?
- **Marginal cost:** Does customer #1,000 cost far less to serve than customer #10?
- **Retention:** Flat retention curves mean you have something real.
- **Expansion:** Adjacent segments, geographies, upsells.

**Suggested sequence:** 2–4 weeks of interviews → 2–4 weeks of fake-door or concierge tests → 5–10 paying customers → then build seriously.

---

## 2. The biggest problem in robotics right now: data

- Robotics and physical-AI companies raised **~$48B in 2026** so far (PitchBook via FT). A growing share goes to collecting real-world data.
- Hardware and funding are no longer the bottleneck. **Training data is.**
- NVIDIA (GTC 2026): language models had trillions of internet tokens; robotics has **a few hundred thousand hours** of teleoperation data at best, mostly task-specific.
- Unlike text, robot data can't be scraped. It must be created by humans.

### What companies already pay for (crowdsourceable)
| Data type | Example | Notes |
|---|---|---|
| **First-person (egocentric) video** | Micro1: ~4,000 contributors, 71 countries, 160k+ hrs/month. DoorDash launched a Tasks app for this. | Crowded; pay often low. |
| **Wearable / glove data** | Generalist AI shipped thousands of grippers worldwide, targeting 500k hours. | Requires hardware distribution. |
| **Teleoperation of real robots** | 1X, Figure — teleoperator roles at ~$22–35/hr. | Mostly employees in labs or company setups. |
| **Browser / phone sim teleop** | Axis Robotics — 100k+ contributors claimed. | Closest to "masses, decentralized." |

### The catch
- Egocentric video is **commoditizing fast**, and India is a major supply hub (e.g., Human Archive pays gig workers ~$1/hr baseline).
- Pure data provision can be a **thin-margin** business.

### Where the real gaps are
1. **Quality, not volume.** Volume-first gig data often fails to transfer across robot bodies. A decentralized *verification/review* network is less crowded than collection.
2. **Evals and benchmarks.** YC-backed founders say robotics evals "barely exist." Crowd-sourced real-world test scenarios could be valuable.
3. **Niche domains.** Skilled trades (welding, tailoring, electrical), commercial kitchens, agriculture, Indian / non-Western homes. Labs buy *diversity*.
4. **Richer sensor data.** Video + hand pose + force/touch from cheap wearables.
5. **Consent & compliance.** India's IT ministry is examining egocentric-data consent practices. A clean, DPDP-compliant network is a selling point.

---

## 3. Company deep dives

### 1X Technologies (NEO humanoid)
- **Customers / revenue:** Not public. Pre-orders opened Oct 30, 2025 at **$20,000** or **$499/month**; ~**10,000 pre-orders** reported. No independently verified customer delivery as of mid-July 2026.
- **Other revenue:** EVE (wheeled industrial robot) is deployed commercially.
- **How data is collected:** The robot in the customer's home is the collector. When NEO can't do a task, a remote 1X operator ("Expert Mode") takes over via **VR headset**, seeing through the robot's cameras. Every session becomes training data.
- **Who operates:** Employees, not gig workers (~$22–31/hr postings).
- **Privacy controls:** Owner-approved session windows, face blurring, no-go zones, indicator light during sessions.
- **Replicable at home?** No — needs a full humanoid + VR rig.

### Prosper Robotics (Alfie)
- London startup founded 2021 by Shariq Hashme (ex-OpenAI, Scale AI).
- **Status:** As of mid-2026, Alfie **not commercially released** → no customers or revenue.
- **Planned model:** 5'10" robot, two arms, grippers, four wheels, depth camera, teleoperated from low-wage countries via VR.
- Founder estimate: ~**10,000 attempts** per task before the robot can learn it.

### Axis Robotics (browser-based sim teleop)
- **Founded:** 2025, Berkeley/SF. ~11 employees. CEO Chris Feng, co-founder Christine Cao.
- **Funding:** **$12M seed** (July 2026) led by Hack VC, with Nomad Capital, Pi Network Ventures, 10K Ventures.
- **Revenue:** PitchBook lists "generating revenue"; amount not public.
- **Customers:** Teams building robot foundation models; also pitches to hardware makers and automakers.
- **Scale claims:** 100,000+ contributors; 200,000+ verified trajectories.
- **How it works:**
  - Contributors control **simulated** robot arms in a browser — no hardware.
  - Controls: keyboard (precise steps), virtual joystick or gamepad (continuous motion), click-and-drag gripper, double-click auto-navigate, save/rewind checkpoints.
  - Quality: success checks, filtering, training runs, real-robot evaluation.
  - Incentives: points/rewards with an **on-chain record** of contributions (crypto-style "train-to-earn").
- **Proof points:**
  - **"The Little Prince's Rose" (Jan 2026):** Contributors guided a sim arm to pick up a watering can and water a plant. **10,000+ valid trajectories in 3 days.** A policy trained on this ran on a **real robot** in an unseen environment.
  - **February 2026 beta:** **18,000 users**, **~100,000 trajectories**, **27 task types**, **5 days.**

#### Where to see Axis in action
- Live platform: https://hub.axisrobotics.ai/?tab=hub
- Teleop UX demo clips: https://axisrobotics.ai/product/teleop-ux-updates-click-drag-auto-navigate-save-rewind
- Funding article with embedded X video: https://runtimewire.com/article/axis-robotics-raises-12-million-robot-training-data
- Official X account: https://x.com/axisrobotics (contributor task videos — search "@axisrobotics task video")
- GitHub: https://github.com/AxisAIOrg
- Tech report: https://techreport.axisrobotics.ai/

*No official YouTube channel found.*

---

## 4. Axis's tech stack

| Layer | Technology |
|---|---|
| Physics in the browser | **MuJoCo compiled to WebAssembly** — runs on CPU, no GPU or install needed |
| Task generation | LLMs + MuJoCo create randomized manipulation scenes (12 categories) |
| Data cleaning | Quality filtering, hesitation removal, Savitzky-Golay smoothing, cubic spline resampling |
| Realism (server side) | Demos replayed on Linux GPU servers with an **Isaac Sim-based** augmentation backend (lighting, textures, domain randomization) |
| Abstraction | "MetaSim" layer to support multiple simulators |
| Training | Vision-language-action (VLA) models → sim-to-real testing |

**Key insight:** The phone/browser only runs cheap physics and records actions. Expensive photorealistic rendering happens later on servers by replaying those actions.

---

## 5. Recommended stack if building this

### Core choices
- **Physics:** MuJoCo WASM via official bindings — `npm install @mujoco/mujoco` (still marked WIP; test on low-end Android early).
  - Why MuJoCo over game engines (Rapier, Cannon, PhysX): robotics-grade contacts and actuators, ready-made models of real robot arms, and demos replay identically in labs' Python pipelines.
- **Rendering:** Three.js (proven pairing with MuJoCo WASM). Babylon.js is an alternative.
- **Phone controls (potential edge over Axis):**
  - Touch drag for gripper + open/close buttons.
  - Use phone motion sensors (WebXR / DeviceOrientation API) as a 6-axis controller. The COBALT study found phone teleop matched or beat specialized hardware.
- **Data format:** **LeRobotDataset** (Hugging Face). Log state, actions, timestamps at ~20–30 Hz.

### Backend
- App: Next.js / React; Supabase or Postgres for users, tasks, payouts.
- Storage: S3 or Cloudflare R2 for trajectories.
- Replay & augmentation: Python with native MuJoCo; Isaac Sim or MuJoCo rendering for visual variety.
- Quality filters: automatic checks for task success, smoothness, duration outliers before payout.

### Architecture options
| | Option 1: Physics on phone | Option 2: Physics on server, stream video |
|---|---|---|
| Used by | Axis | COBALT (research) |
| Server cost | Near zero | GPU per ~8 concurrent users |
| Scene complexity | Simpler | Richer |
| Device consistency | Varies by phone | Identical |
| Internet needs | Low | Good, low-latency |

**Pick:** Start with **Option 1** (MuJoCo WASM + Three.js + phone motion controls + LeRobot format). A single-arm pick-and-place demo is achievable in 1–2 weeks. Move to Option 2 only when a paying customer needs heavier scenes.

**Fastest starting point:** Open the mujoco_wasm demo on your phone to check performance: https://github.com/zalo/mujoco_wasm

---

## 6. Building real (not simulated) teleop data at home

- **SO-101 arm** (open source, ~₹20–30k for leader + follower pair): you move the leader arm by hand; the follower copies it.
- **LeRobot (Hugging Face):** teleoperate → record → train → deploy. One command records ~50 episodes and uploads to the Hugging Face Hub. **LeLab** offers a browser GUI.
- Guides:
  - SO-101 setup: https://huggingface.co/docs/lerobot/so101
  - Imitation learning tutorial: https://huggingface.co/docs/lerobot/getting_started_real_world_robot
  - Parts & assembly: https://github.com/TheRobotStudio/SO-ARM100
- YouTube search terms: "SO-101 LeRobot assembly", "LeRobot record dataset SO-101".

---

## 7. Possible wedge & next steps

**Wedge idea:** A network of cheap SO-101-style rigs in Indian homes and workshops collecting **real** manipulation data on tasks labs actually need — sitting between Axis (cheap but simulated) and lab teleop (real but expensive). Alternatively, a phone-first sim platform with motion-sensor controls, or a decentralized quality-verification layer.

**Next steps**
1. Try Axis as a contributor to feel the experience and its friction.
2. Open the mujoco_wasm demo on your phone to gauge performance.
3. Build or buy one SO-101 and record 50 demos to learn real data-quality problems.
4. Interview 15–20 data leads at robotics labs (e.g., Physical Intelligence, Skild, Figure, CynLr, Addverb):
   - What data did you buy last quarter?
   - What was wrong with it?
   - What would you pay per hour for better data?
5. Sell a small **50–100 hour pilot dataset** before building a full platform.

---

## Sources

**Market & data bottleneck**
- FT/PitchBook via AI Weekly: https://aiweekly.co/alerts/ft-robotics-and-physical-ai-labs-raise-48b-ytd-on-data-hunt
- KoreaTechDesk (NVIDIA GTC 2026): https://www.koreatechdesk.com/physical-ai-commercialization-robot-deployment
- Generalist AI (The Daily Upside): https://www.thedailyupside.com/technology/artificial-intelligence/2-billion-start-up-generalist-ai-wants-to-solve-the-robot-data-bottleneck/
- XDOF (Dealroom): https://dealroom.co/news/135015-xdof-raises-70m-to-build-the-data-pipelines-for-training-robots
- Egocentric data platforms: https://remowork.life/blog/get-paid-to-record-household-chores-egocentric-ai-data-platforms-2026
- Human Archive: https://mezha.net/eng/news/aac0e4fd_human_archive_raises/
- Indian factory workers (Metaintro): https://www.metaintro.com/blog/india-workers-robot-training-data-2026
- YC robotics infrastructure (A3): https://www.automate.org/ai/industry-insights/yc-startups-look-to-build-infrastructure-for-the-robotics-industry/aph
- Gig worker data quality (Claru): https://claru.ai/blog/gig-workers-training-humanoid-robots-data-quality
- Teleop economics: https://liveinthefuture.org/stories/robot-data-factory-economics.html

**1X Technologies**
- https://ai2.work/blog/1x-neo-ships-into-homes-with-a-human-teleoperator-still-inside
- https://www.jaredwatkins.com/research/robotics/humanoid/us-companies/1x-technologies/
- https://runtimewire.com/article/1x-neo-preorders-home-robot-data-flywheel
- https://komo.ai/directory/1x-technologies

**Prosper Robotics**
- https://aiwiki.ai/wiki/prosper_robotics
- https://prosper-landing.onrender.com
- https://www.technologyreview.com/2024/12/23/1108466/general-purpose-robots-humanoids-ai-remote-assistants/

**Axis Robotics**
- Docs: https://docs.axisrobotics.ai/
- Tech report: https://techreport.axisrobotics.ai/
- Little Prince's Rose: https://axisrobotics.ai/resources/blog/little-princes-rose-sim-to-real
- Browser simulation: https://axisrobotics.ai/resources/learn/browser-based-simulation-robotics
- Seed round (RuntimeWire): https://runtimewire.com/article/axis-robotics-raises-12-million-robot-training-data
- Seed round (Seedtable): https://seedtable.com/companies/axis-robotics/funding-rounds/axis-robotics-seed-2026-07
- PitchBook: https://pitchbook.com/profiles/company/1442234-80

**Tech stack**
- MuJoCo: https://github.com/google-deepmind/mujoco
- MuJoCo JS bindings: https://cdn.jsdelivr.net/npm/@mujoco/mujoco@3.9.0/README.md
- mujoco_wasm: https://github.com/zalo/mujoco_wasm
- COBALT paper: https://www.emergentmind.com/papers/2605.19138
- LeRobot: https://huggingface.co/docs/lerobot/en