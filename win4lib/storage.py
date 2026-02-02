"""
Watchlist storage and persistence for WIN4 Analyzer.
Handles saving/loading watchlist using Streamlit session state
and optional file-based persistence.
"""
import streamlit as st
import json
import csv
import io
from typing import List, Set, Optional, Dict
from pathlib import Path


# File path for persistent storage (used when file persistence is enabled)
WATCHLIST_FILE = Path(".win4_watchlist.json")


def init_watchlist() -> Set[str]:
    """
    Initialize watchlist in session state.

    Returns:
        Current watchlist set
    """
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = set()
        # Try to load from file if exists
        loaded = load_watchlist_from_file()
        if loaded:
            st.session_state.watchlist = loaded

    return st.session_state.watchlist


def add_to_watchlist(combo: str) -> bool:
    """
    Add a combo to the watchlist.

    Args:
        combo: 4-digit combo string

    Returns:
        True if added, False if invalid or already exists
    """
    # Validate
    combo = combo.strip().zfill(4)
    if len(combo) != 4 or not combo.isdigit():
        return False

    if combo in st.session_state.watchlist:
        return False

    st.session_state.watchlist.add(combo)
    save_watchlist_to_file(st.session_state.watchlist)
    return True


def remove_from_watchlist(combo: str) -> bool:
    """
    Remove a combo from the watchlist.

    Args:
        combo: 4-digit combo string

    Returns:
        True if removed, False if not in watchlist
    """
    if combo not in st.session_state.watchlist:
        return False

    st.session_state.watchlist.discard(combo)
    save_watchlist_to_file(st.session_state.watchlist)
    return True


def clear_watchlist():
    """Clear all combos from watchlist."""
    st.session_state.watchlist = set()
    save_watchlist_to_file(st.session_state.watchlist)


def get_watchlist() -> List[str]:
    """
    Get sorted list of watchlist combos.

    Returns:
        Sorted list of combo strings
    """
    return sorted(st.session_state.get("watchlist", set()))


def get_watchlist_count() -> int:
    """Get number of combos in watchlist."""
    return len(st.session_state.get("watchlist", set()))


def is_in_watchlist(combo: str) -> bool:
    """Check if combo is in watchlist."""
    return combo in st.session_state.get("watchlist", set())


def bulk_add_to_watchlist(combos: List[str]) -> int:
    """
    Add multiple combos to watchlist.

    Args:
        combos: List of combo strings

    Returns:
        Number of combos successfully added
    """
    count = 0
    for combo in combos:
        if add_to_watchlist(combo):
            count += 1
    return count


# === File-based persistence ===

def save_watchlist_to_file(watchlist: Set[str]):
    """
    Save watchlist to JSON file.

    Args:
        watchlist: Set of combo strings
    """
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(list(watchlist), f)
    except Exception:
        pass  # Silently fail - file persistence is optional


def load_watchlist_from_file() -> Optional[Set[str]]:
    """
    Load watchlist from JSON file.

    Returns:
        Set of combo strings, or None if file doesn't exist
    """
    try:
        if WATCHLIST_FILE.exists():
            with open(WATCHLIST_FILE) as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
    except Exception:
        pass
    return None


# === CSV Export/Import ===

def export_watchlist_csv() -> str:
    """
    Export watchlist as CSV string.

    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["win4"])
    for combo in get_watchlist():
        writer.writerow([combo])
    return output.getvalue()


def import_watchlist_csv(csv_content: str) -> Dict[str, int]:
    """
    Import combos from CSV content.

    Expected format: CSV with 'win4' column header.

    Args:
        csv_content: CSV file content as string

    Returns:
        Dict with 'added', 'skipped', 'invalid' counts
    """
    results = {"added": 0, "skipped": 0, "invalid": 0}

    try:
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            # Try common column names
            combo = (
                row.get("win4") or
                row.get("WIN4") or
                row.get("combo") or
                row.get("Combo") or
                row.get("number") or
                list(row.values())[0] if row else None
            )

            if combo:
                combo = str(combo).strip().zfill(4)
                if len(combo) == 4 and combo.isdigit():
                    if add_to_watchlist(combo):
                        results["added"] += 1
                    else:
                        results["skipped"] += 1
                else:
                    results["invalid"] += 1
            else:
                results["invalid"] += 1

    except Exception as e:
        st.error(f"Error importing CSV: {e}")

    return results


# === Watchlist Statistics ===

def get_watchlist_stats(df, watchlist: List[str]) -> List[Dict]:
    """
    Calculate statistics for watchlist combos against historical data.

    Args:
        df: DataFrame with win4 and draw_date columns
        watchlist: List of combo strings

    Returns:
        List of dicts with combo stats
    """
    from .data import get_pattern_type, get_box_permutation_count

    stats = []

    for combo in watchlist:
        # Straight matches
        straight_matches = df[df["win4"] == combo]
        straight_count = len(straight_matches)

        # Box matches
        sorted_combo = "".join(sorted(combo))
        box_matches = df[df["win4"].apply(lambda x: "".join(sorted(x))) == sorted_combo]
        box_count = len(box_matches)

        # Last seen
        if straight_count > 0:
            last_seen = straight_matches["draw_date"].max()
            days_ago = (df["draw_date"].max() - last_seen).days
        else:
            last_seen = None
            days_ago = None

        # Pattern info
        pattern = get_pattern_type(combo)
        box_ways = get_box_permutation_count(combo)

        stats.append({
            "combo": combo,
            "straight_hits": straight_count,
            "box_hits": box_count,
            "last_seen": last_seen,
            "days_ago": days_ago,
            "pattern": pattern,
            "box_ways": box_ways
        })

    return stats
