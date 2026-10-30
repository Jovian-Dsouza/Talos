"""Backend-paid miner registration: treasury funds the player's coldkey, which burns to register.

One player at a time, oldest first. Each step records its status before the next, so a restart
resumes where it stopped (pending -> funding -> registering -> registered). Transient refusals
(treasury low, daily cap) leave the player pending with the reason in reg_error.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass

from accounts.keys import CustodialWallet, KeyVault
from accounts.store import AccountStore, User
from common.chain import Chain

log = logging.getLogger("registrar")
RAO_PER_TAO = 10**9


@dataclass(frozen=True)
class RegistrarSettings:
    max_burn_rao: int
    fee_margin_rao: int
    max_signups_per_day: int
    max_uids: int
    max_attempts: int
    idle_seconds: float

    @staticmethod
    def from_env() -> "RegistrarSettings":
        return RegistrarSettings(
            max_burn_rao=int(float(os.environ.get("MAX_BURN_TAO", "0.05")) * RAO_PER_TAO),
            fee_margin_rao=int(float(os.environ.get("FEE_MARGIN_TAO", "0.005")) * RAO_PER_TAO),
            max_signups_per_day=int(os.environ.get("MAX_SIGNUPS_PER_DAY", "200")),
            max_uids=int(os.environ.get("MAX_UIDS", "256")),
            max_attempts=int(os.environ.get("REGISTRATION_ATTEMPTS", "3")),
            idle_seconds=float(os.environ.get("REGISTRAR_IDLE_SECONDS", "2")),
        )


class Registrar:
    def __init__(self, store: AccountStore, vault: KeyVault, chain: Chain, treasury: CustodialWallet,
                 settings: RegistrarSettings) -> None:
        self._store, self._vault, self._chain = store, vault, chain
        self._treasury, self._cfg = treasury, settings
        self._attempts: dict[int, int] = {}
        self._stop = threading.Event()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self._loop, name="registrar", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self.step()
            except Exception:
                log.exception("registrar step crashed")
                worked = False
            if not worked:
                self._stop.wait(self._cfg.idle_seconds)

    def step(self) -> bool:
        """Advance the oldest unfinished player. True when something moved."""
        user = self._store.next_pending()
        if user is None:
            return False
        try:
            return self._advance(user)
        except Exception as exc:
            attempts = self._attempts.get(user.id, 0) + 1
            self._attempts[user.id] = attempts
            log.warning("registration of %s failed (%d): %s", user.wallet.hotkey_ss58[:8], attempts, exc)
            if attempts >= self._cfg.max_attempts:
                self._store.set_status(user.id, "failed", str(exc))
            else:
                time.sleep(self._cfg.idle_seconds)
            return True

    def _hold(self, user: User, reason: str) -> bool:
        self._store.set_status(user.id, user.reg_status, reason)
        return False

    def _advance(self, user: User) -> bool:
        chain, cfg = self._chain, self._cfg
        hotkey = user.wallet.hotkey_ss58
        uid = chain.uid_of(hotkey)
        if uid is not None:
            self._store.set_status(user.id, "registered", uid=uid)
            return True
        if user.reg_status == "pending":
            if self._store.registered_today() >= cfg.max_signups_per_day:
                return self._hold(user, "daily signup limit reached, try again later")
            if len(chain.neurons()) >= cfg.max_uids:
                self._store.set_status(user.id, "failed", "the subnet has no free slots")
                return True
        burn = chain.burn_rao()
        if burn > cfg.max_burn_rao:
            return self._hold(user, f"registration cost {burn / RAO_PER_TAO:.3f} TAO is above the cap")
        need = burn + cfg.fee_margin_rao
        have = chain.balance_rao(user.wallet.coldkey_ss58)
        if have < need:
            top_up = need - have
            if chain.balance_rao(self._treasury.coldkey_ss58) < top_up + cfg.fee_margin_rao:
                return self._hold(user, "treasury is low, registration is waiting for funds")
            self._store.set_status(user.id, "funding")
            chain.transfer(self._treasury, user.wallet.coldkey_ss58, top_up)
        self._store.set_status(user.id, "registering")
        chain.burned_register(self._vault.open(user.wallet), hotkey)
        uid = chain.uid_of(hotkey)
        if uid is None:
            raise RuntimeError("registration was accepted but no UID appeared yet")
        self._store.set_status(user.id, "registered", uid=uid)
        log.info("registered %s as uid %d", hotkey[:8], uid)
        return True
