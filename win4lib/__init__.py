"""
WIN4 Library - Analytics and utilities for NYS Win 4 Lottery data.
"""
from .config import config
from .socrata_client import SocrataClient, SocrataError
from .data import (
    normalize_win4_data,
    normalize_combo,
    filter_by_date_range,
    filter_by_draw_type,
    get_date_range,
    add_derived_columns,
    get_pattern_type,
    get_box_permutation_count,
    calculate_date_preset,
    validate_combo,
)
from .analytics import (
    get_digit_frequency,
    get_digit_frequency_matrix,
    get_combo_frequency,
    get_hot_combos,
    get_cold_combos,
    get_hot_cold_score,
    get_digit_sum_distribution,
    get_pattern_distribution,
    get_repeat_analysis,
    get_mirror_analysis,
    check_straight_match,
    check_box_match,
    calculate_performance,
)
from .storage import (
    init_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    clear_watchlist,
    get_watchlist,
    get_watchlist_count,
    is_in_watchlist,
    bulk_add_to_watchlist,
    export_watchlist_csv,
    import_watchlist_csv,
    get_watchlist_stats,
)

__version__ = "1.1.0"
__all__ = [
    # Config
    "config",
    # Socrata
    "SocrataClient",
    "SocrataError",
    # Data
    "normalize_win4_data",
    "normalize_combo",
    "filter_by_date_range",
    "filter_by_draw_type",
    "get_date_range",
    "add_derived_columns",
    "get_pattern_type",
    "get_box_permutation_count",
    "calculate_date_preset",
    "validate_combo",
    # Analytics
    "get_digit_frequency",
    "get_digit_frequency_matrix",
    "get_combo_frequency",
    "get_hot_combos",
    "get_cold_combos",
    "get_hot_cold_score",
    "get_digit_sum_distribution",
    "get_pattern_distribution",
    "get_repeat_analysis",
    "get_mirror_analysis",
    "check_straight_match",
    "check_box_match",
    "calculate_performance",
    # Storage
    "init_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "clear_watchlist",
    "get_watchlist",
    "get_watchlist_count",
    "is_in_watchlist",
    "bulk_add_to_watchlist",
    "export_watchlist_csv",
    "import_watchlist_csv",
    "get_watchlist_stats",
]
