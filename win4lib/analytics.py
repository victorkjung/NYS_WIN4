"""
Analytics functions for WIN4 data analysis.
Includes frequency analysis, hot/cold tracking, and pattern detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime, timedelta

from .config import config


def get_digit_frequency(df: pd.DataFrame, position: int) -> pd.Series:
    """
    Get frequency distribution of digits at a specific position.

    Args:
        df: DataFrame with win4 column
        position: Position (1-4)

    Returns:
        Series with digit counts, indexed 0-9
    """
    digits = df["win4"].str[position - 1]
    freq = digits.value_counts()
    # Ensure all digits 0-9 are present
    freq = freq.reindex(config.ui.digits, fill_value=0)
    return freq.sort_index()


def get_digit_frequency_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get frequency matrix of all digits at all positions.

    Returns:
        DataFrame with positions as columns, digits as rows
    """
    matrix = {}
    for pos in range(1, 5):
        matrix[f"Pos {pos}"] = get_digit_frequency(df, pos)

    return pd.DataFrame(matrix)


def get_combo_frequency(
    df: pd.DataFrame,
    top_n: Optional[int] = None
) -> pd.DataFrame:
    """
    Get frequency of each combo.

    Args:
        df: DataFrame with win4 column
        top_n: Limit to top N combos (None = all)

    Returns:
        DataFrame with combo, count, and percentage
    """
    freq = df["win4"].value_counts()

    if top_n:
        freq = freq.head(top_n)

    result = pd.DataFrame({
        "combo": freq.index,
        "count": freq.values,
        "pct": (freq.values / len(df) * 100).round(3)
    })

    return result


def get_hot_combos(
    df: pd.DataFrame,
    rolling_days: int = 30,
    top_n: int = 20
) -> pd.DataFrame:
    """
    Get hot (frequently appearing) combos in recent window.

    Args:
        df: DataFrame with draw_date and win4 columns
        rolling_days: Number of days to look back
        top_n: Number of combos to return

    Returns:
        DataFrame with combo, count, and last_seen date
    """
    cutoff = df["draw_date"].max() - timedelta(days=rolling_days)
    recent = df[df["draw_date"] >= cutoff]

    freq = recent["win4"].value_counts().head(top_n)

    # Get last seen date for each
    last_seen = recent.groupby("win4")["draw_date"].max()

    result = pd.DataFrame({
        "combo": freq.index,
        "count": freq.values,
        "last_seen": [last_seen.get(c, None) for c in freq.index]
    })

    return result


def get_cold_combos(
    df: pd.DataFrame,
    rolling_days: int = 30,
    min_historical_count: int = 2
) -> pd.DataFrame:
    """
    Get cold (infrequently appearing) combos that have appeared before.

    Args:
        df: DataFrame with draw_date and win4 columns
        rolling_days: Number of days to look back
        min_historical_count: Minimum historical appearances to consider

    Returns:
        DataFrame with combo, recent_count, historical_count, last_seen
    """
    cutoff = df["draw_date"].max() - timedelta(days=rolling_days)
    recent = df[df["draw_date"] >= cutoff]
    historical = df[df["draw_date"] < cutoff]

    # Get historical frequency
    hist_freq = historical["win4"].value_counts()
    hist_freq = hist_freq[hist_freq >= min_historical_count]

    # Get recent frequency
    recent_freq = recent["win4"].value_counts()

    # Find combos that appeared historically but rarely/never recently
    results = []
    for combo in hist_freq.index:
        recent_count = recent_freq.get(combo, 0)
        hist_count = hist_freq[combo]

        # Calculate "coldness" - high historical but low recent
        if recent_count <= 1:  # Cold threshold
            last_seen = df[df["win4"] == combo]["draw_date"].max()
            results.append({
                "combo": combo,
                "recent_count": recent_count,
                "historical_count": hist_count,
                "last_seen": last_seen
            })

    result = pd.DataFrame(results)
    if len(result) > 0:
        result = result.sort_values("historical_count", ascending=False)

    return result


def get_hot_cold_score(
    df: pd.DataFrame,
    rolling_days: int = 30
) -> pd.DataFrame:
    """
    Calculate hot/cold score for each combo.

    Score = (recent_freq - expected_freq) / std_dev

    Positive = hot, Negative = cold

    Args:
        df: DataFrame with draw_date and win4 columns
        rolling_days: Rolling window size

    Returns:
        DataFrame with combo and score
    """
    cutoff = df["draw_date"].max() - timedelta(days=rolling_days)
    recent = df[df["draw_date"] >= cutoff]

    freq = recent["win4"].value_counts()

    # Expected frequency (uniform distribution)
    total = len(recent)
    expected = total / 10000  # 10000 possible combos

    # Standard deviation for binomial
    std = np.sqrt(expected * (1 - 1/10000))

    # Calculate z-score
    scores = (freq - expected) / std if std > 0 else freq - expected

    result = pd.DataFrame({
        "combo": scores.index,
        "count": freq.values,
        "score": scores.values.round(2)
    })

    return result.sort_values("score", ascending=False)


