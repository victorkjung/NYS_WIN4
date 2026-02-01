from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

import pandas as pd
import requests
import streamlit as st

from .socrata_client import SocrataConfig, fetch_all_rows


def _get_app_token() -> Optional[str]:
    try:
        tok = st.secrets.get("SOCRATA_APP_TOKEN")
        if tok:
            return str(tok)
    except Exception:
        pass
    return os.getenv("SOCRATA_APP_TOKEN")


@st.cache_data(ttl=60 * 60, show_spinner=False)  # 1 hour
def get_dataset_metadata(domain: str, dataset_id: str) -> Dict[str, Any]:
    """
    Socrata dataset metadata endpoint:
      https://{domain}/api/views/{dataset_id}.json
    Includes timestamps: dataUpdatedAt, rowsUpdatedAt (epoch seconds).
    """
    url = f"https://{domain}/api/views/{dataset_id}.json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _to_dt_utc(epoch_seconds: Optional[int]) -> Optional[datetime]:
    if epoch_seconds is None:
        return None
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc)


def get_freshness_info(domain: str, dataset_id: str) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    """
    Returns:
      (data_updated_at_utc, rows_updated_at_utc, label)
    """
    try:
        meta = get_dataset_metadata(domain, dataset_id)
        data_updated = _to_dt_utc(meta.get("dataUpdatedAt"))
        rows_updated = _to_dt_utc(meta.get("rowsUpdatedAt"))
        title = meta.get("name")
        label = f"{title}" if title else None
        return data_updated, rows_updated, label
    except Exception:
        return None, None, None


def format_freshness_badge(data_updated: Optional[datetime], rows_updated: Optional[datetime]) -> str:
    """
    Returns small HTML badge string.
    Use with st.markdown(..., unsafe_allow_html=True).
    """
    def fmt(dt: Optional[datetime]) -> str:
        if not dt:
            return "unknown"
        return dt.strftime("%Y-%m-%d %H:%M UTC")

    best = data_updated or rows_updated
    ts = fmt(best)

    # simple color coding
    bg = "#334155" if best is None else "#1d4ed8"
    return f"""
    <span style="
        display:inline-block;
        padding:0.25rem 0.55rem;
        border-radius:999px;
        background:{bg};
        color:white;
        font-size:0.80rem;
        line-height:1;
        font-weight:600;
    ">
      Freshness: {ts}
    </span>
    """


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)  # 6 hours
def load_win4_long(domain: str, dataset_id: str) -> pd.DataFrame:
    """
    Load and normalize Win 4 into long format:
      draw_date (datetime64), draw_type (Midday/Evening), win4 (zero-padded "0000"-"9999"), booster (string)
    """
    cfg = SocrataConfig(domain=domain, dataset_id=dataset_id, app_token=_get_app_token())

    # Pull only what we need.
    select = "draw_date,midday_win_4,evening_win_4,midday_win_4_booster,evening_win_4_booster"
    rows = fetch_all_rows(
        config=cfg,
        select=select,
        order="draw_date ASC",
        chunk_size=50000,
    )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["draw_date", "draw_type", "win4", "booster"])

    df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce")

    # Midday normalization
    mid = df[["draw_date", "midday_win_4", "midday_win_4_booster"]].copy()
    mid.columns = ["draw_date", "win4_raw", "booster"]
    mid["draw_type"] = "Midday"

    # Evening normalization
    eve = df[["draw_date", "evening_win_4", "evening_win_4_booster"]].copy()
    eve.columns = ["draw_date", "win4_raw", "booster"]
    eve["draw_type"] = "Evening"

    out = pd.concat([mid, eve], ignore_index=True)

    # Clean + zero-pad
    out["win4_raw"] = out["win4_raw"].astype("string")
    out["win4"] = (
        out["win4_raw"]
        .str.replace(r"\D+", "", regex=True)
        .str.zfill(4)
    )
    out = out[out["win4"].str.fullmatch(r"\d{4}", na=False)]
    out = out.drop(columns=["win4_raw"])

    out["booster"] = out["booster"].astype("string")
    out = out.sort_values(["draw_date", "draw_type"], ascending=[True, True]).reset_index(drop=True)
    return out


def get_last_updated_hint(df_long: pd.DataFrame) -> str:
    if df_long.empty:
        return "Dataset loaded (no rows)."
    dmin = df_long["draw_date"].min()
    dmax = df_long["draw_date"].max()
    return f"Loaded {len(df_long):,} draws from {dmin.date().isoformat()} → {dmax.date().isoformat()}."
