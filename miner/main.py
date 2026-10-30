"""Run the hosted miner: player accounts, the registrar thread and the HTTP API."""

import logging

import uvicorn

from accounts.clerk import ClerkAuth, ClerkSettings
from accounts.keys import KeyVault, wallet_from_mnemonics
from accounts.registrar import Registrar, RegistrarSettings
from accounts.store import AccountStore
from common.chain import Chain
from miner.app import create_app
from miner.config import MinerConfig
from miner.db import MinerDb
from miner.deps import AppState
from miner.earnings import StakeSampler


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    config = MinerConfig.from_env()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    chain = Chain(config.chain_endpoint, config.netuid)
    vault = KeyVault(config.wallet_encryption_key)
    accounts = AccountStore(config.database_url)
    treasury = wallet_from_mnemonics(config.treasury_mnemonic, config.treasury_mnemonic)
    Registrar(accounts, vault, chain, treasury, RegistrarSettings.from_env()).start()
    state = AppState(
        config=config, db=MinerDb(config.data_dir), chain=chain, accounts=accounts, vault=vault,
        auth=ClerkAuth(ClerkSettings.from_env(config.chain_endpoint)),
    )
    StakeSampler(state).start()
    uvicorn.run(create_app(state), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
