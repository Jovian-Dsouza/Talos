"""Background sampler that records each registered player's stake, the history behind the wallet chart."""

import logging
import threading
import time

from miner.deps import AppState

log = logging.getLogger("earnings")

SAMPLE_SECONDS = 30
HEARTBEAT_SECONDS = 600  # record an unchanged stake this often, so a flat period shows up as flat


class StakeSampler(threading.Thread):
    def __init__(self, state: AppState, interval: float = SAMPLE_SECONDS) -> None:
        super().__init__(name="stake-sampler", daemon=True)
        self._state = state
        self._interval = interval
        self._last_write: dict[str, float] = {}

    def run(self) -> None:
        while True:
            try:
                self.sample()
            except Exception:  # a chain hiccup must not stop sampling for good
                log.exception("stake sample failed")
            time.sleep(self._interval)

    def sample(self) -> None:
        state = self._state
        players = state.accounts.hotkeys()
        latest = state.db.latest_stakes()
        block = state.chain.current_block()
        now = time.monotonic()
        rows = [
            (n.hotkey, block, n.stake) for n in state.neurons()
            if n.hotkey in players and (
                latest.get(n.hotkey) != n.stake or now - self._last_write.get(n.hotkey, 0.0) >= HEARTBEAT_SECONDS
            )
        ]
        if rows:
            state.db.add_stake_samples(rows)
            self._last_write = {**self._last_write, **{hotkey: now for hotkey, _, _ in rows}}
