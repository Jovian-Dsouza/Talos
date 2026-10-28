"""Localnet only: turn off commit-reveal and the weights rate limit so plain set_weights works.

Run after setup.py. Needs the dev sudo account (Alice), which exists on development chains.
"""

import sys

import bittensor as bt

ENDPOINT = "ws://127.0.0.1:9944"


def main(netuid: int) -> None:
    st = bt.Subtensor(ENDPOINT)
    alice = bt.Wallet(name="alice", hotkey="default")
    admin = bt.calls.AdminUtils
    for call in (
        admin.sudo_set_commit_reveal_weights_enabled(netuid=netuid, enabled=False),
        admin.sudo_set_weights_set_rate_limit(netuid=netuid, weights_set_rate_limit=0),
    ):
        inner = st.compose(call)
        result = st.submit_call(bt.calls.Sudo.sudo(call=inner), alice)
        print(result.success, result.message)


main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
