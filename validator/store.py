"""SQLite state for one validator: used tickets, accepted episodes, verdicts and pull cursors."""

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.dblock import locked

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets_used (
  hotkey TEXT NOT NULL, task_id TEXT NOT NULL, counter INTEGER NOT NULL,
  bundle_id TEXT NOT NULL, seen_at REAL NOT NULL,
  PRIMARY KEY (hotkey, task_id, counter)
);
CREATE TABLE IF NOT EXISTS accepted (
  bundle_id TEXT PRIMARY KEY, hotkey TEXT NOT NULL, task_id TEXT NOT NULL, epoch INTEGER NOT NULL,
  contributor TEXT NOT NULL, signature BLOB NOT NULL, leaf TEXT NOT NULL,
  time_score REAL NOT NULL, smooth_score REAL NOT NULL, duration_s REAL NOT NULL,
  value REAL NOT NULL, accepted_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS verdicts (
  bundle_id TEXT PRIMARY KEY, hotkey TEXT NOT NULL, verdict TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS cursors (hotkey TEXT PRIMARY KEY, cursor INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS epoch_roots (epoch INTEGER PRIMARY KEY, root TEXT NOT NULL, count INTEGER NOT NULL);
"""

RECENT_SIGNATURES = 500


@dataclass(frozen=True)
class AcceptedRow:
    bundle_id: str
    hotkey: str
    task_id: str
    epoch: int
    contributor: str
    leaf: str
    time_score: float
    smooth_score: float
    duration_s: float
    value: float


class Store:
    def __init__(self, path: str | Path) -> None:
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.RLock()
        self._db.executescript(SCHEMA)

    @locked
    def claim_ticket(self, hotkey: str, task_id: str, counter: int, bundle_id: str) -> bool:
        """Record first sight of a ticket; False when it was already seen."""
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO tickets_used VALUES (?,?,?,?,?)",
                    (hotkey, task_id, counter, bundle_id, time.time()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    @locked
    def recent_signatures(self, task_id: str) -> list[np.ndarray]:
        rows = self._db.execute(
            "SELECT signature FROM accepted WHERE task_id=? ORDER BY accepted_at DESC LIMIT ?",
            (task_id, RECENT_SIGNATURES),
        ).fetchall()
        return [np.frombuffer(row[0], dtype="<f8") for row in rows]

    @locked
    def add_accepted(self, row: AcceptedRow, signature: np.ndarray) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO accepted (bundle_id, hotkey, task_id, epoch, contributor, signature,"
                " leaf, time_score, smooth_score, duration_s, value, accepted_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (row.bundle_id, row.hotkey, row.task_id, row.epoch, row.contributor,
                 signature.astype("<f8").tobytes(), row.leaf, row.time_score, row.smooth_score,
                 row.duration_s, row.value, time.time()),
            )

    @locked
    def add_verdict(self, bundle_id: str, hotkey: str, verdict: dict) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO verdicts VALUES (?,?,?,?)",
                (bundle_id, hotkey, json.dumps(verdict), time.time()),
            )

    @locked
    def epoch_values(self) -> dict[int, dict[str, float]]:
        rows = self._db.execute("SELECT epoch, hotkey, SUM(value) FROM accepted GROUP BY epoch, hotkey")
        result: dict[int, dict[str, float]] = {}
        for epoch, hotkey, total in rows:
            result.setdefault(int(epoch), {})[hotkey] = float(total)
        return result

    @locked
    def leaves(self, epoch: int) -> list[str]:
        rows = self._db.execute("SELECT leaf FROM accepted WHERE epoch=?", (epoch,)).fetchall()
        return [row[0] for row in rows]

    @locked
    def contributor_totals(self) -> list[tuple[str, str, int, float]]:
        rows = self._db.execute(
            "SELECT contributor, hotkey, COUNT(*), SUM(value) FROM accepted "
            "GROUP BY contributor, hotkey ORDER BY SUM(value) DESC"
        ).fetchall()
        return [(r[0], r[1], int(r[2]), float(r[3])) for r in rows]

    @locked
    def get_cursor(self, hotkey: str) -> int:
        row = self._db.execute("SELECT cursor FROM cursors WHERE hotkey=?", (hotkey,)).fetchone()
        return int(row[0]) if row else 0

    @locked
    def set_cursor(self, hotkey: str, cursor: int) -> None:
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO cursors VALUES (?,?)", (hotkey, cursor))

    @locked
    def save_root(self, epoch: int, root: str, count: int) -> None:
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO epoch_roots VALUES (?,?,?)", (epoch, root, count))
