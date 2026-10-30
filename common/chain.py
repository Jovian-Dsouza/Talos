"""Thin adapter over the Bittensor SDK 11 client.

Everything chain related goes through this module so SDK changes stay in one place.
"""

import ipaddress
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import bittensor as bt

LOCALNET = "ws://127.0.0.1:9944"


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


def _endpoint(axon: dict) -> tuple[str, int] | None:
    if not axon or not axon.get("port") or not axon.get("ip"):
        return None
    return str(ipaddress.ip_address(int(axon["ip"]))), int(axon["port"])


class Chain:
    def __init__(self, endpoint: str, netuid: int) -> None:
        self.netuid = netuid
        self._st = bt.Subtensor(endpoint)

    def current_block(self) -> int:
        return int(self._st.block)

    def block_hash(self, block: int) -> str | None:
        return _cached_block_hash(self, block)

    def _fetch_block_hash(self, block: int) -> str | None:
        try:
            return str(self._st.block_info(block).hash).removeprefix("0x")
        except Exception:
            return None

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

    def commit_root(self, wallet: "bt.Wallet", epoch: int, root: str) -> None:
        """Publish the epoch's Merkle root as a hotkey-signed on-chain commitment."""
        data = f"e{epoch}:{root}".encode()
        call = bt.calls.Commitments.set_commitment(
            netuid=self.netuid, info={"fields": [[{f"Raw{len(data)}": data}]]}
        )
        _must(self._st.submit_call(call, wallet, signer="hotkey"), "commit root")


@lru_cache(maxsize=4096)
def _cached_block_hash(chain: Chain, block: int) -> str | None:
    return chain._fetch_block_hash(block)