def get_digit_sum_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get distribution of digit sums.

    Args:
        df: DataFrame with win4 column

    Returns:
        DataFrame with sum, count, and percentage
    """
    sums = df["win4"].apply(lambda x: sum(int(d) for d in x))
    freq = sums.value_counts().sort_index()

    # Ensure all possible sums (0-36) are present
    full_index = range(37)
    freq = freq.reindex(full_index, fill_value=0)

    result = pd.DataFrame({
        "digit_sum": freq.index,
        "count": freq.values,
        "pct": (freq.values / len(df) * 100).round(2)
    })

    return result


def get_pattern_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get distribution of pattern types.

    Args:
        df: DataFrame with win4 column

    Returns:
        DataFrame with pattern, count, percentage, and description
    """
    from .data import get_pattern_type

    patterns = df["win4"].apply(get_pattern_type)
    freq = patterns.value_counts()

    result = pd.DataFrame({
        "pattern": freq.index,
        "count": freq.values,
        "pct": (freq.values / len(df) * 100).round(2)
    })

    # Add descriptions
    result["description"] = result["pattern"].map(config.pattern_names)

    # Sort by expected probability order
    pattern_order = ["ABCD", "AABC", "AABB", "AAAB", "AAAA"]
    result["sort_key"] = result["pattern"].apply(lambda x: pattern_order.index(x))
    result = result.sort_values("sort_key").drop(columns=["sort_key"])

    return result


def get_repeat_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze digit repeats by position pairs.

    Position pairs: 1-2, 1-3, 1-4, 2-3, 2-4, 3-4

    Args:
        df: DataFrame with win4 column

    Returns:
        DataFrame with position pair, repeat count, and percentage
    """
    pairs = [
        ("1-2", 0, 1),
        ("1-3", 0, 2),
        ("1-4", 0, 3),
        ("2-3", 1, 2),
        ("2-4", 1, 3),
        ("3-4", 2, 3),
    ]

    results = []
    total = len(df)

    for name, i, j in pairs:
        matches = df["win4"].apply(lambda x: x[i] == x[j]).sum()
        results.append({
            "position_pair": name,
            "repeat_count": matches,
            "pct": round(matches / total * 100, 2)
        })

    return pd.DataFrame(results)


def get_mirror_analysis(df: pd.DataFrame) -> Dict[str, any]:
    """
    Analyze mirror/symmetry patterns.

    Checks:
    - Mirror ends (d1 = d4)
    - Mirror middle (d2 = d3)
    - Palindrome (d1=d4 AND d2=d3)
    - ABBA pattern

    Args:
        df: DataFrame with win4 column

    Returns:
        Dict with counts and percentages for each pattern
    """
    total = len(df)

    mirror_ends = df["win4"].apply(lambda x: x[0] == x[3]).sum()
    mirror_middle = df["win4"].apply(lambda x: x[1] == x[2]).sum()
    palindrome = df["win4"].apply(lambda x: x == x[::-1]).sum()
    abba = df["win4"].apply(lambda x: x[0] == x[3] and x[1] == x[2]).sum()

    return {
        "mirror_ends": {"count": mirror_ends, "pct": round(mirror_ends / total * 100, 2)},
        "mirror_middle": {"count": mirror_middle, "pct": round(mirror_middle / total * 100, 2)},
        "palindrome": {"count": palindrome, "pct": round(palindrome / total * 100, 2)},
        "abba": {"count": abba, "pct": round(abba / total * 100, 2)}
    }


def check_straight_match(combo: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Find all straight (exact) matches for a combo.

    Args:
        combo: 4-digit combo to check
        df: DataFrame with draw data

    Returns:
        DataFrame of matching draws
    """
    matches = df[df["win4"] == combo].copy()
    return matches.sort_values("draw_date", ascending=False)


def check_box_match(combo: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Find all box matches (same digits, any order).

    Args:
        combo: 4-digit combo to check
        df: DataFrame with draw data

    Returns:
        DataFrame of matching draws
    """
    sorted_combo = "".join(sorted(combo))
    matches = df[df["win4"].apply(lambda x: "".join(sorted(x))) == sorted_combo].copy()
    return matches.sort_values("draw_date", ascending=False)


def calculate_performance(
    df: pd.DataFrame,
    rolling_days: int = 30,
    prediction_method: str = "most_frequent"
) -> pd.DataFrame:
    """
    Calculate prediction performance over time.

    For each day, predicts the next draw based on the rolling window,
    then checks if prediction was correct.

    Args:
        df: DataFrame with draw data
        rolling_days: Size of lookback window
        prediction_method: "most_frequent" or "hot_digit"

    Returns:
        DataFrame with date, prediction, actual, and hit columns
    """
    df_sorted = df.sort_values("draw_date").reset_index(drop=True)
    results = []

    for i in range(rolling_days, len(df_sorted)):
        # Get lookback window
        window = df_sorted.iloc[i - rolling_days:i]

        # Make prediction
        if prediction_method == "most_frequent":
            prediction = window["win4"].mode().iloc[0] if len(window) > 0 else "0000"
        else:
            # Hot digit method: most frequent digit at each position
            prediction = ""
            for pos in range(4):
                digit = window["win4"].str[pos].mode().iloc[0]
                prediction += digit

        # Check actual
        actual = df_sorted.iloc[i]["win4"]
        draw_date = df_sorted.iloc[i]["draw_date"]

        # Check hits
        straight_hit = prediction == actual
        box_hit = "".join(sorted(prediction)) == "".join(sorted(actual))

        results.append({
            "date": draw_date,
            "prediction": prediction,
            "actual": actual,
            "straight_hit": straight_hit,
            "box_hit": box_hit
        })

    return pd.DataFrame(results)
