"""Signed HTTP exchange with miners: pull recordings, push verdicts."""

import json
from typing import Any

import httpx
from bittensor import http_auth

TIMEOUT = httpx.Timeout(20.0)


def _signed_headers(wallet, method: str, path: str, body: bytes, miner_hotkey: str) -> dict[str, str]:
    return http_auth.sign(wallet, method=method, path=path, body=body, receiver_ss58=miner_hotkey)


def fetch_bundles(wallet, base_url: str, miner_hotkey: str, since: int) -> list[dict[str, Any]]:
    path = f"/trajectories?since={since}"
    headers = _signed_headers(wallet, "GET", path, b"", miner_hotkey)
    response = httpx.get(base_url + path, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["bundles"]


def push_verdicts(wallet, base_url: str, miner_hotkey: str, items: list[dict[str, Any]]) -> None:
    body = json.dumps({"verdicts": items}).encode()
    headers = {**_signed_headers(wallet, "POST", "/verdicts", body, miner_hotkey),
               "Content-Type": "application/json"}
    response = httpx.post(base_url + "/verdicts", content=body, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
