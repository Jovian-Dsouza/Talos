"""Per-recording validation: ticket, replay, success, duplicate, score."""

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

import mujoco
from bittensor_core import Keypair

from common.bundle import BundleError, parse_bundle
from common.mjcf import model_hash
from common.scene import task_config
from common.schema import Verdict, rejected
from common.ticket import TICKET_TTL_BLOCKS, ticket_problem
from validator import scoring
from validator.merkle import merkle_root
from validator.replay import replay
from validator.signature import DUPLICATE_DISTANCE, nearest_distance, path_signature
from validator.store import AcceptedRow, Store


class ChainView(Protocol):
    def current_block(self) -> int: ...
    def block_hash(self, block: int) -> str | None: ...


@dataclass(frozen=True)
class PipelineConfig:
    replay_mode: str = "strict"
    eps_arm: float = 0.01
    eps_object: float = 0.005
    ttl_blocks: int = TICKET_TTL_BLOCKS
    tempo_blocks: int = 360
    require_miner_signature: bool = True


@dataclass(frozen=True)
class Context:
    config: PipelineConfig
    store: Store
    chain: ChainView
    accepted_dir: Path | None = None


def process(
    raw: Mapping[str, Any], miner_hotkey: str, ctx: Context, miner_signature: str | None = None
) -> tuple[str, Verdict]:
    """Validate one recording; returns (bundle_id, verdict). Never raises on bad input."""
    try:
        bundle = parse_bundle(raw)
    except BundleError as exc:
        return "", rejected(f"malformed upload: {exc}")
    bundle_id = bundle.bundle_id()
    if ctx.config.require_miner_signature and not _signed_by(miner_hotkey, bundle_id, miner_signature):
        verdict = rejected("run not signed by the miner hotkey")
    else:
        verdict = _evaluate(bundle, bundle_id, miner_hotkey, ctx)
    if verdict.accepted and ctx.accepted_dir is not None:
        ctx.accepted_dir.mkdir(parents=True, exist_ok=True)
        (ctx.accepted_dir / f"{bundle_id}.json").write_text(json.dumps(raw))
    ctx.store.add_verdict(bundle_id, miner_hotkey, verdict.to_dict())
    return bundle_id, verdict


def _signed_by(hotkey: str, bundle_id: str, signature: str | None) -> bool:
    if not signature:
        return False
    try:
        return bool(Keypair(ss58_address=hotkey).verify(bundle_id.encode(), bytes.fromhex(signature)))
    except (ValueError, TypeError):
        return False


def _evaluate(bundle, bundle_id: str, miner_hotkey: str, ctx: Context) -> Verdict:
    cfg, ticket = ctx.config, bundle.ticket
    current = ctx.chain.current_block()
    problem = ticket_problem(
        ticket, miner_hotkey, ctx.chain.block_hash(ticket.block), current, cfg.ttl_blocks
    )
    if problem:
        return rejected(problem)
    if bundle.mujoco_version != mujoco.mj_versionString():
        return rejected("MuJoCo version differs from the validator")
    if bundle.model_hash != model_hash(ticket.scene_xml):
        return rejected("model hash mismatch")
    if not ctx.store.claim_ticket(ticket.hotkey, ticket.task_id, ticket.counter, bundle_id):
        return rejected("ticket already used")

    result = replay(bundle, cfg.replay_mode)
    drift = max(result.drift_arm / cfg.eps_arm, result.drift_object / cfg.eps_object)
    if drift > 1.0:
        return rejected("replay does not match the recording", drift, False)
    if not result.success:
        return rejected("task not completed on replay", drift, False)

    signature = path_signature(result.ee_path, ticket.scene_spec)
    nearest = nearest_distance(signature, ctx.store.recent_signatures(ticket.task_id))
    if nearest is not None and nearest < DUPLICATE_DISTANCE:
        return rejected("near duplicate of an accepted episode", drift, True)

    ref_seconds = float(task_config(ticket.task_id)["ref_seconds"])
    episode = scoring.score_episode(result.ee_path, bundle.steps, ref_seconds)
    epoch = current // cfg.tempo_blocks
    ctx.store.add_accepted(
        AcceptedRow(bundle_id, ticket.hotkey, ticket.task_id, epoch, bundle.contributor, bundle_id,
                    episode.time_score, episode.smooth_score, episode.duration_s, episode.score),
        signature,
    )
    return Verdict(True, "accepted", drift, True, episode.time_score, episode.smooth_score,
                   episode.duration_s, episode.score)


def epoch_root(store: Store, epoch: int) -> tuple[str, int]:
    leaves = store.leaves(epoch)
    return merkle_root(leaves), len(leaves)
