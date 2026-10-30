"""Localnet only: turn off commit-reveal and the weights rate limit so plain set_weights works.

Run after setup.py. Needs the dev sudo account (Alice), which exists on development chains.
"""

import sys
import time

import bittensor as bt

ENDPOINT = "ws://127.0.0.1:9944"
ATTEMPTS = 20  # admin calls are refused inside the protected weights window near each tempo


def main(netuid: int) -> None:
    st = bt.Subtensor(ENDPOINT)
    alice = bt.Wallet(name="alice", hotkey="default")
    admin = bt.calls.AdminUtils
    for call in (
        admin.sudo_set_commit_reveal_weights_enabled(netuid=netuid, enabled=False),
        admin.sudo_set_weights_set_rate_limit(netuid=netuid, weights_set_rate_limit=0),
    ):
        for _ in range(ATTEMPTS):
            result = st.submit_call(bt.calls.Sudo.sudo(call=st.compose(call)), alice)
            if result.success or "protected weights window" not in str(result.message):
                break
            time.sleep(1)
        print(result.success, result.message)


main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
