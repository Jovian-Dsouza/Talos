"""Validator loop: pull recordings, validate them, push verdicts, set weights, commit epoch roots."""

import logging
import time

import bittensor as bt

from common.chain import Chain, NeuronView
from validator import scoring
from validator.config import ValidatorConfig
from validator.pipeline import Context, epoch_root, process
from validator.pull import fetch_bundles, push_verdicts
from validator.store import Store

log = logging.getLogger("validator")


def miner_url(config: ValidatorConfig, neuron: NeuronView) -> str | None:
    if neuron.hotkey in config.miner_urls:
        return config.miner_urls[neuron.hotkey]
    if neuron.endpoint:
        ip, port = neuron.endpoint
        return f"http://{ip}:{port}"
    return None


def pull_and_validate(config: ValidatorConfig, wallet, ctx: Context, neuron: NeuronView) -> int:
    url = miner_url(config, neuron)
    if url is None:
        return 0
    since = ctx.store.get_cursor(neuron.hotkey)
    try:
        bundles = fetch_bundles(wallet, url, neuron.hotkey, since)
    except Exception as exc:  # network and auth failures must not stop the loop
        log.warning("pull from %s failed: %s", neuron.hotkey[:8], exc)
        return 0
    feed = []
    for item in bundles:
        bundle_id, verdict = process(item["bundle"], neuron.hotkey, ctx)
        log.info("%s %s %s", item["bundle_id"][:8], verdict.accepted, verdict.reason)
        feed.append({"bundle_id": item["bundle_id"], "verdict": verdict.to_dict()})
        ctx.store.set_cursor(neuron.hotkey, item["seq"])
    if feed:
        try:
            push_verdicts(wallet, url, neuron.hotkey, feed)
        except Exception as exc:
            log.warning("push to %s failed: %s", neuron.hotkey[:8], exc)
    return len(bundles)


def set_weights(chain: Chain, wallet, store: Store, neurons: list[NeuronView]) -> None:
    scores = scoring.pool_scores(store.epoch_values())
    shares = scoring.normalize(scores)
    uids = {n.hotkey: n.uid for n in neurons}
    pairs = [(uids[hotkey], share) for hotkey, share in shares.items() if hotkey in uids]
    if not pairs:
        return
    chain.set_weights(wallet, [uid for uid, _ in pairs], [share for _, share in pairs])
    log.info("set weights %s", pairs)


def commit_finished_epochs(chain: Chain, wallet, ctx: Context, last: int, current_epoch: int) -> int:
    for epoch in range(last + 1, current_epoch):
        root, count = epoch_root(ctx.store, epoch)
        ctx.store.save_root(epoch, root, count)
        if count:
            try:
                chain.commit_root(wallet, epoch, root)
                log.info("committed epoch %d root %s (%d episodes)", epoch, root[:12], count)
            except Exception as exc:
                log.warning("commit of epoch %d failed: %s", epoch, exc)
    return max(last, current_epoch - 1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    config = ValidatorConfig.from_env()
    wallet = bt.Wallet(name=config.wallet_name, hotkey=config.hotkey_name)
    chain = Chain(config.chain_endpoint, config.netuid)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    ctx = Context(config.pipeline, Store(config.db_path), chain, scoring.load_demand(config.demand_file),
                  config.accepted_dir)
    me = wallet.hotkey.ss58_address
    last_weights_block = 0
    committed_epoch = chain.current_block() // config.pipeline.tempo_blocks - 1
    log.info("validator %s on subnet %d, replay mode %s", me, config.netuid, config.pipeline.replay_mode)
    while True:
        neurons = chain.neurons()
        for neuron in neurons:
            if neuron.hotkey != me:
                pull_and_validate(config, wallet, ctx, neuron)
        block = chain.current_block()
        committed_epoch = commit_finished_epochs(
            chain, wallet, ctx, committed_epoch, block // config.pipeline.tempo_blocks
        )
        if block - last_weights_block >= config.weights_every_blocks:
            try:
                set_weights(chain, wallet, ctx.store, neurons)
                last_weights_block = block
            except Exception as exc:
                log.warning("set weights failed: %s", exc)
        time.sleep(config.poll_seconds)


if __name__ == "__main__":
    main()
