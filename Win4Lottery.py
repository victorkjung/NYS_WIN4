"""
NYS Win 4 Lottery Analytics (Streamlit) — production-ready
Includes:
- Socrata freshness badge via dataset metadata API
- Patterns explorer (pairs/repeats/mirrors/palindromes)
- Hot list CSV export
- Watchlist (favorites): add/remove + export + optional import CSV
- Mock Checker: 4-digit inputs -> Straight + Box matching + Box Type
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from win4lib.data import (
    load_win4_long,
    get_last_updated_hint,
    get_freshness_info,
    format_freshness_badge,
)
from win4lib.analytics import (
    add_digit_columns,
    digit_position_frequency,
    combo_frequency,
    hot_cold_scores,
    strategy_backtest_hit_rate,
    add_pattern_features,
    pattern_summary,
    pair_position_matrix,
    watchlist_stats,
    add_sorted_signature,
    box_type_for_number,
)

st.set_page_config(
    page_title="NYS Win 4 Lottery Analytics",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
@media (max-width: 768px) {
  .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
  div[data-baseweb="input"] { width: 100% !important; }
}
h1, h2, h3 { letter-spacing: -0.02em; }
</style>
""",
    unsafe_allow_html=True,
)

DATASET_DOMAIN = "data.ny.gov"
DATASET_ID = "hsys-3def"
DRAW_TYPES = ["Midday", "Evening"]


@dataclass(frozen=True)
class Filters:
    draw_types: List[str]
    start_date: date
    end_date: date


def _default_date_range() -> Tuple[date, date]:
    today = date.today()
    return (today - timedelta(days=365), today)


