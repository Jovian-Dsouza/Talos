"""Validator settings, read once from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from validator.pipeline import PipelineConfig


def _overrides(raw: str) -> dict[str, str]:
    pairs = (part.split("=", 1) for part in raw.split(",") if "=" in part)
    return {hotkey.strip(): url.strip().rstrip("/") for hotkey, url in pairs}


@dataclass(frozen=True)
class ValidatorConfig:
    chain_endpoint: str
    netuid: int
    wallet_name: str
    hotkey_name: str
    db_path: Path
    poll_seconds: float
    weights_every_blocks: int
    miner_urls: dict[str, str]
    demand_file: str | None
    accepted_dir: Path
    pipeline: PipelineConfig

    @staticmethod
    def from_env() -> "ValidatorConfig":
        return ValidatorConfig(
            chain_endpoint=os.environ.get("CHAIN_ENDPOINT", "ws://127.0.0.1:9944"),
            netuid=int(os.environ.get("NETUID", "2")),
            wallet_name=os.environ.get("VALIDATOR_WALLET", "bittesnor-validator"),
            hotkey_name=os.environ.get("VALIDATOR_HOTKEY", "default"),
            db_path=Path(os.environ.get("VALIDATOR_DB", "data/validator.db")),
            poll_seconds=float(os.environ.get("POLL_SECONDS", "3")),
            weights_every_blocks=int(os.environ.get("WEIGHTS_EVERY_BLOCKS", "10")),
            miner_urls=_overrides(os.environ.get("MINER_URLS", "")),
            demand_file=os.environ.get("DEMAND_FILE"),
            accepted_dir=Path(os.environ.get("ACCEPTED_DIR", "data/accepted")),
            pipeline=PipelineConfig(
                replay_mode=os.environ.get("REPLAY_MODE", "strict"),
                eps_arm=float(os.environ.get("EPS_ARM", "0.01")),
                eps_object=float(os.environ.get("EPS_OBJECT", "0.005")),
                tempo_blocks=int(os.environ.get("TEMPO_BLOCKS", "10")),
            ),
        )
