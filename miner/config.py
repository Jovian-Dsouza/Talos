"""Hosted miner settings, read once from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from common.scene import DEFAULT_TASKS, SCENE_BUILDERS


def _csv(name: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in os.environ.get(name, "").split(",") if part.strip())


def _task_ids() -> tuple[str, ...]:
    """Tasks the service offers, first is the default. Fails at startup on an unknown name."""
    tasks = _csv("TASK_IDS") or DEFAULT_TASKS
    unknown = [task for task in tasks if task not in SCENE_BUILDERS]
    if unknown:
        raise ValueError(f"TASK_IDS names unknown tasks: {', '.join(unknown)}")
    return tasks


def _treasury_secret(chain_endpoint: str) -> str:
    """The dev account pays on a local chain; anywhere else the treasury key must be supplied."""
    secret = os.environ.get("TREASURY_MNEMONIC", "")
    if secret:
        return secret
    if chain_endpoint.startswith(("ws://127.0.0.1", "ws://localhost")):
        return "//Alice"
    raise RuntimeError("TREASURY_MNEMONIC is required on a public network")


@dataclass(frozen=True)
class MinerConfig:
    chain_endpoint: str
    netuid: int
    host: str
    port: int
    data_dir: Path
    database_url: str
    allowed_origins: tuple[str, ...]
    validator_allowlist: tuple[str, ...]
    task_ids: tuple[str, ...]
    trust_proxy: bool
    treasury_mnemonic: str
    wallet_encryption_key: str

    @staticmethod
    def from_env() -> "MinerConfig":
        key = os.environ.get("WALLET_ENCRYPTION_KEY", "")
        if not key:
            raise RuntimeError("WALLET_ENCRYPTION_KEY is required")
        chain_endpoint = os.environ.get("CHAIN_ENDPOINT", "ws://127.0.0.1:9944")
        data_dir = Path(os.environ.get("MINER_DATA_DIR", "data/hosted"))
        return MinerConfig(
            chain_endpoint=chain_endpoint,
            netuid=int(os.environ.get("NETUID", "2")),
            host=os.environ.get("MINER_HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", os.environ.get("MINER_PORT", "8091"))),
            data_dir=data_dir,
            database_url=os.environ.get("DATABASE_URL", f"sqlite:///{data_dir}/accounts.db"),
            allowed_origins=_csv("MINER_ALLOWED_ORIGINS") or ("*",),
            validator_allowlist=_csv("MINER_VALIDATOR_ALLOWLIST"),
            task_ids=_task_ids(),
            trust_proxy=os.environ.get("MINER_TRUST_PROXY", "0") == "1",
            treasury_mnemonic=_treasury_secret(chain_endpoint),
            wallet_encryption_key=key,
        )
