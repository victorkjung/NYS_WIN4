from __future__ import annotations

from collections import Counter
from math import factorial
from typing import Tuple

import numpy as np
import pandas as pd


def add_digit_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds: d1..d4 ints, digit_sum int
    """
    if df.empty:
        return df.assign(
            d1=pd.Series(dtype="int"), d2=pd.Series(dtype="int"),
            d3=pd.Series(dtype="int"), d4=pd.Series(dtype="int"),
            digit_sum=pd.Series(dtype="int"),
        )

    s = df["win4"].astype("string")
    digits = s.str.extract(r"(\d)(\d)(\d)(\d)")
    digits.columns = ["d1", "d2", "d3", "d4"]
    for c in ["d1", "d2", "d3", "d4"]:
        digits[c] = digits[c].astype(int)

    out = df.copy()
    out[["d1", "d2", "d3", "d4"]] = digits[["d1", "d2", "d3", "d4"]]
    out["digit_sum"] = out[["d1", "d2", "d3", "d4"]].sum(axis=1).astype(int)
    return out


def digit_position_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns index=position(1..4), columns=digit(0..9), values=count
    """
    if df.empty:
        return pd.DataFrame(index=[1, 2, 3, 4], columns=list(range(10))).fillna(0).astype(int)

    freq = {}
    for i, col in enumerate(["d1", "d2", "d3", "d4"], start=1):
        counts = df[col].value_counts().reindex(range(10), fill_value=0).sort_index()
        freq[i] = counts.values

    out = pd.DataFrame.from_dict(freq, orient="index", columns=list(range(10)))
    out.index.name = "position"
    return out


def combo_frequency(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["win4", "count"])
    vc = df["win4"].value_counts().reset_index()
    vc.columns = ["win4", "count"]
    return vc


def hot_cold_scores(df: pd.DataFrame, window_days: int = 60) -> pd.DataFrame:
    """
    Score = count_recent - expected_recent (based on prior rate)
    If no prior exists, score = count_recent
    """
    if df.empty:
        return pd.DataFrame(columns=["win4", "count_recent", "count_prior", "score"])

    dmax = df["draw_date"].max()
    cutoff = dmax - pd.Timedelta(days=window_days)

    recent = df[df["draw_date"] > cutoff]
    prior = df[df["draw_date"] <= cutoff]

    recent_counts = recent["win4"].value_counts()
    prior_counts = prior["win4"].value_counts()

    all_keys = recent_counts.index.union(prior_counts.index)

    out = pd.DataFrame({"win4": all_keys})
    out["count_recent"] = out["win4"].map(recent_counts).fillna(0).astype(int)
    out["count_prior"] = out["win4"].map(prior_counts).fillna(0).astype(int)

    if len(prior) > 0:
        prior_rate = out["count_prior"] / max(len(prior), 1)
        expected_recent = prior_rate * max(len(recent), 1)
        out["score"] = (out["count_recent"] - expected_recent).astype(float)
    else:
        out["score"] = out["count_recent"].astype(float)

    return out.sort_values("score", ascending=False).reset_index(drop=True)


def strategy_backtest_hit_rate(df: pd.DataFrame, window_days: int = 60) -> pd.DataFrame:
    """
    Predict the next draw using the most frequent combo in the prior rolling window.
    Then compute hit and expanding mean hit rate.
    """
    if df.empty:
        return pd.DataFrame(columns=["draw_date", "hit", "hit_rate"])

    d = df.sort_values("draw_date").copy()
    hits = []

    for i in range(len(d)):
        t = d.iloc[i]["draw_date"]
        start = t - pd.Timedelta(days=window_days)
        hist = d[(d["draw_date"] < t) & (d["draw_date"] >= start)]
        if hist.empty:
            hits.append(np.nan)
            continue
        pred = hist["win4"].value_counts().idxmax()
        hits.append(1.0 if pred == d.iloc[i]["win4"] else 0.0)

    d["hit"] = hits
    d["hit_rate"] = d["hit"].expanding(min_periods=10).mean()
    return d[["draw_date", "hit", "hit_rate"]].dropna(subset=["hit_rate"]).reset_index(drop=True)


# ---------------------------
# Patterns Explorer
# ---------------------------

