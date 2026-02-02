"""
NYS Win 4 Lottery Analytics - Streamlit Dashboard
A comprehensive analytics tool for Win 4 lottery results.

For entertainment purposes only.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Import win4lib modules
from win4lib import (
    config,
    SocrataClient,
    SocrataError,
    normalize_win4_data,
    filter_by_date_range,
    filter_by_draw_type,
    get_date_range,
    add_derived_columns,
    get_pattern_type,
    get_box_permutation_count,
    calculate_date_preset,
    validate_combo,
    get_digit_frequency,
    get_digit_frequency_matrix,
    get_combo_frequency,
    get_hot_combos,
    get_cold_combos,
    get_digit_sum_distribution,
    get_pattern_distribution,
    get_repeat_analysis,
    get_mirror_analysis,
    check_straight_match,
    check_box_match,
    init_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    clear_watchlist,
    get_watchlist,
    get_watchlist_count,
    bulk_add_to_watchlist,
    export_watchlist_csv,
    import_watchlist_csv,
    get_watchlist_stats,
)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="NYS Win 4 Analytics",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# Custom CSS for Mobile & Styling
# =============================================================================

st.markdown("""
<style>
/* Responsive tables */
.stDataFrame {
    max-width: 100%;
    overflow-x: auto;
}

/* Larger touch targets */
.stButton > button {
    min-height: 44px;
}

/* Better input sizing on mobile */
@media (max-width: 768px) {
    .stTextInput input {
        font-size: 16px !important;
    }
    
    .stSelectbox select {
        font-size: 16px !important;
    }
}

/* Stat card styling */
.stat-box {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 0.5rem;
}

.stat-box h3 {
    margin: 0;
    color: #fff;
    font-size: 1.5rem;
}

.stat-box p {
    margin: 0;
    color: #a0c4e8;
    font-size: 0.85rem;
}

/* Combo display */
.combo-display {
    font-family: 'Courier New', monospace;
    font-size: 2rem;
    font-weight: bold;
    letter-spacing: 0.5rem;
    color: #4CAF50;
}

