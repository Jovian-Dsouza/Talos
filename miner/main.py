"""Run the open-pool miner: publish the endpoint on chain, then serve HTTP."""

import bittensor as bt
import uvicorn

from common.chain import Chain
from miner.app import create_app
from miner.config import MinerConfig


def main() -> None:
    config = MinerConfig.from_env()
    wallet = bt.Wallet(name=config.wallet_name, hotkey=config.hotkey_name)
    hotkey = wallet.hotkey.ss58_address
    chain = Chain(config.chain_endpoint, config.netuid)
    if config.publish_endpoint:
        chain.serve_endpoint(wallet, config.public_ip, config.port)
        print(f"published endpoint {config.public_ip}:{config.port} for {hotkey}")
    uvicorn.run(create_app(config, hotkey, chain), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