def add_pattern_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds pattern flags:
      - has_pair, has_triple, has_quad, is_two_pairs
      - is_mirror_ends (d1==d4), is_mirror_middle (d2==d3), is_palindrome (ABBA)
      - is_all_unique
      - pattern_label
    """
    if df.empty:
        cols_bool = [
            "is_all_unique", "has_pair", "has_triple", "has_quad", "is_two_pairs",
            "is_palindrome", "is_mirror_ends", "is_mirror_middle",
        ]
        out = df.copy()
        for c in cols_bool:
            out[c] = pd.Series(dtype="bool")
        out["pattern_label"] = pd.Series(dtype="string")
        return out

    out = df.copy()

    digits = out[["d1", "d2", "d3", "d4"]].to_numpy()
    sd = np.sort(digits, axis=1)

    eq1 = (sd[:, 0] == sd[:, 1]).astype(int)
    eq2 = (sd[:, 1] == sd[:, 2]).astype(int)
    eq3 = (sd[:, 2] == sd[:, 3]).astype(int)

    out["has_quad"] = (eq1 & eq2 & eq3).astype(bool)
    out["has_triple"] = (((sd[:, 0] == sd[:, 2]) | (sd[:, 1] == sd[:, 3])) & (~out["has_quad"].to_numpy()))
    out["has_pair"] = ((eq1 + eq2 + eq3) >= 1)

    out["is_two_pairs"] = ((sd[:, 0] == sd[:, 1]) & (sd[:, 2] == sd[:, 3]) & (sd[:, 1] != sd[:, 2]))
    out["is_all_unique"] = ~(out["has_pair"])

    out["is_mirror_ends"] = (out["d1"] == out["d4"])
    out["is_mirror_middle"] = (out["d2"] == out["d3"])
    out["is_palindrome"] = out["is_mirror_ends"] & out["is_mirror_middle"]

    def label_row(r) -> str:
        if bool(r["has_quad"]):
            return "Quad (AAAA)"
        if bool(r["has_triple"]):
            return "Triple (AAAB)"
        if bool(r["is_two_pairs"]):
            return "Two Pairs (AABB)"
        if bool(r["has_pair"]):
            return "One Pair (AABC)"
        return "All Unique (ABCD)"

    out["pattern_label"] = out.apply(label_row, axis=1).astype("string")
    return out


def pattern_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "pattern_label" not in df.columns:
        return pd.DataFrame(columns=["pattern_label", "count", "share"])

    vc = df["pattern_label"].value_counts().reset_index()
    vc.columns = ["pattern_label", "count"]
    vc["share"] = vc["count"] / vc["count"].sum()
    return vc


def pair_position_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    ✅ FIXED: Always returns a tidy dataframe with:
      index = pair label (e.g., "1-2")
      column = "count"
    This prevents shape surprises and fixes the Streamlit crash.
    """
    idx = ["1-2", "1-3", "1-4", "2-3", "2-4", "3-4"]
    if df.empty:
        return pd.DataFrame({"count": [0] * len(idx)}, index=idx)

    # Ensure digits exist
    if not all(c in df.columns for c in ["d1", "d2", "d3", "d4"]):
        return pd.DataFrame({"count": [0] * len(idx)}, index=idx)

    d = df[["d1", "d2", "d3", "d4"]]

    pairs = {
        "1-2": int((d["d1"] == d["d2"]).sum()),
        "1-3": int((d["d1"] == d["d3"]).sum()),
        "1-4": int((d["d1"] == d["d4"]).sum()),
        "2-3": int((d["d2"] == d["d3"]).sum()),
        "2-4": int((d["d2"] == d["d4"]).sum()),
        "3-4": int((d["d3"] == d["d4"]).sum()),
    }

    return pd.Series(pairs, name="count").reindex(idx).to_frame()


# ---------------------------
# Box matching support
# ---------------------------

def add_sorted_signature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds `sig_sorted` for Box matching (multiset equality).
    Uses digit columns if present for speed; otherwise falls back to string sorting.
    """
    out = df.copy()
    if df.empty:
        out["sig_sorted"] = pd.Series(dtype="string")
        return out

    if all(c in out.columns for c in ["d1", "d2", "d3", "d4"]):
        digits = out[["d1", "d2", "d3", "d4"]].to_numpy()
        sd = np.sort(digits, axis=1).astype(int)
        out["sig_sorted"] = pd.Series(["".join(map(str, row)) for row in sd], index=out.index, dtype="string")
        return out

    out["sig_sorted"] = out["win4"].astype("string").apply(lambda s: "".join(sorted(s))).astype("string")
    return out


def box_type_for_number(win4: str) -> Tuple[str, int, str]:
    """
    Returns: (box_label, distinct_permutations, sorted_signature)

    24-way: ABCD
    12-way: AABC
    6-way : AABB
    4-way : AAAB
    1-way : AAAA
    """
    s = str(win4).strip()
    if not (s.isdigit() and len(s) == 4):
        s = "".join(ch for ch in s if ch.isdigit()).zfill(4)[:4]

    sig = "".join(sorted(s))
    counts = Counter(sig)

    denom = 1
    for c in counts.values():
        denom *= factorial(c)

    ways = factorial(4) // denom

    if ways == 24:
        label = "24-way"
    elif ways == 12:
        label = "12-way"
    elif ways == 6:
        label = "6-way"
    elif ways == 4:
        label = "4-way"
    elif ways == 1:
        label = "1-way"
    else:
        label = f"{ways}-way"

    return label, int(ways), sig


# ---------------------------
# Watchlist helpers
# ---------------------------

def watchlist_stats(df: pd.DataFrame, watchlist: list[str], window_days: int = 60) -> pd.DataFrame:
    if df.empty or not watchlist:
        return pd.DataFrame(columns=["win4", "overall_count", "recent_count", "recent_share"])

    dmax = df["draw_date"].max()
    cutoff = dmax - pd.Timedelta(days=window_days)
    recent = df[df["draw_date"] > cutoff]

    overall = df["win4"].value_counts()
    recent_counts = recent["win4"].value_counts()

    rows = []
    for w in watchlist:
        oc = int(overall.get(w, 0))
        rc = int(recent_counts.get(w, 0))
        share = (rc / max(len(recent), 1)) if len(recent) else 0.0
        rows.append((w, oc, rc, share))

    out = pd.DataFrame(rows, columns=["win4", "overall_count", "recent_count", "recent_share"])
    return out.sort_values(["recent_count", "overall_count"], ascending=False).reset_index(drop=True)
