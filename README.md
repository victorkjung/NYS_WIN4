# NYS Win 4 Lottery Analytics (Streamlit)

A production-ready analytics dashboard for **New York State Win 4** results using the official NY Open Data Socrata dataset.

- **Dataset**: Lottery Daily Numbers (Win 4) Winning Numbers  
- **Socrata Domain**: `data.ny.gov`  
- **Dataset ID**: `hsys-3def`

---

## Features

### Data + Infrastructure
- ✅ Socrata API integration with **chunked fetching** (`$limit/$offset`) + retries
- ✅ Optional **Socrata App Token** support for higher rate limits (`SOCRATA_APP_TOKEN`)
- ✅ Streamlit caching (`@st.cache_data`) with manual **Refresh cache** button
- ✅ Mobile-friendly layout + dark theme
- ✅ Plotly visualizations
- ✅ Streamlit Cloud + Docker compatible
- ✅ **Socrata “Freshness Badge”** (checks dataset metadata `dataUpdatedAt/rowsUpdatedAt`)

### Win 4 Normalization
- Converts source into **long format**: one row per draw
  - `Midday` from `midday_win_4`
  - `Evening` from `evening_win_4`
- Cleans and **zero-pads** results to `0000–9999`
- Supports multiple daily drawings (Midday + Evening)

---

## App Sections

### 1) Overview
- Draw volume trend over time (based on selected filters)

### 2) Frequency Analysis
- **Digit frequency heatmap** by position (1st–4th digit)
- Digit-sum distribution (0–36)
- **Top/Bottom** most frequent combos
- **Hot List** (rolling window) + **CSV export**

### 3) Patterns Explorer (Pairs / Repeats / Mirror Digits)
- Pattern categories:
  - **All Unique (ABCD)**
  - **One Pair (AABC)**
  - **Two Pairs (AABB)**
  - **Triple (AAAB)**
  - **Quad (AAAA)**
- Mirror and symmetry metrics:
  - `d1 = d4` (mirror ends)
  - `d2 = d3` (mirror middle)
  - Palindrome / ABBA (`d1=d4` and `d2=d3`)
- Repeats-by-position heat map (1-2, 1-3, 1-4, 2-3, 2-4, 3-4)

### 4) Trends (Hot vs Cold + Performance)
- **Hot vs Cold scoring** using a rolling window (days configurable)
- Simple performance metric:
  - Predicts “next draw” as most frequent combo in the prior window
  - Plots **hit-rate** trend over time

### 5) Watchlist (Favorite Combos)
- Add/remove favorite 4-digit combos
- Quick-add from the current Hot List
- **CSV export** of watchlist stats
- Optional **CSV import** (expects a `win4` column)

### 6) Mock Drawing Checker (Straight + Box + Box Type)
- User enters four digits (separate inputs)
- Checks against history for:
  - ✅ **Straight matches** (exact order)
  - ✅ **Box matches** (digits any order, repeats handled correctly)
- Displays match tables and Midday/Evening breakdown
- Computes **Box Type** (distinct permutation count):
  - **24-way**: ABCD (all unique)
  - **12-way**: AABC (one pair)
  - **6-way** : AABB (two pairs)
  - **4-way** : AAAB (triple)
  - **1-way** : AAAA (quad)

### 7) Data
- View the normalized dataset
- Export filtered data as CSV

---

## Quickstart (Local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Win4Lottery.py
```
Socrata App Token (Optional)
Streamlit Cloud
Add to Secrets:
SOCRATA_APP_TOKEN="YOUR_TOKEN"

Local / Docker
export SOCRATA_APP_TOKEN="YOUR_TOKEN"
Docker
docker build -t nys-win4 .
docker run -p 8501:8501 -e SOCRATA_APP_TOKEN="$SOCRATA_APP_TOKEN" nys-win4
Open:
http://localhost:8501

Repo Structure
Win4Lottery.py — Streamlit entrypoint

win4lib/
socrata_client.py — chunked Socrata fetch + retries
data.py — load + normalize + freshness badge helpers
analytics.py — digit analytics + patterns + hot/cold + watchlist + box tools

.streamlit/config.toml — theme/server config

requirements.txt — pinned dependencies

Dockerfile — container deployment

Notes / Performance Tips
The app caches dataset loads for faster exploration.
If you expand the date range to “all time,” tables may become large; filtering by date/draw type improves responsiveness.
If you hit rate limits, use a Socrata App Token.

Disclaimer

Lottery drawings are random. This project is for education and analytics only.
::contentReference[oaicite:0]{index=0}