def _sidebar() -> Tuple[Filters, int]:
    st.sidebar.header("⚙️ Controls")
    st.sidebar.caption("Optional token: SOCRATA_APP_TOKEN (secrets/env)")

    if st.sidebar.button("🔄 Refresh data cache", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache cleared. Re-loading…", icon="✅")

    rolling = st.sidebar.slider(
        "Hot/Cold rolling window (days)",
        min_value=7,
        max_value=365,
        value=60,
        step=1,
    )

    draw_types = st.sidebar.multiselect("Draw(s)", options=DRAW_TYPES, default=DRAW_TYPES)
    if not draw_types:
        draw_types = DRAW_TYPES

    d0, d1 = _default_date_range()
    start_date, end_date = st.sidebar.date_input("Date range", value=(d0, d1))
    if isinstance(start_date, (tuple, list)) and len(start_date) == 2:
        start_date, end_date = start_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    return Filters(draw_types=draw_types, start_date=start_date, end_date=end_date), rolling


def _apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    out = df.copy()
    out = out[out["draw_type"].isin(f.draw_types)]
    out = out[(out["draw_date"].dt.date >= f.start_date) & (out["draw_date"].dt.date <= f.end_date)]
    return out


def _kpi_row(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rows (draws)", f"{len(df):,}")
    with c2:
        st.metric("Unique combos", f"{df['win4'].nunique():,}" if len(df) else "0")
    with c3:
        st.metric("Date min", df["draw_date"].min().date().isoformat() if len(df) else "—")
    with c4:
        st.metric("Date max", df["draw_date"].max().date().isoformat() if len(df) else "—")


def _heatmap_digit_position(freq: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=freq.values,
            x=[str(c) for c in freq.columns],
            y=[f"Pos {i}" for i in freq.index],
            hovertemplate="Position=%{y}<br>Digit=%{x}<br>Count=%{z}<extra></extra>",
        )
    )
    fig.update_layout(title=title, xaxis_title="Digit", yaxis_title="Position", height=420)
    return fig


def _tidy_pair_matrix(df_pairs: pd.DataFrame) -> pd.DataFrame:
    """
    Defensive: ensures we always get a 2-col df: pair,count
    even if upstream changes.
    """
    if df_pairs is None or df_pairs.empty:
        return pd.DataFrame({"pair": [], "count": []})

    tmp = df_pairs.reset_index()

    cols = list(tmp.columns)
    if len(cols) < 2:
        return pd.DataFrame({"pair": [], "count": []})

    # Rename first two columns to pair/count and select only those
    tmp = tmp.rename(columns={cols[0]: "pair", cols[1]: "count"})
    tmp = tmp[["pair", "count"]]
    return tmp


def main() -> None:
    st.title("🎰 NYS Win 4 Lottery Analytics")

    data_updated, rows_updated, _label = get_freshness_info(DATASET_DOMAIN, DATASET_ID)
    st.markdown(format_freshness_badge(data_updated, rows_updated), unsafe_allow_html=True)

    filters, rolling_days = _sidebar()

    with st.spinner("Loading NYS Win 4 data…"):
        df_long = load_win4_long(domain=DATASET_DOMAIN, dataset_id=DATASET_ID)

    st.caption(get_last_updated_hint(df_long))

    df = _apply_filters(df_long, filters)
    df = add_digit_columns(df)
    df = add_pattern_features(df)
    df = add_sorted_signature(df)

    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

    _kpi_row(df)

    tabs = st.tabs(["📌 Overview", "🔥 Frequency", "🧩 Patterns", "📈 Trends", "⭐ Watchlist", "✅ Mock Checker", "🧾 Data"])

    with tabs[0]:
        st.subheader("Overview")
        if df.empty:
            st.info("No data for the selected filters.")
        else:
            daily = df.groupby(df["draw_date"].dt.date).size().reset_index(name="draws")
            daily.columns = ["date", "draws"]
            fig = px.line(daily, x="date", y="draws", title="Draw count per day (filtered)")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.subheader("Frequency Analysis")

        c1, c2 = st.columns(2)
        with c1:
            freq_pos = digit_position_frequency(df)
            st.plotly_chart(_heatmap_digit_position(freq_pos, "Digit frequency by position (1–4)"), use_container_width=True)

        with c2:
            if df.empty:
                st.info("No data to plot.")
            else:
                sum_counts = df["digit_sum"].value_counts().sort_index().reset_index()
                sum_counts.columns = ["digit_sum", "count"]
                fig = px.bar(sum_counts, x="digit_sum", y="count", title="Distribution: digit sum (0–36)")
                fig.update_layout(height=420)
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("#### Hot list (exportable)")
        hot_n = st.slider("Hot list size", 10, 500, 50, step=10)
        hot_df = hot_cold_scores(df, window_days=rolling_days).head(hot_n)
        st.dataframe(hot_df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Hot List CSV",
            data=hot_df.to_csv(index=False).encode("utf-8"),
            file_name=f"nys_win4_hot_list_{rolling_days}d.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.divider()
        st.markdown("#### Top / Bottom combos")
        top_n = st.slider("Show top/bottom N combos", 10, 200, 50, step=10)
        freq_combo = combo_frequency(df)

        colT, colBtm = st.columns(2)
        with colT:
            st.markdown("**Most frequent**")
            st.dataframe(freq_combo.head(top_n), use_container_width=True, hide_index=True)
        with colBtm:
            st.markdown("**Least frequent**")
            st.dataframe(freq_combo.tail(top_n), use_container_width=True, hide_index=True)

    # ✅ CRASH FIX IS HERE
    with tabs[2]:
        st.subheader("Pattern Explorer: Pairs / Repeats / Mirrors")

        if df.empty:
            st.info("No data for selected filters.")
        else:
            summ = pattern_summary(df)
            fig = px.bar(summ, x="pattern_label", y="count", title="Pattern distribution")
            fig.update_layout(height=420, xaxis_title="Pattern", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                mirror = pd.DataFrame(
                    {
                        "metric": ["Mirror ends (d1=d4)", "Mirror middle (d2=d3)", "Palindrome (ABBA)"],
                        "count": [
                            int(df["is_mirror_ends"].sum()),
                            int(df["is_mirror_middle"].sum()),
                            int(df["is_palindrome"].sum()),
                        ],
                    }
                )
                mirror["share"] = mirror["count"] / max(len(df), 1)
                st.dataframe(mirror, use_container_width=True, hide_index=True)

            with c2:
                # pair_position_matrix now returns tidy shape,
                # but we still defend in case of future edits.
                pm_raw = pair_position_matrix(df)
                pm = _tidy_pair_matrix(pm_raw)

                fig2 = px.bar(pm, x="pair", y="count", title="Where repeats occur (position pairs)")
                fig2.update_layout(height=420, xaxis_title="Position Pair", yaxis_title="Count")
                st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            st.markdown("#### Filter by pattern and inspect combos")
            pat = st.selectbox("Pattern", options=sorted(df["pattern_label"].unique().tolist()))
            dpat = df[df["pattern_label"] == pat]
            pat_freq = dpat["win4"].value_counts().head(100).reset_index()
            pat_freq.columns = ["win4", "count"]
            st.dataframe(pat_freq, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.subheader("Trends: Hot vs Cold + Performance")

        if df.empty:
            st.info("No data for selected filters.")
        else:
            scores = hot_cold_scores(df, window_days=rolling_days)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Hot (last {rolling_days} days)**")
                st.dataframe(scores.sort_values("score", ascending=False).head(30), use_container_width=True, hide_index=True)
            with c2:
                st.markdown(f"**Cold (last {rolling_days} days)**")
                st.dataframe(scores.sort_values("score", ascending=True).head(30), use_container_width=True, hide_index=True)

            st.divider()

            perf = strategy_backtest_hit_rate(df, window_days=rolling_days)
            fig = px.line(perf, x="draw_date", y="hit_rate", title=f"Strategy hit rate over time (window={rolling_days} days)")
            fig.update_layout(height=420, yaxis_tickformat=".2%")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.subheader("⭐ Watchlist (favorite combos)")

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            add_one = st.text_input("Add combo (0000–9999)", value="", max_chars=4, placeholder="e.g., 0427")
        with c2:
            if st.button("➕ Add", use_container_width=True):
                s = add_one.strip()
                if s.isdigit() and len(s) == 4:
                    if s not in st.session_state["watchlist"]:
                        st.session_state["watchlist"].append(s)
                        st.toast(f"Added {s}", icon="⭐")
                else:
                    st.toast("Enter exactly 4 digits.", icon="⚠️")
        with c3:
            st.write("")

        hot_pick = st.multiselect(
            "Quick-add from current Hot List",
            options=hot_cold_scores(df, window_days=rolling_days)["win4"].head(200).tolist() if not df.empty else [],
            default=[],
        )
        if st.button("⭐ Add selected to watchlist", use_container_width=True) and hot_pick:
            for w in hot_pick:
                if w not in st.session_state["watchlist"]:
                    st.session_state["watchlist"].append(w)

        if st.session_state["watchlist"]:
            remove_pick = st.multiselect("Remove from watchlist", options=sorted(st.session_state["watchlist"]))
            if st.button("🗑️ Remove selected", use_container_width=True) and remove_pick:
                st.session_state["watchlist"] = [w for w in st.session_state["watchlist"] if w not in set(remove_pick)]

        st.divider()
        wl = sorted(st.session_state["watchlist"])
        st.caption(f"Watchlist size: {len(wl)}")

        stats = watchlist_stats(df, wl, window_days=rolling_days)
        st.dataframe(stats, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Watchlist CSV",
            data=stats.to_csv(index=False).encode("utf-8"),
            file_name="nys_win4_watchlist.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("#### Optional: Import watchlist from CSV")
        up = st.file_uploader("Upload CSV with a 'win4' column", type=["csv"])
        if up is not None:
            try:
                imp = pd.read_csv(up)
                if "win4" not in imp.columns:
                    st.error("CSV must include a 'win4' column.")
                else:
                    new_vals = (
                        imp["win4"].astype(str).str.replace(r"\D+", "", regex=True).str.zfill(4)
                        .loc[lambda s: s.str.fullmatch(r"\d{4}", na=False)]
                        .unique()
                        .tolist()
                    )
                    for w in new_vals:
                        if w not in st.session_state["watchlist"]:
                            st.session_state["watchlist"].append(w)
                    st.success(f"Imported {len(new_vals)} combos.")
            except Exception as e:
                st.error(f"Import failed: {e}")

    with tabs[5]:
        st.subheader("Mock Drawing Checker (Straight + Box + Box Type)")
        st.caption("Straight = exact order. Box = same digits any order (repeats count). Box Type = distinct permutations.")

        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        with dcol1:
            d1 = st.number_input("Digit 1", min_value=0, max_value=9, value=0, step=1)
        with dcol2:
            d2 = st.number_input("Digit 2", min_value=0, max_value=9, value=0, step=1)
        with dcol3:
            d3 = st.number_input("Digit 3", min_value=0, max_value=9, value=0, step=1)
        with dcol4:
            d4 = st.number_input("Digit 4", min_value=0, max_value=9, value=0, step=1)

        user_straight = f"{d1}{d2}{d3}{d4}"
        box_label, box_ways, user_box_sig = box_type_for_number(user_straight)

        scope_col1, scope_col2 = st.columns([1, 2])
        with scope_col1:
            draw_scope = st.selectbox("Check which draws?", options=["Both (Midday + Evening)", "Midday only", "Evening only"])
        with scope_col2:
            st.markdown(f"**Your Box Type:** {box_label} ({box_ways} ways)  \n**Sorted signature:** `{user_box_sig}`")

        if df.empty:
            st.info("No data for the selected filters.")
        else:
            dff = df.copy()
            if draw_scope == "Midday only":
                dff = dff[dff["draw_type"] == "Midday"]
            elif draw_scope == "Evening only":
                dff = dff[dff["draw_type"] == "Evening"]

            straight_matches = dff[dff["win4"] == user_straight].sort_values("draw_date", ascending=False)
            box_matches_all = dff[dff["sig_sorted"] == user_box_sig].sort_values("draw_date", ascending=False)
            box_only_matches = box_matches_all[box_matches_all["win4"] != user_straight]

            s_count = len(straight_matches)
            b_count = len(box_only_matches)
            total_box_including_straight = len(box_matches_all)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Your number", user_straight)
            with k2:
                st.metric("Box Type", box_label)
            with k3:
                st.metric("Straight wins", f"{s_count:,}")
            with k4:
                st.metric("Box wins (non-straight)", f"{b_count:,}")

            st.caption(f"Total box matches (including straight): {total_box_including_straight:,}")

            if s_count == 0 and total_box_including_straight == 0:
                st.warning("No straight or box matches found in the current filtered dataset.")
            else:
                if s_count > 0:
                    st.markdown("### ✅ Straight Matches (Exact Order)")
                    show = straight_matches[["draw_date", "draw_type", "win4", "digit_sum"]].copy()
                    show["match_type"] = "Straight"
                    show["user_box_type"] = box_label
                    st.dataframe(show, use_container_width=True, hide_index=True)

                if total_box_including_straight > 0:
                    st.markdown("### 🎯 Box Matches (Any Order)")
                    showb = box_matches_all[["draw_date", "draw_type", "win4", "digit_sum"]].copy()
                    showb["match_type"] = showb["win4"].apply(lambda x: "Straight (also)" if x == user_straight else "Box")
                    showb["user_box_type"] = box_label
                    st.dataframe(showb, use_container_width=True, hide_index=True)

                breakdown = pd.DataFrame({
                    "draw_type": ["Midday", "Evening"],
                    "straight": [
                        int((straight_matches["draw_type"] == "Midday").sum()),
                        int((straight_matches["draw_type"] == "Evening").sum()),
                    ],
                    "box_total_including_straight": [
                        int((box_matches_all["draw_type"] == "Midday").sum()),
                        int((box_matches_all["draw_type"] == "Evening").sum()),
                    ],
                    "box_only": [
                        int((box_only_matches["draw_type"] == "Midday").sum()),
                        int((box_only_matches["draw_type"] == "Evening").sum()),
                    ],
                })
                st.markdown("### Breakdown by draw")
                st.dataframe(breakdown, use_container_width=True, hide_index=True)

    with tabs[6]:
        st.subheader("Underlying Data")
        st.caption("Normalized long-format: one row per draw (Midday/Evening).")

        st.dataframe(df.sort_values("draw_date", ascending=False).head(500), use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download filtered CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="nys_win4_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
