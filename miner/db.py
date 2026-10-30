"""SQLite storage for issued tickets, received bundles and validator verdicts (all players)."""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from common.dblock import locked

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
  counter INTEGER PRIMARY KEY AUTOINCREMENT, hotkey TEXT NOT NULL, block INTEGER NOT NULL,
  block_hash TEXT NOT NULL, seed TEXT NOT NULL, issued_at REAL NOT NULL, submitted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bundles (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, bundle_id TEXT UNIQUE NOT NULL, counter INTEGER NOT NULL,
  hotkey TEXT NOT NULL, contributor TEXT NOT NULL, signature TEXT NOT NULL, path TEXT NOT NULL,
  received_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS verdicts (
  bundle_id TEXT NOT NULL, validator TEXT NOT NULL, verdict TEXT NOT NULL, created_at REAL NOT NULL,
  PRIMARY KEY (bundle_id, validator)
);
"""


class MinerDb:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "bundles").mkdir(exist_ok=True)
        self._dir = data_dir
        self._db = sqlite3.connect(str(data_dir / "miner.db"), check_same_thread=False)
        self._lock = threading.RLock()
        self._db.executescript(SCHEMA)

    @locked
    def issue_ticket_slot(self, hotkey: str, block: int, block_hash: str) -> int:
        """Reserve the next counter. The seed column is filled in once it is derived."""
        with self._db:
            cursor = self._db.execute(
                "INSERT INTO tickets (hotkey, block, block_hash, seed, issued_at) VALUES (?,?,?,?,?)",
                (hotkey, block, block_hash, "", time.time()),
            )
        return int(cursor.lastrowid)

    @locked
    def set_seed(self, counter: int, seed: int) -> None:
        with self._db:
            self._db.execute("UPDATE tickets SET seed=? WHERE counter=?", (str(seed), counter))

    @locked
    def claim_submission(self, hotkey: str, counter: int) -> dict[str, Any] | None:
        """Mark one of this player's tickets as submitted; None if unknown, foreign or already used."""
        with self._db:
            row = self._db.execute(
                "SELECT block, block_hash, seed FROM tickets WHERE counter=? AND hotkey=? AND submitted=0",
                (counter, hotkey),
            ).fetchone()
            if row is None:
                return None
            self._db.execute("UPDATE tickets SET submitted=1 WHERE counter=?", (counter,))
        return {"block": row[0], "block_hash": row[1], "seed": row[2]}

    @locked
    def release_submission(self, counter: int) -> None:
        with self._db:
            self._db.execute("UPDATE tickets SET submitted=0 WHERE counter=?", (counter,))

    @locked
    def add_bundle(self, bundle_id: str, counter: int, hotkey: str, contributor: str, signature: str,
                   raw_text: str) -> int:
        path = self._dir / "bundles" / f"{bundle_id}.json"
        path.write_text(raw_text)
        with self._db:
            cursor = self._db.execute(
                "INSERT INTO bundles (bundle_id, counter, hotkey, contributor, signature, path, received_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (bundle_id, counter, hotkey, contributor, signature, str(path), time.time()),
            )
        return int(cursor.lastrowid)

    @locked
    def bundles_since(self, hotkey: str, seq: int, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT seq, bundle_id, signature, path FROM bundles WHERE hotkey=? AND seq>? ORDER BY seq LIMIT ?",
            (hotkey, seq, limit),
        ).fetchall()
        return [
            {"seq": r[0], "bundle_id": r[1], "miner_signature": r[2], "bundle": json.loads(Path(r[3]).read_text())}
            for r in rows
        ]

    @locked
    def add_verdict(self, hotkey: str, bundle_id: str, validator: str, verdict: dict[str, Any]) -> bool:
        known = self._db.execute(
            "SELECT 1 FROM bundles WHERE bundle_id=? AND hotkey=?", (bundle_id, hotkey)
        ).fetchone()
        if not known:
            return False
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO verdicts VALUES (?,?,?,?)",
                (bundle_id, validator, json.dumps(verdict), time.time()),
            )
        return True

    @locked
    def status(self, bundle_id: str) -> dict[str, Any] | None:
        bundle = self._db.execute(
            "SELECT contributor FROM bundles WHERE bundle_id=?", (bundle_id,)
        ).fetchone()
        if bundle is None:
            return None
        rows = self._db.execute(
            "SELECT validator, verdict FROM verdicts WHERE bundle_id=?", (bundle_id,)
        ).fetchall()
        return {
            "bundle_id": bundle_id,
            "contributor": bundle[0],
            "verdicts": {validator: json.loads(text) for validator, text in rows},
        }

    @locked
    def player_totals(self) -> dict[str, dict[str, Any]]:
        """Per hotkey: runs submitted, accepted and summed score from the first verdict of each run."""
        rows = self._db.execute(
            "SELECT b.hotkey, b.contributor, v.verdict FROM bundles b "
            "JOIN verdicts v ON v.bundle_id=b.bundle_id GROUP BY b.bundle_id"
        ).fetchall()
        totals: dict[str, dict[str, Any]] = {}
        for hotkey, contributor, text in rows:
            verdict = json.loads(text)
            entry = totals.setdefault(hotkey, {"hotkey": hotkey, "contributor": contributor,
                                               "submitted": 0, "accepted": 0, "value": 0.0})
            entry["submitted"] += 1
            if verdict.get("accepted"):
                entry["accepted"] += 1
                entry["value"] += float(verdict.get("score", 0.0))
        return totals

    @locked
    def recent_verdicts(self, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT b.hotkey, b.contributor, v.verdict, v.created_at FROM verdicts v "
            "JOIN bundles b ON b.bundle_id=v.bundle_id ORDER BY v.created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"hotkey": h, "contributor": c, "verdict": json.loads(v), "at": at} for h, c, v, at in rows]
