"""Create the owner and validator wallets, fund them from the localnet dev account, create the subnet,
register and stake the validator. Players are registered later by the hosted miner (the treasury is Alice).

Run once per fresh chain, after scripts/localnet/up.sh (it creates a new subnet each run). Uses the well-known public dev seed for Alice, which only
exists on development chains. Wallets are written unencrypted under ~/.bittensor/wallets.
"""

import bittensor as bt

ENDPOINT = "ws://127.0.0.1:9944"
ALICE_SEED = "0xe5be9a5092b81bca64be81d212e7f2f9eba183bb7a90954f7b76361f6edb5c0a"
FUND_TAO = 2000
STAKE_TAO = 500

OWNER = "bittesnor-owner"
VALIDATOR = "bittesnor-validator"


def must(result, what: str):
    if not result.success:
        raise RuntimeError(f"{what} failed: {result.message}")
    return result


def ensure_wallet(name: str, hotkey: str) -> bt.Wallet:
    wallet = bt.Wallet(name=name, hotkey=hotkey)
    if not wallet.coldkey_file.exists_on_device():
        wallet.create_new_coldkey(use_password=False, suppress=True)
    if not wallet.hotkey_file.exists_on_device():
        wallet.create_new_hotkey(use_password=False, suppress=True)
    return wallet


def alice_wallet() -> bt.Wallet:
    wallet = bt.Wallet(name="alice", hotkey="default")
    if not wallet.coldkey_file.exists_on_device():
        wallet.regenerate_coldkey(seed=ALICE_SEED, use_password=False, suppress=True)
    if not wallet.hotkey_file.exists_on_device():
        wallet.create_new_hotkey(use_password=False, suppress=True)
    return wallet


def main() -> None:
    st = bt.Subtensor(ENDPOINT, policy=bt.Policy(max_spend_tao=100_000, max_fee_tao=100))
    print("chain block", st.block)

    alice = alice_wallet()
    owner = ensure_wallet(OWNER, "default")
    validator = ensure_wallet(VALIDATOR, "default")

    for wallet in (owner, validator):
        if st.read("balance", coldkey_ss58=wallet.coldkeypub.ss58_address).tao < FUND_TAO / 2:
            must(st.execute(bt.Transfer(wallet.coldkeypub.ss58_address, FUND_TAO), alice), "transfer")
    print("funded wallets")

    # Subnet creation cost is only known at execution time, so a spend cap would block it.
    # Localnet only: the dev chain has no real money at stake.
    uncapped = bt.Subtensor(ENDPOINT)
    must(uncapped.execute(bt.RegisterSubnet(hotkey_ss58=owner.hotkey.ss58_address), owner), "register subnet")
    netuid = max(info.netuid for info in st.read("subnets"))
    print("subnet netuid", netuid)

    # The intent preflight reads storage the localnet runtime lacks, so submit raw calls.
    sub = bt.calls.SubtensorModule
    call = sub.burned_register(netuid=netuid, hotkey=validator.hotkey.ss58_address)
    must(uncapped.submit_call(call, validator), "burned register")
    # Staking and emissions stay disabled until the owner starts the subnet.
    must(uncapped.submit_call(sub.start_call(netuid=netuid), owner), "start subnet")
    stake = sub.add_stake(
        hotkey=validator.hotkey.ss58_address, netuid=netuid, amount_staked=STAKE_TAO * 10**9
    )
    must(uncapped.submit_call(stake, validator), "add stake")
    for wallet in (owner, validator):
        print(wallet.name, "uid", st.read("uid", hotkey_ss58=wallet.hotkey.ss58_address, netuid=netuid))
    print(f"subnet registered. Run: NETUID={netuid} scripts/localnet/run_all.sh")


main()
