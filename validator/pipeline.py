"""Per-recording validation: ticket, replay, success, duplicate, quality, score."""

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol

import mujoco

from common.bundle import BundleError, parse_bundle
from common.mjcf import model_hash
from common.schema import Verdict, rejected
from common.ticket import TICKET_TTL_BLOCKS, ticket_problem
from validator import scoring
from validator.merkle import merkle_root
from validator.quality import home_end_effector, score_quality
from validator.replay import replay
from validator.signature import DUPLICATE_DISTANCE, nearest_distance, novelty, path_signature
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


@dataclass(frozen=True)
class Context:
    config: PipelineConfig
    store: Store
    chain: ChainView
    demand: Mapping[str, float]
    accepted_dir: Path | None = None


def process(raw: Mapping[str, Any], miner_hotkey: str, ctx: Context) -> tuple[str, Verdict]:
    """Validate one recording; returns (bundle_id, verdict). Never raises on bad input."""
    try:
        bundle = parse_bundle(raw)
    except BundleError as exc:
        return "", rejected(f"malformed upload: {exc}")
    bundle_id = bundle.bundle_id()
    verdict = _evaluate(bundle, bundle_id, miner_hotkey, ctx)
    if verdict.accepted and ctx.accepted_dir is not None:
        ctx.accepted_dir.mkdir(parents=True, exist_ok=True)
        (ctx.accepted_dir / f"{bundle_id}.json").write_text(json.dumps(raw))
    ctx.store.add_verdict(bundle_id, miner_hotkey, verdict.to_dict())
    return bundle_id, verdict


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

    quality = score_quality(result.ee_path, bundle.ctrl, ticket.scene_spec,
                            result.arm_contact_steps, _HOME_EE())
    novelty_score = novelty(nearest)
    epoch = current // cfg.tempo_blocks
    prior = ctx.store.accepted_count(ticket.hotkey, ticket.task_id, epoch)
    value = scoring.episode_value(ctx.demand, ticket.task_id, quality.score, novelty_score, prior)
    ctx.store.add_accepted(
        AcceptedRow(bundle_id, ticket.hotkey, ticket.task_id, epoch, bundle.contributor,
                    bundle_id, quality.score, novelty_score, value),
        signature,
    )
    return Verdict(True, "accepted", drift, True, quality.score, novelty_score, value)


_home_cache: list = []


def _HOME_EE():
    if not _home_cache:
        _home_cache.append(home_end_effector())
    return _home_cache[0]


def epoch_root(store: Store, epoch: int) -> tuple[str, int]:
    leaves = store.leaves(epoch)
    return merkle_root(leaves), len(leaves)
