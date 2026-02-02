"""
Centralized configuration for WIN4 Analyzer.
All configurable values in one place for easy maintenance.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AnalyticsConfig:
    """Analytics-related settings."""
    default_rolling_window: int = 30
    hot_threshold_percentile: float = 75.0
    cold_threshold_percentile: float = 25.0
    min_draws_for_analysis: int = 10
    default_top_n: int = 20


@dataclass
class UIConfig:
    """UI-related settings."""
    chart_height: int = 400
    heatmap_colorscale: str = "Blues"
    table_page_size: int = 50
    date_format: str = "%Y-%m-%d"
    digits: list = field(default_factory=lambda: [str(i) for i in range(10)])


@dataclass
class APIConfig:
    """Socrata API settings."""
    domain: str = "data.ny.gov"
    dataset_id: str = "hsys-3def"
    chunk_size: int = 10000
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30


@dataclass
class PayoutConfig:
    """Win4 payout amounts (for $1 bet)."""
    straight: int = 5000
    box_24: int = 208      # 24-way box (ABCD - all unique)
    box_12: int = 416      # 12-way box (AABC - one pair)
    box_6: int = 833       # 6-way box (AABB - two pairs)
    box_4: int = 1250      # 4-way box (AAAB - triple)


@dataclass
class Config:
    """Main configuration container."""
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    api: APIConfig = field(default_factory=APIConfig)
    payouts: PayoutConfig = field(default_factory=PayoutConfig)

    # Date presets for quick filtering (value = number of days, None = all time)
    date_presets: Dict[str, Optional[int]] = field(default_factory=lambda: {
        "7 Days": 7,
        "30 Days": 30,
        "90 Days": 90,
        "1 Year": 365,
        "All Time": None
    })

    # Pattern definitions
    pattern_names: Dict[str, str] = field(default_factory=lambda: {
        "ABCD": "All Unique (24-way)",
        "AABC": "One Pair (12-way)",
        "AABB": "Two Pairs (6-way)",
        "AAAB": "Triple (4-way)",
        "AAAA": "Quad (1-way)"
    })


# Global config instance - import this in other modules
config = Config()
