# M0 findings (October 26, 2026)

## Determinism: WASM vs native MuJoCo

`@mujoco/mujoco` 3.17.0 exists on npm, so the browser build can match native `mujoco` 3.17.0 exactly.

Spike (`scripts/m0`): SO-101 arm with a cube, 140 control steps of 20 ms over 2 ms physics, a scripted trajectory that touches and pushes the cube. The same controls were run in WASM (Node) and in native MuJoCo.

| Quantity | Max difference |
|---|---|
| Arm joint positions | 8.0e-05 rad |
| Cube position | 1.1e-04 m (0.1 mm) |

Decision: **strict replay is viable** for this contact level. Start with epsilon of 0.01 rad for the arm and 5 mm for objects. Windowed replay stays in the validator as a fallback switch. Not yet measured: a phone browser, and grasp-and-lift contact, which amplifies error more than a push.

## Bittensor SDK 11.3.0 facts

- Chain client: `bt.Subtensor(endpoint)`. Reads: `st.read("name", **params)` (for example `balance`, `subnets`, `neurons`, `uid`, `metagraph`). Blocks: `st.block`, `st.block_info(block)` returns the hash.
- Writes are intents run with `st.execute(intent, wallet)`: `SetWeights(netuid, uids, weights)`, `ServeAxon(netuid, ip, port)` (publishes an endpoint, starts no server), `RegisterSubnet`, `BurnedRegister`, `AddStake`, `Transfer`.
- HTTP auth: `bt.http_auth.sign(wallet, method, path, body, receiver_ss58)` returns headers, and `bt.http_auth.verify(headers, body, method, path, self_hotkey_ss58, nonce_store)` returns the caller or raises. It binds the receiver, checks freshness and rejects replayed nonces.
- `bt.Policy(max_spend_tao, max_fee_tao, ...)` caps spending. `RegisterSubnet` cannot be bounded, so it needs a client without a spend cap.
- The localnet image (`subtensor-localnet:latest` and `devnet-ready`) lacks storage that the `BurnedRegister` and `AddStake` intents preflight (`CollateralLockShare`). Workaround: submit raw calls with `bt.calls.SubtensorModule.*` through `submit_call`. Check `SetWeights` and `ServeAxon` against the localnet before relying on them.

## Localnet

`scripts/localnet/up.sh` starts the arm64 Docker image. `scripts/localnet/setup.py` (run once per fresh chain) funds wallets from the dev account, creates the subnet and registers the owner (uid 0), validator (uid 1), open pool (uid 2) and second pool (uid 3), and stakes the validator.
