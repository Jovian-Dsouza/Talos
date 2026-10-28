"""Merkle root over accepted trajectory hashes, committed once per epoch."""

import hashlib


def _pair(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(left + right).digest()


def merkle_root(leaves: list[str]) -> str:
    """Root of the sorted hex leaf hashes; the empty set has a fixed all-zero root."""
    if not leaves:
        return "00" * 32
    level = [bytes.fromhex(leaf) if len(leaf) == 64 else hashlib.sha256(leaf.encode()).digest()
             for leaf in sorted(leaves)]
    while len(level) > 1:
        if len(level) % 2:
            level = [*level, level[-1]]
        level = [_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0].hex()
