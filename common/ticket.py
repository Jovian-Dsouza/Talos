"""Ticket construction (miner) and verification (validator) from the same derivation."""

from common.mjcf import scene_xml
from common.scene import make_scene, task_config
from common.schema import Ticket
from common.seed import derive_seed

TICKET_TTL_BLOCKS = 720  # two default tempos of 360 blocks


def build_ticket(
    block: int, block_hash: str, hotkey: str, task_id: str, counter: int,
    ttl_blocks: int = TICKET_TTL_BLOCKS,
) -> Ticket:
    task_config(task_id)
    seed = derive_seed(block_hash, hotkey, task_id, counter)
    spec = make_scene(task_id, seed)
    return Ticket(
        block=block,
        block_hash=block_hash,
        hotkey=hotkey,
        task_id=task_id,
        counter=counter,
        seed=seed,
        scene_spec=spec,
        scene_xml=scene_xml(spec),
        instruction=spec["instruction"],
        expires_block=block + ttl_blocks,
    )


def ticket_problem(
    ticket: Ticket, expected_hotkey: str, chain_block_hash: str | None, current_block: int,
    ttl_blocks: int = TICKET_TTL_BLOCKS,
) -> str | None:
    """Return why a ticket is invalid, or None when every check passes."""
    if ticket.hotkey != expected_hotkey:
        return "ticket hotkey does not match the serving pool"
    try:
        task_config(ticket.task_id)
    except FileNotFoundError:
        return "unknown task"
    if chain_block_hash is None or chain_block_hash != ticket.block_hash:
        return "block hash does not match the chain"
    if ticket.expires_block != ticket.block + ttl_blocks:
        return "wrong expiry"
    if current_block > ticket.expires_block:
        return "ticket expired"
    expected = build_ticket(ticket.block, ticket.block_hash, ticket.hotkey, ticket.task_id,
                            ticket.counter, ttl_blocks)
    if ticket.seed != expected.seed:
        return "seed does not derive from the ticket fields"
    if ticket.scene_spec != expected.scene_spec or ticket.instruction != expected.instruction:
        return "scene does not match the seed"
    if ticket.scene_xml != expected.scene_xml:
        return "scene model does not match the seed"
    return None
