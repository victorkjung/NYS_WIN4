"""
Data loading, normalization, and preprocessing for WIN4 data.
Converts raw Socrata data into analysis-ready format.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter

from .config import config


def normalize_win4_data(raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalize raw Socrata data into long format (one row per draw).

    The source data has columns like:
    - draw_date
    - midday_win_4
    - evening_win_4

    We convert to:
    - draw_date (datetime)
    - draw_type (Midday/Evening)
    - win4 (zero-padded 4-digit string)

    Args:
        raw_data: Raw records from Socrata API

    Returns:
        Normalized DataFrame with one row per draw
    """
    if not raw_data:
        return pd.DataFrame(columns=["draw_date", "draw_type", "win4"])

    df = pd.DataFrame(raw_data)

    # Collect normalized rows
    rows = []

    for _, record in df.iterrows():
        draw_date = pd.to_datetime(record.get("draw_date"))

        # Process Midday draw
        midday = record.get("midday_win_4", record.get("midday_win4", ""))
        if midday and str(midday).strip():
            rows.append({
                "draw_date": draw_date,
                "draw_type": "Midday",
                "win4": normalize_combo(str(midday))
            })

        # Process Evening draw
        evening = record.get("evening_win_4", record.get("evening_win4", ""))
        if evening and str(evening).strip():
            rows.append({
                "draw_date": draw_date,
                "draw_type": "Evening",
                "win4": normalize_combo(str(evening))
            })

    result = pd.DataFrame(rows)

    if len(result) > 0:
        result = result.sort_values("draw_date", ascending=False).reset_index(drop=True)

    return result


def normalize_combo(combo: str) -> str:
    """
    Normalize a WIN4 combo to 4-digit zero-padded string.

    Args:
        combo: Raw combo value (could be int, float, or string)

    Returns:
        Zero-padded 4-digit string (e.g., "0042")
    """
    # Handle various input types
    try:
        # Remove any whitespace and convert to string
        combo_str = str(combo).strip()

        # Remove any decimal points (e.g., "123.0" -> "123")
        if "." in combo_str:
            combo_str = combo_str.split(".")[0]

        # Zero-pad to 4 digits
        combo_str = combo_str.zfill(4)

        # Validate: should be exactly 4 digits
        if len(combo_str) == 4 and combo_str.isdigit():
            return combo_str

        # If longer than 4, take last 4 digits
        if len(combo_str) > 4 and combo_str.isdigit():
            return combo_str[-4:]

        return "0000"  # Fallback for invalid data

    except (ValueError, TypeError):
        return "0000"


def filter_by_date_range(
    df: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Filter DataFrame by date range.

    Args:
        df: DataFrame with draw_date column
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered DataFrame
    """
    result = df.copy()

    if start_date is not None:
        result = result[result["draw_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        # Add one day to include the end date fully
        end_dt = pd.to_datetime(end_date) + timedelta(days=1)
        result = result[result["draw_date"] < end_dt]

    return result


def filter_by_draw_type(
    df: pd.DataFrame,
    draw_type: str = "Both"
) -> pd.DataFrame:
    """
    Filter DataFrame by draw type.

    Args:
        df: DataFrame with draw_type column
        draw_type: "Midday", "Evening", or "Both"

    Returns:
        Filtered DataFrame
    """
    if draw_type == "Both":
        return df

    return df[df["draw_type"] == draw_type].copy()


def get_date_range(df: pd.DataFrame) -> Tuple[datetime, datetime]:
    """
    Get min and max dates from DataFrame.

    Args:
        df: DataFrame with draw_date column

    Returns:
        Tuple of (min_date, max_date)
    """
    if len(df) == 0:
        today = datetime.now()
        return (today, today)

    return (df["draw_date"].min(), df["draw_date"].max())


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add commonly used derived columns to DataFrame.

    Adds:
    - digit_1, digit_2, digit_3, digit_4: Individual digits
    - digit_sum: Sum of all digits (0-36)
    - pattern_type: ABCD, AABC, AABB, AAAB, or AAAA
    - sorted_combo: Digits sorted (for box matching)
    - is_palindrome: True if reads same forwards/backwards
    - has_repeat: True if any digit repeats

    Args:
        df: DataFrame with win4 column

    Returns:
        DataFrame with additional columns
    """
    result = df.copy()

    # Individual digits
    for i in range(4):
        result[f"digit_{i+1}"] = result["win4"].str[i]

    # Digit sum
    result["digit_sum"] = result["win4"].apply(
        lambda x: sum(int(d) for d in x)
    )

    # Pattern type
    result["pattern_type"] = result["win4"].apply(get_pattern_type)

    # Sorted combo (for box matching)
    result["sorted_combo"] = result["win4"].apply(lambda x: "".join(sorted(x)))

    # Palindrome check
    result["is_palindrome"] = result["win4"].apply(lambda x: x == x[::-1])

    # Has repeat
    result["has_repeat"] = result["win4"].apply(lambda x: len(set(x)) < 4)

    return result


def get_pattern_type(combo: str) -> str:
    """
    Determine the pattern type of a combo.

    Pattern types:
    - ABCD: All unique digits (24-way box)
    - AABC: One pair (12-way box)
    - AABB: Two pairs (6-way box)
    - AAAB: Triple (4-way box)
    - AAAA: Quad (1-way, same as straight)

    Args:
        combo: 4-digit combo string

    Returns:
        Pattern type string
    """
    counts = sorted(Counter(combo).values(), reverse=True)

    if counts == [4]:
        return "AAAA"
    elif counts == [3, 1]:
        return "AAAB"
    elif counts == [2, 2]:
        return "AABB"
    elif counts == [2, 1, 1]:
        return "AABC"
    else:
        return "ABCD"


def get_box_permutation_count(combo: str) -> int:
    """
    Get the number of unique permutations for box play.

    Args:
        combo: 4-digit combo string

    Returns:
        Number of permutations (1, 4, 6, 12, or 24)
    """
    pattern = get_pattern_type(combo)
    perm_counts = {
        "AAAA": 1,
        "AAAB": 4,
        "AABB": 6,
        "AABC": 12,
        "ABCD": 24
    }
    return perm_counts.get(pattern, 24)


def calculate_date_preset(
    max_date: datetime,
    preset_days: Optional[int]
) -> datetime:
    """
    Calculate start date from a preset.

    Args:
        max_date: Maximum date in dataset
        preset_days: Number of days (None = all time)

    Returns:
        Calculated start date
    """
    if preset_days is None:
        # Return a very old date for "all time"
        return datetime(1990, 1, 1)

    return max_date - timedelta(days=preset_days)


def validate_combo(combo: str) -> Tuple[bool, str]:
    """
    Validate a user-entered combo.

    Args:
        combo: User input string

    Returns:
        Tuple of (is_valid, error_message or normalized_combo)
    """
    # Remove whitespace
    combo = combo.strip()

    # Check length
    if len(combo) != 4:
        return (False, "Combo must be exactly 4 digits")

    # Check all digits
    if not combo.isdigit():
        return (False, "Combo must contain only digits 0-9")

    return (True, combo)
