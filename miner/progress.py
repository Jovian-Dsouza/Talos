"""Player progress for the game layer: XP, level, streaks, daily goal, personal bests and badges.

Computed on the server from the validators' verdicts, so a browser cannot award itself anything.
XP per verified run = XP_BASE + round(XP_PER_SCORE * score); rejected and unjudged runs earn nothing.
"""

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

XP_BASE = 50
XP_PER_SCORE = 100
DAILY_GOAL = 3
HISTORY_RUNS = 30
LEVELS = (  # (total XP needed, title)
    (0, "Trainee"), (150, "Operator"), (400, "Technician"), (800, "Engineer"), (1400, "Specialist"),
    (2200, "Roboticist"), (3200, "Lead roboticist"), (4500, "Master"), (6000, "Grandmaster"), (8000, "Legend"),
)
SMOOTH_BADGE = 0.9
SPEED_BADGE = 0.95
VOLUME_BADGE = 10
STREAK_BADGE = 3
PODIUM = 3


def run_xp(score: float) -> int:
    return XP_BASE + round(XP_PER_SCORE * score)


def _day(epoch: float) -> date:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date()


def _streaks(days: set[date], today: date) -> tuple[int, int]:
    """(current, longest) runs of consecutive UTC days. The current streak survives until a full day is missed."""
    longest = run = 0
    previous: date | None = None
    for day in sorted(days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest, previous = max(longest, run), day
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current, cursor = current + 1, cursor - timedelta(days=1)
    return current, longest


def _level(xp: int) -> dict[str, Any]:
    index = max(i for i, (need, _) in enumerate(LEVELS) if xp >= need)
    floor, title = LEVELS[index]
    ceiling = LEVELS[index + 1][0] if index + 1 < len(LEVELS) else None
    return {"level": index + 1, "title": title, "level_xp": floor, "next_xp": ceiling}


def _bests(accepted: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    bests: dict[str, dict[str, float]] = {}
    for run in accepted:
        verdict = run["verdict"]
        best = bests.setdefault(run["task_id"], {"score": 0.0, "duration_s": float("inf")})
        best["score"] = max(best["score"], float(verdict.get("score", 0.0)))
        best["duration_s"] = min(best["duration_s"], float(verdict.get("duration_s", 0.0)))
    return bests


def _badges(accepted: list[dict[str, Any]], task_ids: Iterable[str], rank: int | None,
            longest_streak: int) -> list[dict[str, Any]]:
    scores = [run["verdict"] for run in accepted]
    done_tasks = {run["task_id"] for run in accepted}
    earned = {
        "first": bool(accepted),
        "smooth": any(v.get("smooth_score", 0.0) >= SMOOTH_BADGE for v in scores),
        "speed": any(v.get("time_score", 0.0) >= SPEED_BADGE for v in scores),
        "volume": len(accepted) >= VOLUME_BADGE,
        "all_tasks": set(task_ids) <= done_tasks,
        "podium": rank is not None and rank <= PODIUM,
        "streak": longest_streak >= STREAK_BADGE,
    }
    titles = {
        "first": ("First demo", "Get one run verified"),
        "smooth": ("Steady hands", f"Smoothness of {SMOOTH_BADGE:.0%} or more"),
        "speed": ("Speedrunner", f"Time score of {SPEED_BADGE:.0%} or more"),
        "volume": ("Ten verified", f"{VOLUME_BADGE} verified runs"),
        "all_tasks": ("All-rounder", "A verified run on every task"),
        "podium": ("Podium", f"Reach the top {PODIUM} on the leaderboard"),
        "streak": ("On a roll", f"Verified runs {STREAK_BADGE} days in a row"),
    }
    return [{"id": key, "title": titles[key][0], "detail": titles[key][1], "earned": value}
            for key, value in earned.items()]


def progress(runs: list[dict[str, Any]], task_ids: Iterable[str], rank: int | None, players: int,
             now: float | None = None) -> dict[str, Any]:
    """`runs` are the player's jobs newest first, each with its first verdict or None."""
    now = time.time() if now is None else now
    task_ids = tuple(task_ids)
    judged = [run for run in runs if run["verdict"] is not None]
    accepted = [run for run in judged if run["verdict"].get("accepted")]
    xp = sum(run_xp(float(run["verdict"].get("score", 0.0))) for run in accepted)
    days = {_day(run["received_at"]) for run in accepted}
    today = _day(now)
    current, longest = _streaks(days, today)
    bests = _bests(accepted)
    return {
        "xp": xp, **_level(xp),
        "streak_days": current, "longest_streak": longest,
        "daily": {"done": sum(1 for run in accepted if _day(run["received_at"]) == today), "goal": DAILY_GOAL},
        "runs": len(runs), "verified": len(accepted), "rejected": len(judged) - len(accepted),
        "rank": rank, "players": players,
        "bests": [{"task_id": task_id, **best} for task_id, best in bests.items()],
        "badges": _badges(accepted, task_ids, rank, longest),
        "history": [
            {"at": run["received_at"], "task_id": run["task_id"], "accepted": bool(run["verdict"].get("accepted")),
             "score": float(run["verdict"].get("score", 0.0)), "time_score": float(run["verdict"].get("time_score", 0.0)),
             "smooth_score": float(run["verdict"].get("smooth_score", 0.0)), "reason": run["verdict"].get("reason", ""),
             "xp": run_xp(float(run["verdict"].get("score", 0.0))) if run["verdict"].get("accepted") else 0}
            for run in reversed(judged[:HISTORY_RUNS])
        ],
    }
