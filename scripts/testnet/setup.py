"""Create the subnet and register neurons on Bittensor testnet.

Needs testnet TAO in the owner coldkey (about 1 TAO for the subnet plus registration burns and
stake). Wallets are created if missing and are written unencrypted so services can run unattended;
use encrypted wallets for anything that holds real value.

Usage: python scripts/testnet/setup.py   (CHAIN_ENDPOINT defaults to the named network "test")
"""

import os

import bittensor as bt

ENDPOINT = os.environ.get("CHAIN_ENDPOINT", "test")
STAKE_TAO = float(os.environ.get("STAKE_TAO", "5"))
OWNER = "bittesnor-owner"
VALIDATOR = "bittesnor-validator"
POOLS = ("pool-open", "pool-two")


def must(result, what: str):
    if not result.success:
        raise RuntimeError(f"{what} failed: {result.message}")
    return result


def ensure_wallet(name: str) -> bt.Wallet:
    wallet = bt.Wallet(name=name, hotkey="default")
    if not wallet.coldkey_file.exists_on_device():
        wallet.create_new_coldkey(use_password=False, suppress=True)
    if not wallet.hotkey_file.exists_on_device():
        wallet.create_new_hotkey(use_password=False, suppress=True)
    return wallet


def main() -> None:
    st = bt.Subtensor(ENDPOINT)
    owner = ensure_wallet(OWNER)
    validator = ensure_wallet(VALIDATOR)
    pools = [ensure_wallet(f"bittesnor-{p}") for p in POOLS]
    for wallet in (owner, validator, *pools):
        print(wallet.name, "coldkey", wallet.coldkeypub.ss58_address, "hotkey", wallet.hotkey.ss58_address)
    balance = st.read("balance", coldkey_ss58=owner.coldkeypub.ss58_address)
    print("owner balance", balance)
    if input("Create the subnet and register neurons? [y/N] ").strip().lower() != "y":
        return

    # The subnet cost is only known at execution time, so no spend cap here.
    must(st.execute(bt.RegisterSubnet(hotkey_ss58=owner.hotkey.ss58_address), owner), "register subnet")
    netuid = max(info.netuid for info in st.read("subnets"))
    print("subnet netuid", netuid)
    sub = bt.calls.SubtensorModule
    # Staking and emissions stay off until the owner starts the subnet.
    must(st.submit_call(sub.start_call(netuid=netuid), owner), "start subnet")
    for wallet in (validator, *pools):
        # The coldkey must hold TAO: send some from the owner first (bt.Transfer) if it is empty.
        must(st.submit_call(sub.burned_register(netuid=netuid, hotkey=wallet.hotkey.ss58_address), wallet),
             f"register {wallet.name}")
    stake = sub.add_stake(hotkey=validator.hotkey.ss58_address, netuid=netuid,
                          amount_staked=int(STAKE_TAO * 10**9))
    must(st.submit_call(stake, validator), "stake validator")
    print(f"done. Export NETUID={netuid} CHAIN_ENDPOINT={ENDPOINT} for the miner and validator.")


main()
