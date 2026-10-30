"""Miner settings, read once from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from common.scene import DEFAULT_TASKS, SCENE_BUILDERS


def _csv(name: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in os.environ.get(name, "").split(",") if part.strip())


def _task_ids() -> tuple[str, ...]:
    """Tasks this pool serves, first is the default. Fails at startup on an unknown name."""
    tasks = _csv("TASK_IDS") or DEFAULT_TASKS
    unknown = [task for task in tasks if task not in SCENE_BUILDERS]
    if unknown:
        raise ValueError(f"TASK_IDS names unknown tasks: {', '.join(unknown)}")
    return tasks


@dataclass(frozen=True)
class MinerConfig:
    chain_endpoint: str
    netuid: int
    wallet_name: str
    hotkey_name: str
    host: str
    port: int
    public_ip: str
    data_dir: Path
    allowed_origins: tuple[str, ...]
    validator_allowlist: tuple[str, ...]
    task_ids: tuple[str, ...]
    publish_endpoint: bool
    trust_proxy: bool

    @staticmethod
    def from_env() -> "MinerConfig":
        return MinerConfig(
            chain_endpoint=os.environ.get("CHAIN_ENDPOINT", "ws://127.0.0.1:9944"),
            netuid=int(os.environ.get("NETUID", "2")),
            wallet_name=os.environ.get("MINER_WALLET", "bittesnor-pool-open"),
            hotkey_name=os.environ.get("MINER_HOTKEY", "default"),
            host=os.environ.get("MINER_HOST", "0.0.0.0"),
            port=int(os.environ.get("MINER_PORT", "8091")),
            public_ip=os.environ.get("MINER_PUBLIC_IP", "127.0.0.1"),
            data_dir=Path(os.environ.get("MINER_DATA_DIR", "data/miner-open")),
            allowed_origins=_csv("MINER_ALLOWED_ORIGINS") or ("*",),
            validator_allowlist=_csv("MINER_VALIDATOR_ALLOWLIST"),
            task_ids=_task_ids(),
            publish_endpoint=os.environ.get("MINER_PUBLISH_ENDPOINT", "1") == "1",
            trust_proxy=os.environ.get("MINER_TRUST_PROXY", "0") == "1",
        )