/* Hot/Cold indicators */
.hot-indicator { color: #ff4444; }
.cold-indicator { color: #4444ff; }

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Data Loading with Progress
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_data() -> pd.DataFrame:
    """Load and normalize WIN4 data from Socrata."""
    # Get app token from secrets if available
    app_token = st.secrets.get("SOCRATA_APP_TOKEN", None)
    
    client = SocrataClient(app_token=app_token)
    raw_data = client.fetch_all()
    df = normalize_win4_data(raw_data)
    df = add_derived_columns(df)
    
    return df


def load_data_with_progress() -> pd.DataFrame:
    """Load data with visual progress indicator."""
    # Check if data is already cached
    if "data_loaded" in st.session_state and st.session_state.data_loaded:
        return load_data()
    
    progress_container = st.empty()
    
    with progress_container.container():
        st.info("📊 Loading lottery data from NY Open Data...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        app_token = st.secrets.get("SOCRATA_APP_TOKEN", None)
        client = SocrataClient(app_token=app_token)
        
        def update_progress(current: int, total: int):
            progress = min(current / total, 1.0) if total > 0 else 0
            progress_bar.progress(progress)
            status_text.text(f"Loading: {current:,} / ~{total:,} records")
        
        try:
            raw_data = client.fetch_all(progress_callback=update_progress)
            df = normalize_win4_data(raw_data)
            df = add_derived_columns(df)
            
            st.session_state.data_loaded = True
            
        except SocrataError as e:
            st.error(f"Failed to load data: {e}")
            return pd.DataFrame()
    
    progress_container.empty()
    
    # Also populate the cache
    return load_data()


def get_freshness_info() -> dict:
    """Get dataset freshness information."""
    try:
        app_token = st.secrets.get("SOCRATA_APP_TOKEN", None)
        client = SocrataClient(app_token=app_token)
        return client.get_freshness()
    except Exception:
        return {"data_updated": "Unknown", "rows_updated": "Unknown"}


# =============================================================================
# Sidebar
# =============================================================================

def render_sidebar(df: pd.DataFrame):
    """Render sidebar with filters and controls."""
    st.sidebar.title("🎰 Win 4 Analytics")
    
    # Data freshness badge
    with st.sidebar.expander("📡 Data Status", expanded=False):
        freshness = get_freshness_info()
        st.caption(f"Last Updated: {freshness['data_updated'][:10] if len(freshness['data_updated']) > 10 else freshness['data_updated']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.session_state.data_loaded = False
                st.rerun()
        with col2:
            st.metric("Records", f"{len(df):,}")
    
    st.sidebar.divider()
    
    # Date Range Section
    st.sidebar.subheader("📅 Date Range")
    
    min_date, max_date = get_date_range(df)
    
    # Date preset buttons
    st.sidebar.caption("Quick Select:")
    preset_cols = st.sidebar.columns(3)
    preset_names = list(config.date_presets.keys())
    
    # Initialize session state for date preset
    if "date_preset" not in st.session_state:
        st.session_state.date_preset = "30 Days"
    
    # Render preset buttons
    for i, preset_name in enumerate(preset_names[:3]):
        with preset_cols[i % 3]:
            if st.button(preset_name, key=f"preset_{i}", use_container_width=True,
                        type="primary" if st.session_state.date_preset == preset_name else "secondary"):
                st.session_state.date_preset = preset_name
                st.rerun()
    
    preset_cols2 = st.sidebar.columns(2)
    for i, preset_name in enumerate(preset_names[3:]):
        with preset_cols2[i]:
            if st.button(preset_name, key=f"preset_{i+3}", use_container_width=True,
                        type="primary" if st.session_state.date_preset == preset_name else "secondary"):
                st.session_state.date_preset = preset_name
                st.rerun()
    
    # Calculate default dates from preset
    preset_days = config.date_presets.get(st.session_state.date_preset)
    if preset_days is None:
        default_start = min_date.date()
    else:
        default_start = max(min_date.date(), (max_date - timedelta(days=preset_days)).date())
    
    # Manual date pickers
    st.sidebar.caption("Or select custom range:")
    start_date = st.sidebar.date_input(
        "Start",
        value=default_start,
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    end_date = st.sidebar.date_input(
        "End",
        value=max_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    
    st.sidebar.divider()
    
    # Draw Type Filter
    st.sidebar.subheader("🎯 Draw Type")
    draw_type = st.sidebar.radio(
        "Select draws",
        ["Both", "Midday", "Evening"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.sidebar.divider()
    
    # Analysis Settings
    st.sidebar.subheader("⚙️ Settings")
    rolling_window = st.sidebar.slider(
        "Rolling Window (days)",
        min_value=7,
        max_value=90,
        value=config.analytics.default_rolling_window,
        help="Used for hot/cold analysis"
    )
    
    return start_date, end_date, draw_type, rolling_window


# =============================================================================
# Tab: Overview
# =============================================================================

def render_overview_tab(df: pd.DataFrame):
    """Render overview tab with summary stats."""
    st.header("📈 Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Draws", f"{len(df):,}")
    with col2:
        unique_combos = df["win4"].nunique()
        st.metric("Unique Combos", f"{unique_combos:,}")
    with col3:
        min_date, max_date = get_date_range(df)
        days_span = (max_date - min_date).days
        st.metric("Date Range", f"{days_span:,} days")
    with col4:
        midday_count = len(df[df["draw_type"] == "Midday"])
        evening_count = len(df[df["draw_type"] == "Evening"])
        st.metric("Midday / Evening", f"{midday_count:,} / {evening_count:,}")
    
    st.divider()
    
    # Draw volume over time
    st.subheader("Draw Volume Trend")
    
    # Aggregate by month
    df_monthly = df.copy()
    df_monthly["month"] = df_monthly["draw_date"].dt.to_period("M").astype(str)
    monthly_counts = df_monthly.groupby(["month", "draw_type"]).size().reset_index(name="count")
    
    fig = px.bar(
        monthly_counts,
        x="month",
        y="count",
        color="draw_type",
        barmode="group",
        title="Monthly Draw Volume",
        labels={"month": "Month", "count": "Draws", "draw_type": "Draw Type"}
    )
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent results
    st.subheader("🕐 Recent Results")
    recent = df.head(10)[["draw_date", "draw_type", "win4", "digit_sum", "pattern_type"]]
    recent.columns = ["Date", "Draw", "Win4", "Sum", "Pattern"]
    st.dataframe(recent, use_container_width=True, hide_index=True)


# =============================================================================
# Tab: Frequency Analysis
# =============================================================================

def render_frequency_tab(df: pd.DataFrame):
    """Render frequency analysis tab."""
    st.header("📊 Frequency Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Digit Frequency by Position")
        
        # Build heatmap data
        freq_matrix = get_digit_frequency_matrix(df)
        
        fig = go.Figure(data=go.Heatmap(
            z=freq_matrix.values,
            x=freq_matrix.columns,
            y=freq_matrix.index,
            colorscale="Blues",
            text=freq_matrix.values,
            texttemplate="%{text}",
            textfont={"size": 11},
            hovertemplate="Position: %{x}<br>Digit: %{y}<br>Count: %{z}<extra></extra>"
        ))
        fig.update_layout(
            height=400,
            xaxis_title="Position",
            yaxis_title="Digit",
            yaxis=dict(dtick=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Digit Sum Distribution")
        
        sum_dist = get_digit_sum_distribution(df)
        
        fig = px.bar(
            sum_dist,
            x="digit_sum",
            y="count",
            title="Distribution of Digit Sums (0-36)",
            labels={"digit_sum": "Digit Sum", "count": "Frequency"}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Top combos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔥 Most Frequent Combos")
        top_combos = get_combo_frequency(df, top_n=config.analytics.default_top_n)
        st.dataframe(
            top_combos.rename(columns={"combo": "Combo", "count": "Count", "pct": "%"}),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.subheader("❄️ Least Frequent (Appeared)")
        # Get combos that appeared but are rare
        all_combos = get_combo_frequency(df)
        rare = all_combos.tail(20).iloc[::-1]  # Reverse to show rarest first
        st.dataframe(
            rare.rename(columns={"combo": "Combo", "count": "Count", "pct": "%"}),
            use_container_width=True,
            hide_index=True
        )


# =============================================================================
# Tab: Patterns
# =============================================================================

def render_patterns_tab(df: pd.DataFrame):
    """Render pattern analysis tab."""
    st.header("🔍 Pattern Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pattern Distribution")
        
        patterns = get_pattern_distribution(df)
        
        fig = px.pie(
            patterns,
            values="count",
            names="description",
            title="Combo Pattern Types",
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            patterns[["pattern", "description", "count", "pct"]].rename(columns={
                "pattern": "Pattern",
                "description": "Type",
                "count": "Count",
                "pct": "%"
            }),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.subheader("Position Pair Repeats")
        
        repeats = get_repeat_analysis(df)
        
        fig = px.bar(
            repeats,
            x="position_pair",
            y="pct",
            title="Repeat Rate by Position Pair",
            labels={"position_pair": "Position Pair", "pct": "Repeat %"}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Mirror Patterns")
        mirrors = get_mirror_analysis(df)
        
        mirror_df = pd.DataFrame([
            {"Pattern": "Mirror Ends (d1=d4)", "Count": mirrors["mirror_ends"]["count"], "%": mirrors["mirror_ends"]["pct"]},
            {"Pattern": "Mirror Middle (d2=d3)", "Count": mirrors["mirror_middle"]["count"], "%": mirrors["mirror_middle"]["pct"]},
            {"Pattern": "Palindrome", "Count": mirrors["palindrome"]["count"], "%": mirrors["palindrome"]["pct"]},
            {"Pattern": "ABBA Pattern", "Count": mirrors["abba"]["count"], "%": mirrors["abba"]["pct"]},
        ])
        st.dataframe(mirror_df, use_container_width=True, hide_index=True)


# =============================================================================
# Tab: Trends (Hot/Cold)
# =============================================================================

def render_trends_tab(df: pd.DataFrame, rolling_window: int):
    """Render trends and hot/cold analysis."""
    st.header("📈 Trends & Hot/Cold Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🔥 Hot Combos (Last {rolling_window} Days)")
        hot = get_hot_combos(df, rolling_days=rolling_window)
        
        if len(hot) > 0:
            hot_display = hot.copy()
            hot_display["last_seen"] = hot_display["last_seen"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                hot_display.rename(columns={
                    "combo": "Combo",
                    "count": "Count",
                    "last_seen": "Last Seen"
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Quick add to watchlist
            if st.button("➕ Add Top 5 to Watchlist"):
                added = bulk_add_to_watchlist(hot["combo"].head(5).tolist())
                st.success(f"Added {added} combos to watchlist")
        else:
            st.info("No data in selected range")
    
    with col2:
        st.subheader(f"❄️ Cold Combos (Historically Active)")
        cold = get_cold_combos(df, rolling_days=rolling_window)
        
        if len(cold) > 0:
            cold_display = cold.head(20).copy()
            cold_display["last_seen"] = cold_display["last_seen"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                cold_display.rename(columns={
                    "combo": "Combo",
                    "recent_count": "Recent",
                    "historical_count": "Historical",
                    "last_seen": "Last Seen"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No cold combos found")
    
    st.divider()
    
    # Hot digits by position
    st.subheader("🎯 Hot Digits by Position")
    
    cutoff = df["draw_date"].max() - timedelta(days=rolling_window)
    recent = df[df["draw_date"] >= cutoff]
    
    cols = st.columns(4)
    for i, col in enumerate(cols):
        with col:
            freq = get_digit_frequency(recent, i + 1)
            top_digit = freq.idxmax()
            top_count = freq.max()
            
            st.metric(
                f"Position {i+1}",
                f"Digit: {top_digit}",
                f"{top_count} times"
            )


# =============================================================================
# Tab: Watchlist
# =============================================================================

def render_watchlist_tab(df: pd.DataFrame):
    """Render watchlist management tab."""
    st.header("⭐ Watchlist")
    
    # Initialize watchlist
    init_watchlist()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Add to Watchlist")
        
        # Single combo input
        new_combo = st.text_input(
            "Enter 4-digit combo",
            max_chars=4,
            placeholder="e.g., 1234"
        )
        
        add_col1, add_col2 = st.columns(2)
        with add_col1:
            if st.button("➕ Add Combo", use_container_width=True):
                if new_combo:
                    is_valid, result = validate_combo(new_combo)
                    if is_valid:
                        if add_to_watchlist(result):
                            st.success(f"Added {result}")
                        else:
                            st.warning(f"{result} already in watchlist")
                    else:
                        st.error(result)
        
        with add_col2:
            if st.button("🗑️ Clear All", use_container_width=True):
                clear_watchlist()
                st.success("Watchlist cleared")
                st.rerun()
    
    with col2:
        st.subheader("Import/Export")
        
        # Export
        csv_data = export_watchlist_csv()
        st.download_button(
            "📥 Export CSV",
            csv_data,
            file_name="win4_watchlist.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Import
        uploaded = st.file_uploader("📤 Import CSV", type=["csv"])
        if uploaded:
            content = uploaded.read().decode("utf-8")
            results = import_watchlist_csv(content)
            st.success(f"Added: {results['added']}, Skipped: {results['skipped']}, Invalid: {results['invalid']}")
            st.rerun()
    
    st.divider()
    
    # Display watchlist
    watchlist = get_watchlist()
    
    if watchlist:
        st.subheader(f"📋 Your Watchlist ({len(watchlist)} combos)")
        
        # Get stats
        stats = get_watchlist_stats(df, watchlist)
        stats_df = pd.DataFrame(stats)
        
        # Format for display
        display_df = stats_df.copy()
        display_df["last_seen"] = display_df["last_seen"].apply(
            lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "Never"
        )
        display_df["days_ago"] = display_df["days_ago"].apply(
            lambda x: f"{int(x)} days" if pd.notna(x) else "-"
        )
        
        st.dataframe(
            display_df[["combo", "straight_hits", "box_hits", "last_seen", "days_ago", "pattern", "box_ways"]].rename(columns={
                "combo": "Combo",
                "straight_hits": "Straight",
                "box_hits": "Box",
                "last_seen": "Last Seen",
                "days_ago": "Days Ago",
                "pattern": "Pattern",
                "box_ways": "Box Ways"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Remove individual combos
        st.subheader("Remove Combos")
        combo_to_remove = st.selectbox("Select combo to remove", watchlist)
        if st.button("🗑️ Remove Selected"):
            remove_from_watchlist(combo_to_remove)
            st.success(f"Removed {combo_to_remove}")
            st.rerun()
    else:
        st.info("Your watchlist is empty. Add combos above!")


# =============================================================================
# Tab: Checker
# =============================================================================

def render_checker_tab(df: pd.DataFrame):
    """Render mock drawing checker tab."""
    st.header("🔎 Drawing Checker")
    
    st.markdown("Check any 4-digit combo against historical results.")
    
    # Input
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        d1 = st.selectbox("D1", config.ui.digits, key="check_d1")
    with col2:
        d2 = st.selectbox("D2", config.ui.digits, key="check_d2")
    with col3:
        d3 = st.selectbox("D3", config.ui.digits, key="check_d3")
    with col4:
        d4 = st.selectbox("D4", config.ui.digits, key="check_d4")
    
    combo = f"{d1}{d2}{d3}{d4}"
    
    with col5:
        st.markdown(f"### Combo: `{combo}`")
        pattern = get_pattern_type(combo)
        box_ways = get_box_permutation_count(combo)
        st.caption(f"{config.pattern_names[pattern]} ({box_ways}-way box)")
    
    st.divider()
    
    # Results
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Straight Matches")
        straight = check_straight_match(combo, df)
        st.metric("Total Straight Hits", len(straight))
        
        if len(straight) > 0:
            display = straight[["draw_date", "draw_type"]].head(20).copy()
            display["draw_date"] = display["draw_date"].dt.strftime("%Y-%m-%d")
            display.columns = ["Date", "Draw"]
            st.dataframe(display, use_container_width=True, hide_index=True)
            
            # Breakdown
            midday = len(straight[straight["draw_type"] == "Midday"])
            evening = len(straight[straight["draw_type"] == "Evening"])
            st.caption(f"Midday: {midday} | Evening: {evening}")
        else:
            st.info("No straight matches found")
    
    with col2:
        st.subheader("📦 Box Matches")
        box = check_box_match(combo, df)
        st.metric("Total Box Hits", len(box))
        
        if len(box) > 0:
            display = box[["draw_date", "draw_type", "win4"]].head(20).copy()
            display["draw_date"] = display["draw_date"].dt.strftime("%Y-%m-%d")
            display.columns = ["Date", "Draw", "Result"]
            st.dataframe(display, use_container_width=True, hide_index=True)
            
            # Breakdown
            midday = len(box[box["draw_type"] == "Midday"])
            evening = len(box[box["draw_type"] == "Evening"])
            st.caption(f"Midday: {midday} | Evening: {evening}")
        else:
            st.info("No box matches found")
    
    # Add to watchlist button
    if st.button(f"⭐ Add {combo} to Watchlist"):
        if add_to_watchlist(combo):
            st.success(f"Added {combo} to watchlist!")
        else:
            st.info(f"{combo} is already in your watchlist")


# =============================================================================
# Tab: Data Export
# =============================================================================

def render_data_tab(df: pd.DataFrame):
    """Render data viewing and export tab."""
    st.header("📁 Data Export")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", f"{len(df):,}")
    with col2:
        min_date, max_date = get_date_range(df)
        st.metric("Date Range", f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    with col3:
        st.metric("Columns", len(df.columns))
    
    st.divider()
    
    # Data preview
    st.subheader("Data Preview")
    display_cols = ["draw_date", "draw_type", "win4", "digit_sum", "pattern_type"]
    st.dataframe(df[display_cols].head(100), use_container_width=True, hide_index=True)
    
    # Export
    st.subheader("Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV export
        csv = df[display_cols].to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"win4_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # JSON export
        json_data = df[display_cols].to_json(orient="records", date_format="iso")
        st.download_button(
            "📥 Download JSON",
            json_data,
            file_name=f"win4_data_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )


# =============================================================================
# Main App
# =============================================================================

def main():
    """Main application entry point."""
    # Load data with progress indicator
    df_full = load_data_with_progress()
    
    if len(df_full) == 0:
        st.error("Failed to load data. Please check your connection and try again.")
        st.stop()
    
    # Render sidebar and get filter values
    start_date, end_date, draw_type, rolling_window = render_sidebar(df_full)
    
    # Apply filters
    df = filter_by_date_range(df_full, start_date, end_date)
    df = filter_by_draw_type(df, draw_type)
    
    # Show filtered count
    st.sidebar.divider()
    st.sidebar.metric("Filtered Draws", f"{len(df):,}")
    
    # Main content tabs
    tabs = st.tabs([
        "📈 Overview",
        "📊 Frequency",
        "🔍 Patterns",
        "📈 Trends",
        "⭐ Watchlist",
        "🔎 Checker",
        "📁 Data"
    ])
    
    with tabs[0]:
        render_overview_tab(df)
    
    with tabs[1]:
        render_frequency_tab(df)
    
    with tabs[2]:
        render_patterns_tab(df)
    
    with tabs[3]:
        render_trends_tab(df, rolling_window)
    
    with tabs[4]:
        render_watchlist_tab(df_full)  # Watchlist uses full data
    
    with tabs[5]:
        render_checker_tab(df_full)  # Checker uses full data
    
    with tabs[6]:
        render_data_tab(df)
    
    # Footer
    st.divider()
    st.caption("""
    **Disclaimer:** Lottery drawings are completely random. Past results have no influence on future outcomes. 
    This app is for entertainment and educational purposes only. Please play responsibly.
    
    Data Source: [NY Open Data](https://data.ny.gov/) | Dataset ID: hsys-3def
    """)


if __name__ == "__main__":
    main()
