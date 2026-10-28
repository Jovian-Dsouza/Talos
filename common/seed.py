"""Seed derivation shared by miner and validator.

seed = H(block_hash | hotkey | task_id | counter)

Every field is length-prefixed so that distinct tuples can never hash to the
same byte string. Any validator can recompute the seed from public data.
"""

import hashlib
import struct

SEED_BITS = 64


def _field(value: bytes) -> bytes:
    return struct.pack(">I", len(value)) + value


def derive_seed(block_hash: str, hotkey: str, task_id: str, counter: int) -> int:
    if counter < 0:
        raise ValueError("counter must be non-negative")
    payload = b"".join(
        (
            _field(bytes.fromhex(block_hash.removeprefix("0x"))),
            _field(hotkey.encode()),
            _field(task_id.encode()),
            _field(struct.pack(">Q", counter)),
        )
    )
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[: SEED_BITS // 8], "big")
