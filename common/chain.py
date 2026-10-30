"""Thin adapter over the Bittensor SDK 11 client.

Everything chain related goes through this module so SDK changes stay in one place.
"""

import ipaddress
import os
import re
from dataclasses import dataclass
from typing import Sequence

import bittensor as bt
import httpx

LOCALNET = "ws://127.0.0.1:9944"
U16_MAX = 65535
BLOCK_HASH_CACHE = 4096
SUBNET_NAME = "taunet"
SUBNET_DESCRIPTION = "Robot teleoperation data from players, verified by physics replay"


def netuid_from_env(chain_endpoint: str) -> int:
    """NETUID is mandatory off a local chain, so a missing value can never point at someone else's subnet."""
    raw = os.environ.get("NETUID")
    if raw:
        return int(raw)
    if chain_endpoint.startswith(("ws://127.0.0.1", "ws://localhost")):
        return 2
    raise RuntimeError("NETUID is required when CHAIN_ENDPOINT is not a local chain")


class ChainCallError(RuntimeError):
    """A submitted extrinsic was rejected; the SDK reports this in the result, not as an exception."""


def _must(result, what: str) -> None:
    if not result.success:
        raise ChainCallError(f"{what} failed: {result.message}")


@dataclass(frozen=True)
class NeuronView:
    uid: int
    hotkey: str
    validator_permit: bool
    stake: float
    endpoint: tuple[str, int] | None
    incentive: float = 0.0  # share of subnet incentive, 0..1
    emission: int = 0  # rao per tempo
    sets_weights: bool = False  # only validators ever set weights


def _endpoint(axon: dict) -> tuple[str, int] | None:
    if not axon or not axon.get("port") or not axon.get("ip"):
        return None
    return str(ipaddress.ip_address(int(axon["ip"]))), int(axon["port"])


