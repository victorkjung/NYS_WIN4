from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


@dataclass(frozen=True)
class SocrataConfig:
    domain: str
    dataset_id: str
    app_token: Optional[str] = None
    timeout_s: int = 30


class SocrataError(RuntimeError):
    pass


def _headers(app_token: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if app_token:
        h["X-App-Token"] = app_token
    return h


def fetch_all_rows(
    *,
    config: SocrataConfig,
    select: str,
    where: Optional[str] = None,
    order: Optional[str] = None,
    chunk_size: int = 50000,
    max_rows: Optional[int] = None,
    sleep_s: float = 0.05,
) -> List[Dict]:
    """
    Chunked Socrata fetch via $limit/$offset with light retries.
    """
    base = f"https://{config.domain}/resource/{config.dataset_id}.json"
    out: List[Dict] = []
    offset = 0

    while True:
        params = {"$select": select, "$limit": chunk_size, "$offset": offset}
        if where:
            params["$where"] = where
        if order:
            params["$order"] = order

        tries = 0
        while True:
            tries += 1
            resp = requests.get(base, headers=_headers(config.app_token), params=params, timeout=config.timeout_s)

            if resp.status_code == 200:
                break

            if resp.status_code in (429, 500, 502, 503, 504) and tries <= 5:
                backoff = min(2 ** tries, 20)
                time.sleep(backoff)
                continue

            raise SocrataError(f"Socrata request failed: {resp.status_code} - {resp.text[:500]}")

        rows = resp.json()
        if not rows:
            break

        out.extend(rows)
        offset += chunk_size

        if max_rows is not None and len(out) >= max_rows:
            out = out[:max_rows]
            break

        time.sleep(sleep_s)

    return out
