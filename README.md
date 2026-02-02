# NYS Win 4 Lottery Analytics (Streamlit)

Win 4 Analyzer for Entertainment Purposes

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-app-red.svg)

A production-ready analytics dashboard for **New York State Win 4** results using the official NY Open Data Socrata dataset.

- **Dataset**: Lottery Daily Numbers (Win 4) Winning Numbers  
- **Socrata Domain**: `data.ny.gov`  
- **Dataset ID**: `hsys-3def`

# NYS WIN4 - Phase 1 Update

## Quick Start

Replace your existing files with these updated versions:

```
NYS_WIN4/
├── Win4Lottery.py          # REPLACE - Main app (completely rewritten)
├── requirements.txt        # REPLACE - Updated dependencies
├── Dockerfile              # REPLACE - Updated container config
├── .streamlit/
│   └── config.toml         # REPLACE - Theme & server settings
└── win4lib/
    ├── __init__.py         # REPLACE - Package exports
    ├── config.py           # NEW - Centralized configuration
    ├── socrata_client.py   # REPLACE - Added progress callbacks
    ├── data.py             # REPLACE - Enhanced data processing
    ├── analytics.py        # REPLACE - Core analytics functions
    └── storage.py          # NEW - Watchlist persistence
```

## Installation

1. **Backup your existing code first!**

2. **Copy all files** from this package to your project directory, replacing existing files.

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   streamlit run Win4Lottery.py
   ```

## What's New in Phase 1

### ✅ Configuration System (`win4lib/config.py`)
- All configurable values centralized in one place
- Easy to modify default rolling window, chart settings, API parameters
- Pattern names and payout values defined as constants

### ✅ Progress Indicators
- Visual progress bar during initial data load
- Shows record count as data streams in
- Better user experience for large datasets

### ✅ Date Presets
- One-click buttons: "7 Days", "30 Days", "90 Days", "1 Year", "All Time"
- Still supports manual date picker for custom ranges
- Selected preset is highlighted

### ✅ Improved Watchlist
- Persists across browser sessions (file-based storage)
- CSV import/export functionality
- Statistics for each watchlist combo (straight/box hits, last seen, etc.)
- Quick-add from Hot List

### ✅ Enhanced Data Loading
- Chunked fetching with retry logic
- Metadata freshness badge
- Manual refresh button to clear cache

### ✅ Mobile-Friendly CSS
- Larger touch targets
- Responsive tables
- Better font sizing on mobile devices

### ✅ Code Organization
- Clean separation of concerns (config, data, analytics, storage)
- Type hints throughout
- Comprehensive docstrings
- Modular tab rendering functions

## Configuration

### Socrata App Token (Optional but Recommended)

For higher API rate limits, add your token to Streamlit secrets:

**For Streamlit Cloud:** Add to your app's secrets in the dashboard:
```toml
SOCRATA_APP_TOKEN = "your_token_here"
```

**For local development:** Create `.streamlit/secrets.toml`:
```toml
SOCRATA_APP_TOKEN = "your_token_here"
```

### Customizing Settings

Edit `win4lib/config.py` to change defaults:

```python
@dataclass
class AnalyticsConfig:
    default_rolling_window: int = 30  # Change default window size
    hot_threshold_percentile: float = 75.0
    cold_threshold_percentile: float = 25.0
    min_draws_for_analysis: int = 10
    default_top_n: int = 20  # Change number of top combos shown
```

## Docker

Build and run with Docker:

```bash
# Build
docker build -t nys-win4 .

# Run
docker run -p 8501:8501 nys-win4

# Run with Socrata token
docker run -p 8501:8501 -e SOCRATA_APP_TOKEN="your_token" nys-win4
```

## File Descriptions

| File | Purpose |
|------|---------|
| `Win4Lottery.py` | Main Streamlit application with all UI tabs |
| `win4lib/config.py` | Centralized configuration dataclasses |
| `win4lib/socrata_client.py` | Socrata API client with progress callbacks |
| `win4lib/data.py` | Data normalization and preprocessing |
| `win4lib/analytics.py` | Frequency, pattern, and trend analysis |
| `win4lib/storage.py` | Watchlist persistence and CSV import/export |
| `win4lib/__init__.py` | Package exports for clean imports |

## Next Steps (Phase 2+)

After implementing Phase 1, you can move on to:

- **Phase 2:** Gap analysis, time-based patterns, statistical significance
- **Phase 3:** Smart number picker, historical what-if calculator
- **Phase 4:** Help docs, additional mobile polish, unit tests

See the full implementation plan for details on upcoming phases.

---

Questions? Issues? The code is modular - feel free to modify individual modules without affecting others.


Disclaimer
```
Lottery drawings are random. This project is for education and analytics only.
::contentReference[oaicite:0]{index=0}
```
