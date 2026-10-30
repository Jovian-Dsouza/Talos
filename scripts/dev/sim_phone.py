"""Dev tool: act like phones. Fetch a ticket, solve it with the scripted policy, submit, poll the verdict.

Each simulated phone signs in as its own dev player (the server needs AUTH_DEV_LOGIN=1), so every
one gets its own custodial wallet and registered miner.

Usage: [TASK=put_cube_in_bowl] python scripts/dev/sim_phone.py BASE_URL [COUNT] [CONCURRENCY] [NAME]
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from common.schema import Ticket
from scripts.dev.scripted_demo import build_payload

TASK = os.environ.get("TASK", "put_cube_in_bowl")  # the scripted solver is tuned for this task
POLL_SECONDS = 1.0
POLL_LIMIT_SECONDS = 120.0


def run_one(base_url: str, name: str) -> dict:
    started = time.monotonic()
    headers = {"Authorization": f"Bearer dev:{name}"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        ticket = Ticket.from_dict(client.get(f"{base_url}/ticket", params={"task": TASK}).json())
        payload = build_payload(ticket, name)
        response = client.post(f"{base_url}/submit", json=payload)
        if response.status_code != 200:
            return {"name": name, "error": f"{response.status_code} {response.text[:120]}"}
        bundle_id = response.json()["bundle_id"]
        while time.monotonic() - started < POLL_LIMIT_SECONDS:
            status = client.get(f"{base_url}/status/{bundle_id}").json()
            if status["verdicts"]:
                verdict = next(iter(status["verdicts"].values()))
                return {"name": name, "seconds": round(time.monotonic() - started, 1), **verdict}
            time.sleep(POLL_SECONDS)
    return {"name": name, "error": "timed out waiting for a verdict"}


def main() -> None:
    base_url = sys.argv[1].rstrip("/")
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    prefix = sys.argv[4] if len(sys.argv) > 4 else "phone"
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda i: run_one(base_url, f"{prefix}-{i}"), range(count)))
    for result in results:
        print(result)
    ok = sum(1 for r in results if r.get("accepted"))
    print(f"accepted {ok}/{count}")


if __name__ == "__main__":
    main()
