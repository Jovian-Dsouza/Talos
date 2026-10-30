"""Public read models over the job log: live activity, per-task datasets and the episode browser.

A job is one submitted run. Its stage is "queued" until a validator judges it, then "accepted" or
"rejected" by that first verdict. Every function here is pure over rows the caller already loaded.
"""

import time
from collections import Counter
from typing import Any, Iterable

WINDOWS = {"1h": (3600, 300), "24h": (86400, 3600)}  # name -> (span, bucket) in seconds
PLAYING_SECONDS = 300  # a ticket issued this recently and not yet submitted means someone is playing
VALIDATING_SECONDS = 600  # a validator that judged a run this recently is validating now
ACTIVE_MINER_SECONDS = 86400
FEED_JOBS = 30
DATASET_DAYS = 14
DAY = 86400
# What export/lerobot_export.py writes; kept here so the hosted image does not need lerobot.
DATASET_FORMAT = {"format": "LeRobot v0.6.1", "robot": "SO-101", "fps": 50, "cameras": ["front", "wrist"]}


def stage(job: dict[str, Any]) -> str:
    verdict = job["verdict"]
    if verdict is None:
        return "queued"
    return "accepted" if verdict.get("accepted") else "rejected"


def reason_label(reason: str) -> str:
    """Group reasons that carry details ("malformed upload: ...") under one label."""
    return reason.split(":", 1)[0].strip() or "unknown"


def job_view(job: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    verdict = job["verdict"] or {}
    return {
        "id": job["seq"], "bundle_id": job["bundle_id"], "hotkey": job["hotkey"],
        "contributor": names.get(job["hotkey"], job["contributor"]), "task_id": job["task_id"],
        "stage": stage(job), "received_at": job["received_at"], "judged_at": job["judged_at"],
        "validator": job["validator"], "reason": verdict.get("reason", ""),
        "score": verdict.get("score", 0.0), "time_score": verdict.get("time_score", 0.0),
        "smooth_score": verdict.get("smooth_score", 0.0), "duration_s": verdict.get("duration_s", 0.0),
    }


def _timeline(jobs: Iterable[dict[str, Any]], span: int, bucket: int, now: float) -> list[dict[str, Any]]:
    start = now - span
    buckets = [{"start": start + i * bucket, "accepted": 0, "rejected": 0, "queued": 0} for i in range(span // bucket)]
    for job in jobs:
        index = int((job["received_at"] - start) // bucket)
        if 0 <= index < len(buckets):
            buckets[index][stage(job)] += 1
    return buckets


def activity(jobs: list[dict[str, Any]], names: dict[str, str], *, miners_registered: int,
             validators_on_chain: int, playing_now: int, validating_now: int, window: str,
             now: float | None = None) -> dict[str, Any]:
    """Everything the Live page draws, from all jobs (newest first)."""
    now = time.time() if now is None else now
    span, bucket = WINDOWS[window]
    stages = Counter(stage(job) for job in jobs)
    accepted = [job for job in jobs if stage(job) == "accepted"]
    reasons = Counter(reason_label(job["verdict"].get("reason", "")) for job in jobs if stage(job) == "rejected")
    tasks: dict[str, Counter] = {}
    for job in jobs:
        tasks.setdefault(job["task_id"] or "unknown", Counter())[stage(job)] += 1
    return {
        "window": window,
        "summary": {
            "miners_registered": miners_registered,
            "miners_active": len({job["hotkey"] for job in jobs if job["received_at"] >= now - ACTIVE_MINER_SECONDS}),
            "playing_now": playing_now,
            "validators_on_chain": validators_on_chain,
            "validating_now": validating_now,
            "runs": len(jobs),
            "episodes": len(accepted),
            "demo_seconds": sum(float(job["verdict"].get("duration_s", 0.0)) for job in accepted),
        },
        "pipeline": {"playing": playing_now, "queued": stages["queued"], "accepted": stages["accepted"],
                     "rejected": stages["rejected"]},
        "reasons": [{"reason": reason, "count": count} for reason, count in reasons.most_common()],
        "tasks": [{"task_id": task_id, "accepted": c["accepted"], "rejected": c["rejected"], "queued": c["queued"]}
                  for task_id, c in sorted(tasks.items())],
        "timeline": {"bucket_seconds": bucket, "buckets": _timeline(jobs, span, bucket, now)},
        "jobs": [job_view(job, names) for job in jobs[:FEED_JOBS]],
        "at": now,
    }


def _dataset(task_id: str, jobs: list[dict[str, Any]], link: str, now: float) -> dict[str, Any]:
    accepted = [job for job in jobs if stage(job) == "accepted"]
    scores = [float(job["verdict"].get("score", 0.0)) for job in accepted]
    today = int(now // DAY)
    per_day = Counter(int(job["received_at"] // DAY) for job in accepted)
    return {
        "task_id": task_id,
        "episodes": len(accepted),
        "rejected": sum(1 for job in jobs if stage(job) == "rejected"),
        "queued": sum(1 for job in jobs if stage(job) == "queued"),
        "seconds": sum(float(job["verdict"].get("duration_s", 0.0)) for job in accepted),
        "contributors": len({job["hotkey"] for job in accepted}),
        "average_score": sum(scores) / len(scores) if scores else 0.0,
        "best_score": max(scores, default=0.0),
        "updated_at": max((job["received_at"] for job in accepted), default=None),
        "per_day": [{"day": (today - i) * DAY, "episodes": per_day.get(today - i, 0)}
                    for i in reversed(range(DATASET_DAYS))],
        "link": link,
    }


def datasets(jobs: list[dict[str, Any]], task_ids: Iterable[str], links: dict[str, str],
             now: float | None = None) -> dict[str, Any]:
    """One dataset per task: the accepted runs a LeRobot export of that task would contain."""
    now = time.time() if now is None else now
    by_task: dict[str, list[dict[str, Any]]] = {task_id: [] for task_id in task_ids}
    for job in jobs:
        by_task.setdefault(job["task_id"] or "unknown", []).append(job)
    return {
        **DATASET_FORMAT,
        "datasets": [_dataset(task_id, rows, links.get(task_id, ""), now) for task_id, rows in by_task.items()],
    }
