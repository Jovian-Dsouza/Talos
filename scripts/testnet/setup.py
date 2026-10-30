"""Create the subnet on Bittensor testnet and register and stake the validator.

The owner coldkey (bittesnor-owner) also acts as the treasury that pays player registrations, so
this script only spends what the budget allows and prints what is left. Wallets are created if
missing and are written unencrypted so services can run unattended; use encrypted wallets for
anything that holds real value.

Usage: python scripts/testnet/setup.py   (CHAIN_ENDPOINT defaults to the named network "test")
"""

import os

import bittensor as bt

ENDPOINT = os.environ.get("CHAIN_ENDPOINT", "test")
VALIDATOR_STAKE_TAO = float(os.environ.get("STAKE_TAO", "0.5"))
VALIDATOR_FUNDING_TAO = float(os.environ.get("VALIDATOR_FUNDING_TAO", "0.7"))  # burn, fees and the stake
OWNER = "bittesnor-owner"
VALIDATOR = "bittesnor-validator"


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


def balance(st: bt.Subtensor, wallet: bt.Wallet) -> float:
    return st.read("balance", coldkey_ss58=wallet.coldkeypub.ss58_address).tao


def main() -> None:
    st = bt.Subtensor(ENDPOINT)
    owner, validator = ensure_wallet(OWNER), ensure_wallet(VALIDATOR)
    for wallet in (owner, validator):
        print(wallet.name, "coldkey", wallet.coldkeypub.ss58_address, "hotkey", wallet.hotkey.ss58_address)
    lock_cost = st.read("subnet_registration_cost").tao
    have = balance(st, owner)
    need = lock_cost + VALIDATOR_FUNDING_TAO
    print(f"owner balance {have} TAO, subnet lock cost {lock_cost} TAO, validator funding {VALIDATOR_FUNDING_TAO} TAO")
    if have < need:
        raise SystemExit(f"need at least {need} TAO in the owner coldkey, have {have}. Fund it from the faucet.")
    if input("Create the subnet and register the validator? [y/N] ").strip().lower() != "y":
        return

    # The subnet cost is only known at execution time, so no spend cap here.
    must(st.execute(bt.RegisterSubnet(hotkey_ss58=owner.hotkey.ss58_address), owner), "register subnet")
    netuid = max(info.netuid for info in st.read("subnets"))
    print("subnet netuid", netuid)
    sub = bt.calls.SubtensorModule
    # Staking and emissions stay off until the owner starts the subnet.
    must(st.submit_call(sub.start_call(netuid=netuid), owner), "start subnet")
    must(st.execute(bt.Transfer(validator.coldkeypub.ss58_address, VALIDATOR_FUNDING_TAO), owner), "fund validator")
    must(st.submit_call(sub.burned_register(netuid=netuid, hotkey=validator.hotkey.ss58_address), validator),
         "register validator")
    stake = sub.add_stake(hotkey=validator.hotkey.ss58_address, netuid=netuid,
                          amount_staked=int(VALIDATOR_STAKE_TAO * 10**9))
    must(st.submit_call(stake, validator), "stake validator")
    print("validator uid", st.read("uid", hotkey_ss58=validator.hotkey.ss58_address, netuid=netuid))
    print(f"owner (treasury) balance left: {balance(st, owner)} TAO")
    print(f"done. Next: NETUID={netuid} python scripts/testnet/export_secrets.py")


main()