class Chain:
    def __init__(self, endpoint: str, netuid: int) -> None:
        self.netuid = netuid
        self._st = bt.Subtensor(endpoint)
        self._hashes: dict[int, str] = {}

    def current_block(self) -> int:
        return int(self._st.block)

    def block_hash(self, block: int) -> str | None:
        """Hash of a block, or None when the node cannot say. Only found hashes are cached."""
        found = self._hashes.get(block)
        if found is None:
            found = self._fetch_block_hash(block)
            if found is not None:
                if len(self._hashes) >= BLOCK_HASH_CACHE:
                    self._hashes.pop(next(iter(self._hashes)))
                self._hashes[block] = found
        return found

    def _fetch_block_hash(self, block: int) -> str | None:
        """Plain chain_getBlockHash RPC. Block hashes outlive state pruning, unlike the SDK's
        block_info, which fails once a non-archive node discards the block's state (the Docker
        localnet keeps only 256 blocks, about a minute and a half of fast blocks)."""
        url = re.sub(r"^ws", "http", self._st.endpoint)
        request = {"jsonrpc": "2.0", "id": 1, "method": "chain_getBlockHash", "params": [block]}
        try:
            response = httpx.post(url, json=request, timeout=10)
            response.raise_for_status()
            result = response.json().get("result")
        except (httpx.HTTPError, ValueError):
            return None
        return str(result).removeprefix("0x") if result else None

    def tempo(self) -> int:
        return int(self._st.read("metagraph", netuid=self.netuid)["tempo"])

    def neurons(self) -> list[NeuronView]:
        views = []
        for n in self._st.read("neurons", netuid=self.netuid, lite=False):
            raw = n.raw if isinstance(n.raw, dict) else {}
            views.append(
                NeuronView(
                    uid=int(n.uid),
                    hotkey=str(n.hotkey),
                    validator_permit=bool(n.validator_permit),
                    stake=float(n.total_stake.alpha),
                    endpoint=_endpoint(raw.get("axon_info", {})),
                    incentive=float(raw.get("incentive", 0)) / U16_MAX,
                    emission=int(raw.get("emission", 0)),
                    sets_weights=bool(raw.get("weights")),
                )
            )
        return views

    def balance_rao(self, coldkey_ss58: str) -> int:
        return int(self._st.read("balance", coldkey_ss58=coldkey_ss58).rao)

    def burn_rao(self) -> int:
        """Current cost to register one neuron on this subnet."""
        return int(self._st.read("burn", netuid=self.netuid).rao)

    def uid_of(self, hotkey_ss58: str) -> int | None:
        uid = self._st.read("uid", hotkey_ss58=hotkey_ss58, netuid=self.netuid)
        return None if uid is None else int(uid)

    def transfer(self, wallet: "bt.Wallet", dest_ss58: str, amount_rao: int) -> None:
        amount = bt.Balance.from_rao(amount_rao)
        _must(self._st.execute(bt.Transfer(dest_ss58, amount), wallet), "transfer")

    def burned_register(self, wallet: "bt.Wallet", hotkey_ss58: str) -> None:
        """Register `hotkey_ss58` on the subnet, paid by the wallet's coldkey. Raw call because the
        BurnedRegister intent preflights storage the Docker localnet runtime lacks."""
        call = bt.calls.SubtensorModule.burned_register(netuid=self.netuid, hotkey=hotkey_ss58)
        _must(self._st.submit_call(call, wallet), "burned register")

    def latest_commitment(self, hotkey_ss58: str) -> dict | None:
        """The hotkey's latest on-chain commitment, the validator's epoch Merkle root ("e<epoch>:<root>")."""
        try:
            found = self._st.read("commitment", netuid=self.netuid, hotkey_ss58=hotkey_ss58)
        except Exception:
            return None
        epoch, _, root = str(getattr(found, "data", "") or "").partition(":")
        if found is None or not root or not epoch.startswith("e"):
            return None
        return {"epoch": int(epoch[1:]), "root": root, "block": int(found.block)}

    def serve_endpoint(self, wallet: "bt.Wallet", ip: str, port: int) -> None:
        _must(self._st.execute(bt.ServeAxon(self.netuid, ip, port), wallet), "serve endpoint")

    def set_weights(self, wallet: "bt.Wallet", uids: Sequence[int], weights: Sequence[float]) -> None:
        """Use the SDK intent (handles commit-reveal); fall back to a raw plain call when the
        runtime lacks storage the intent preflights, as the Docker localnet does."""
        try:
            _must(self._st.execute(bt.SetWeights(self.netuid, list(uids), list(weights)), wallet), "set weights")
        except Exception as exc:
            if "not found" not in str(exc):
                raise
            peak = max(weights)
            scaled = [round(w / peak * 65535) for w in weights]
            call = bt.calls.SubtensorModule.set_weights(
                netuid=self.netuid, dests=list(uids), weights=scaled, version_key=0
            )
            _must(self._st.submit_call(call, wallet, signer="hotkey"), "set weights (raw)")

    def subnet_name(self) -> str | None:
        """The subnet's on-chain identity name, or None when the owner never published one."""
        try:
            identity = self._st.read("subnet_identity", netuid=self.netuid)
        except Exception:
            return None
        name = (identity or {}).get("subnet_name")
        return str(name) if name else None

    def set_subnet_identity(self, wallet: "bt.Wallet", name: str, description: str, repo: str = "") -> None:
        """Publish the subnet's name, owner coldkey signed. Same raw call fallback as set_weights."""
        intent = bt.SetSubnetIdentity(self.netuid, name, github_repo=repo, description=description)
        try:
            _must(self._st.execute(intent, wallet), "set subnet identity")
        except Exception as exc:
            if "not found" not in str(exc):
                raise
            fields = {k: b"" for k in ("subnet_contact", "subnet_url", "discord", "logo_url", "additional")}
            call = bt.calls.SubtensorModule.set_subnet_identity(
                netuid=self.netuid, subnet_name=name.encode(), github_repo=repo.encode(),
                description=description.encode(), **fields,
            )
            _must(self._st.submit_call(call, wallet), "set subnet identity (raw)")

    def commit_root(self, wallet: "bt.Wallet", epoch: int, root: str) -> None:
        """Publish the epoch's Merkle root as a hotkey-signed on-chain commitment."""
        data = f"e{epoch}:{root}".encode()
        call = bt.calls.Commitments.set_commitment(
            netuid=self.netuid, info={"fields": [[{f"Raw{len(data)}": data}]]}
        )
        _must(self._st.submit_call(call, wallet, signer="hotkey"), "commit root")
