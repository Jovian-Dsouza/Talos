"""Write the hosted deployment secrets to deploy/secrets.env (gitignored, mode 600).

Nothing is printed: open the file and paste each value into the Render dashboard, then delete the
file. TREASURY_MNEMONIC is the owner coldkey, VALIDATOR_MNEMONIC the validator hotkey, and
WALLET_ENCRYPTION_KEY is a fresh key for the hosted database (keep a copy: losing it loses every
player wallet).

Usage: NETUID=N python scripts/testnet/export_secrets.py
"""

import json
import os
import sys
from pathlib import Path

import bittensor as bt
from cryptography.fernet import Fernet

OUT = Path("deploy/secrets.env")
OWNER = os.environ.get("OWNER_WALLET", "taunet-owner")
VALIDATOR = os.environ.get("VALIDATOR_WALLET", "taunet-validator")


def phrase(path: str) -> str:
    return json.loads((Path.home() / ".bittensor" / "wallets" / path).read_text())["secretPhrase"]


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists. Delete it first so a stored encryption key is never replaced.")
    netuid = os.environ.get("NETUID")
    if not netuid:
        raise SystemExit("set NETUID to the subnet setup.py created")
    validator = bt.Wallet(name=VALIDATOR, hotkey="default").hotkey.ss58_address
    lines = {
        "NETUID": netuid,
        "TREASURY_MNEMONIC": phrase(f"{OWNER}/coldkey"),
        "VALIDATOR_MNEMONIC": phrase(f"{VALIDATOR}/hotkeys/default"),
        "MINER_VALIDATOR_ALLOWLIST": validator,
        "WALLET_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.touch(mode=0o600)
    OUT.write_text("".join(f"{key}={value}\n" for key, value in lines.items()))
    print(f"wrote {len(lines)} values to {OUT}", file=sys.stderr)


main()
