"""SQLite storage for issued tickets, received bundles, validator verdicts and stake samples (all players)."""

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
  received_at REAL NOT NULL, task_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS verdicts (
  bundle_id TEXT NOT NULL, validator TEXT NOT NULL, verdict TEXT NOT NULL, created_at REAL NOT NULL,
  PRIMARY KEY (bundle_id, validator)
);
CREATE TABLE IF NOT EXISTS stake_samples (
  hotkey TEXT NOT NULL, block INTEGER NOT NULL, alpha REAL NOT NULL, at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS stake_samples_by_hotkey ON stake_samples (hotkey, at);
"""

# Each run with its first verdict (the earliest validator to judge it), or NULLs while it waits.
JOBS_SQL = """
WITH first AS (
  SELECT bundle_id, validator, verdict, created_at,
         ROW_NUMBER() OVER (PARTITION BY bundle_id ORDER BY created_at) AS n
  FROM verdicts
)
SELECT b.seq, b.bundle_id, b.hotkey, b.contributor, b.task_id, b.received_at, f.validator, f.verdict, f.created_at
FROM bundles b LEFT JOIN first f ON f.bundle_id = b.bundle_id AND f.n = 1
"""


def _job(row: tuple) -> dict[str, Any]:
    seq, bundle_id, hotkey, contributor, task_id, received_at, validator, verdict, judged_at = row
    return {
        "seq": seq, "bundle_id": bundle_id, "hotkey": hotkey, "contributor": contributor, "task_id": task_id,
        "received_at": received_at, "validator": validator,
        "verdict": json.loads(verdict) if verdict else None, "judged_at": judged_at,
    }


class MinerDb:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "bundles").mkdir(exist_ok=True)
        self._dir = data_dir
        self._db = sqlite3.connect(str(data_dir / "miner.db"), check_same_thread=False)
        self._lock = threading.RLock()
        self._db.executescript(SCHEMA)
        self._add_task_ids()

    def _add_task_ids(self) -> None:
        """Databases from before task_id existed: add the column and fill it from the stored bundles."""
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(bundles)")}
        with self._db:
            if "task_id" not in columns:
                self._db.execute("ALTER TABLE bundles ADD COLUMN task_id TEXT NOT NULL DEFAULT ''")
            for seq, path in self._db.execute("SELECT seq, path FROM bundles WHERE task_id=''").fetchall():
                try:
                    task_id = json.loads(Path(path).read_text())["ticket"]["task_id"]
                except (OSError, ValueError, KeyError, TypeError):
                    continue
                self._db.execute("UPDATE bundles SET task_id=? WHERE seq=?", (task_id, seq))

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
                   task_id: str, raw_text: str) -> int:
        path = self._dir / "bundles" / f"{bundle_id}.json"
        path.write_text(raw_text)
        with self._db:
            cursor = self._db.execute(
                "INSERT INTO bundles (bundle_id, counter, hotkey, contributor, signature, path, received_at, task_id)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (bundle_id, counter, hotkey, contributor, signature, str(path), time.time(), task_id),
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
    def jobs(self, *, hotkey: str | None = None, task_id: str | None = None, since: float = 0.0,
             before_seq: int | None = None, judged_only: bool = False, limit: int = -1) -> list[dict[str, Any]]:
        """Runs newest first, each with its first verdict (None while no validator has judged it)."""
        where, params = ["b.received_at >= ?"], [since]
        if hotkey is not None:
            where.append("b.hotkey = ?")
            params.append(hotkey)
        if task_id is not None:
            where.append("b.task_id = ?")
            params.append(task_id)
        if before_seq is not None:
            where.append("b.seq < ?")
            params.append(before_seq)
        if judged_only:
            where.append("f.verdict IS NOT NULL")
        sql = f"{JOBS_SQL} WHERE {' AND '.join(where)} ORDER BY b.seq DESC LIMIT ?"
        return [_job(row) for row in self._db.execute(sql, (*params, limit)).fetchall()]

    def player_totals(self) -> dict[str, dict[str, Any]]:
        """Per hotkey: runs judged, accepted and summed score from the first verdict of each run."""
        totals: dict[str, dict[str, Any]] = {}
        for job in self.jobs(judged_only=True):
            entry = totals.setdefault(job["hotkey"], {"hotkey": job["hotkey"], "contributor": job["contributor"],
                                                      "submitted": 0, "accepted": 0, "value": 0.0})
            entry["submitted"] += 1
            if job["verdict"].get("accepted"):
                entry["accepted"] += 1
                entry["value"] += float(job["verdict"].get("score", 0.0))
        return totals

    @locked
    def recent_verdicts(self, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT b.hotkey, b.contributor, v.verdict, v.created_at FROM verdicts v "
            "JOIN bundles b ON b.bundle_id=v.bundle_id ORDER BY v.created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"hotkey": h, "contributor": c, "verdict": json.loads(v), "at": at} for h, c, v, at in rows]

    @locked
    def playing_since(self, since: float) -> int:
        """Players holding a ticket issued since `since` that they have not submitted yet."""
        row = self._db.execute(
            "SELECT COUNT(DISTINCT hotkey) FROM tickets WHERE submitted=0 AND issued_at >= ?", (since,)
        ).fetchone()
        return int(row[0])

    @locked
    def validators_since(self, since: float) -> int:
        """Distinct validators that pushed a verdict since `since`."""
        row = self._db.execute(
            "SELECT COUNT(DISTINCT validator) FROM verdicts WHERE created_at >= ?", (since,)
        ).fetchone()
        return int(row[0])

    @locked
    def latest_stakes(self) -> dict[str, float]:
        rows = self._db.execute(
            "SELECT hotkey, alpha FROM stake_samples s WHERE at = (SELECT MAX(at) FROM stake_samples WHERE hotkey=s.hotkey)"
        ).fetchall()
        return {hotkey: alpha for hotkey, alpha in rows}

    @locked
    def add_stake_samples(self, samples: list[tuple[str, int, float]]) -> None:
        now = time.time()
        with self._db:
            self._db.executemany(
                "INSERT INTO stake_samples (hotkey, block, alpha, at) VALUES (?,?,?,?)",
                [(hotkey, block, alpha, now) for hotkey, block, alpha in samples],
            )

    @locked
    def stake_history(self, hotkey: str, limit: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT block, alpha, at FROM stake_samples WHERE hotkey=? ORDER BY at DESC LIMIT ?", (hotkey, limit)
        ).fetchall()
        return [{"block": block, "alpha": alpha, "at": at} for block, alpha, at in reversed(rows)]
