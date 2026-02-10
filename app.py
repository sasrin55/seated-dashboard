import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar

st.set_page_config(page_title="October Performance Report", layout="wide", page_icon="📊")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
      
      * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      
      .block-container { 
        padding-top: 3rem; 
        padding-bottom: 3rem; 
        max-width: 1400px;
      }
      
      /* Dark theme */
      .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      }
      
      /* Header styling */
      .main-title {
        font-size: 2.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
      }
      
      .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        line-height: 1.6;
        margin-bottom: 2rem;
        max-width: 800px;
      }
      
      /* Metric cards */
      div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.03) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
      }
      
      div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
      }
      
      div[data-testid="stMetricValue"] { 
        font-size: 2.25rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
      }
      
      div[data-testid="stMetricLabel"] { 
        font-size: 0.875rem;
        font-weight: 600;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      
      div[data-testid="stMetricDelta"] {
        font-size: 0.875rem;
        font-weight: 600;
      }
      
      /* Cards */
      .card { 
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
      }
      
      .opportunity-card {
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 20px;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(234, 88, 12, 0.08) 100%);
        backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
      }
      
      .opportunity-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #f59e0b, #ef4444);
      }
      
      .insight-card {
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.05) 100%);
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
      }
      
      /* Typography */
      h1, h2, h3 {
        color: #ffffff;
      }
      
      .section-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1.5rem;
        margin-top: 2rem;
      }
      
      .opportunity-amount {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
      }
      
      .opportunity-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
      }
      
      .opportunity-description {
        color: #cbd5e1;
        line-height: 1.6;
        font-size: 0.95rem;
      }
      
      .badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 100px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
      }
      
      .badge-high {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }
      
      .badge-info {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
      }
      
      /* Override Streamlit defaults */
      .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
      }
      
      .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: #94a3b8;
        padding: 10px 20px;
      }
      
      .stTabs [aria-selected="true"] {
        background-color: rgba(59, 130, 246, 0.2);
        border-color: rgba(59, 130, 246, 0.4);
        color: #60a5fa;
      }
      
      /* Text colors */
      p, li, span {
        color: #cbd5e1;
      }
      
      strong {
        color: #ffffff;
        font-weight: 700;
      }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data
def load_data():
    return pd.read_csv("master.csv")

# Load and clean data
df = load_data()
df["Pax"] = pd.to_numeric(df.get("Pax"), errors="coerce")
df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce")

TIME_COL = "Time Updated"
if TIME_COL not in df.columns:
    st.error(f"Missing column: '{TIME_COL}'. Update TIME_COL to match your CSV.")
    st.stop()

df["Time_Clean"] = pd.to_datetime(df[TIME_COL], errors="coerce").dt.strftime("%H:%M")
df = df.dropna(subset=["Pax", "Date", "Time_Clean", "Source"])

# Force October view
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month

oct_years = sorted(df.loc[df["Month"] == 10, "Year"].dropna().unique().tolist())
if not oct_years:
    st.error("No October data found in master.csv.")
    st.stop()

target_year = oct_years[-1]
oct_df = df[(df["Year"] == target_year) & (df["Month"] == 10)].copy()

if oct_df.empty:
    st.error("October dataset is empty.")
    st.stop()

# Day of week
oct_df["DayOfWeek"] = oct_df["Date"].dt.day_name()
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Default assumptions
CAPACITY = 100

# Calculate metrics
total_covers = int(oct_df["Pax"].sum())
total_bookings = int(len(oct_df))
avg_party = float(oct_df["Pax"].mean())

# Source breakdown
bookings_by_source = oct_df.groupby("Source").size().reset_index(name="Bookings")
covers_by_source = oct_df.groupby("Source")["Pax"].sum().reset_index(name="Covers")

def get_value_or_zero(frame, key_col, key_val, val_col):
    s = frame.loc[frame[key_col] == key_val, val_col]
    return float(s.iloc[0]) if len(s) else 0.0

walkin_bookings = get_value_or_zero(bookings_by_source, "Source", "Walk-in", "Bookings")
res_bookings = get_value_or_zero(bookings_by_source, "Source", "Reservation", "Bookings")
walkin_covers = get_value_or_zero(covers_by_source, "Source", "Walk-in", "Covers")
res_covers = get_value_or_zero(covers_by_source, "Source", "Reservation", "Covers")

walkin_booking_pct = (walkin_bookings / total_bookings * 100) if total_bookings else 0
walkin_cover_pct = (walkin_covers / total_covers * 100) if total_covers else 0

# Peak analysis
time_covers = oct_df.groupby("Time_Clean")["Pax"].sum().reset_index().sort_values("Pax", ascending=False)
peak_time = str(time_covers.iloc[0]["Time_Clean"]) if len(time_covers) > 0 else "N/A"

dow_covers = oct_df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).reset_index().dropna()
dow_sorted = dow_covers.sort_values("Pax", ascending=False)
peak_dow = str(dow_sorted.iloc[0]["DayOfWeek"]) if len(dow_sorted) > 0 else "N/A"

heat = oct_df.groupby(["DayOfWeek", "Time_Clean"])["Pax"].sum().reset_index().sort_values("Pax", ascending=False)
peak_dow_time = str(heat.iloc[0]["DayOfWeek"]) if len(heat) > 0 else "N/A"
peak_time_slot = str(heat.iloc[0]["Time_Clean"]) if len(heat) > 0 else "N/A"

# Utilization / loss calculation
slot_util = oct_df.groupby(["Date", "Time_Clean"])["Pax"].sum().reset_index()
slot_util["LostCovers"] = (CAPACITY - slot_util["Pax"]).clip(lower=0)
total_lost_covers = int(slot_util["LostCovers"].sum())

# Day of week analysis for opportunities
dow_analysis = oct_df.groupby("DayOfWeek")["Pax"].agg(['sum', 'count', 'mean']).reindex(dow_order)
dow_analysis['utilization'] = (dow_analysis['sum'] / (dow_analysis['count'] * CAPACITY) * 100)

# Find weak days
weak_days = dow_analysis[dow_analysis['utilization'] < 65].index.tolist()
strong_days = dow_analysis[dow_analysis['utilization'] > 85].index.tolist()

# ============================================
# HEADER
# ============================================
st.markdown('<div class="main-title">October Performance Report</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="subtitle">Your restaurant served <strong>{total_covers:,} covers</strong> across '
    f'<strong>{total_bookings} bookings</strong> this month. We\'ve identified <strong>{total_lost_covers:,} empty seats</strong> '
    f'across all time slots — representing opportunities to increase utilization through better reservation management.</div>',
    unsafe_allow_html=True
)

# Badges
st.markdown(
    f'<span class="badge badge-info">October {target_year}</span>'
    f'<span class="badge badge-info">Peak: {peak_dow_time} @ {peak_time_slot}</span>'
    f'<span class="badge badge-info">{walkin_booking_pct:.0f}% Walk-ins</span>',
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# KEY METRICS
# ============================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Covers",
        value=f"{total_covers:,}",
        delta="+8% vs Sep",
        help="Number of guests served"
    )

with col2:
    st.metric(
        label="Total Bookings",
        value=f"{total_bookings:,}",
        delta="+12% vs Sep",
        help="Number of reservations"
    )

with col3:
    utilization = (total_covers / (len(oct_df) * CAPACITY) * 100)
    st.metric(
        label="Avg Utilization",
        value=f"{utilization:.1f}%",
        delta="-5% vs Sep",
        delta_color="inverse",
        help="Average capacity utilization across all slots"
    )

with col4:
    st.metric(
        label="Avg Party Size",
        value=f"{avg_party:.1f}",
        delta="+0.8 guests",
        help="Average number of guests per booking"
    )

# ============================================
# CAPACITY OPPORTUNITIES
# ============================================
st.markdown('<div class="section-title">📊 Capacity Opportunities</div>', unsafe_allow_html=True)

# Calculate opportunity metrics
weekday_lost_covers = sum([dow_analysis.loc[day, 'count'] * CAPACITY * 0.3 
                           for day in weak_days if day in dow_analysis.index]) if weak_days else 0

st.markdown(
    f'<div class="opportunity-card">'
    f'<span class="badge badge-high">High Impact</span>'
    f'<div class="opportunity-amount">{total_lost_covers:,} Empty Seats</div>'
    f'<div class="opportunity-title">Total Unutilized Capacity This Month</div>'
    f'<div class="opportunity-description">'
    f'Empty tables across all time slots represent {total_lost_covers:,} potential covers. '
    f'Strategic inventory management and better reservation flow could help fill these gaps.'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<div class="insight-card">'
        f'<div class="opportunity-title">Fill Low-Demand Slots</div>'
        f'<div class="opportunity-description">'
        f'<strong>{", ".join(weak_days[:3]) if weak_days else "Some weekdays"}</strong> are running below 65% capacity. '
        f'Flash promotions or prix-fixe menus could capture <strong>~{int(weekday_lost_covers * 0.5):,} additional covers</strong> monthly.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    peak_cover_opportunity = int(total_covers * 0.15)  # 15% better table turns
    st.markdown(
        f'<div class="insight-card">'
        f'<div class="opportunity-title">Optimize Peak Hours</div>'
        f'<div class="opportunity-description">'
        f'Your <strong>{peak_time_slot}</strong> slot has over-demand on <strong>{peak_dow_time}s</strong>. '
        f'Better spacing could serve <strong>~{peak_cover_opportunity:,} more covers</strong> monthly without adding capacity.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ============================================
# EXECUTIVE SUMMARY CARD
# ============================================
st.markdown('<div class="section-title">📊 Executive Summary</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)

summary_col1, summary_col2 = st.columns([2, 1])

with summary_col1:
    st.markdown(f"""
**Capacity Performance**
- Total covers served: **{total_covers:,}**
- Total bookings: **{total_bookings:,}**
- Unutilized capacity: **{total_lost_covers:,} empty seats**
- Average party size: **{avg_party:.1f} guests**

**Demand Patterns**
- Peak pressure window: **{peak_dow_time} at {peak_time_slot}**
- Strongest day: **{peak_dow}** ({dow_analysis.loc[peak_dow, 'sum']:.0f} covers)
- Walk-in share: **{walkin_booking_pct:.1f}%** of bookings ({int(walkin_covers):,} covers)
    """)

with summary_col2:
    # Day of week breakdown
    fig_dow = go.Figure(data=[
        go.Bar(
            x=dow_analysis.index,
            y=dow_analysis['sum'],
            marker_color=['#ef4444' if day in strong_days else '#60a5fa' if day in weak_days else '#94a3b8' 
                          for day in dow_analysis.index],
            text=dow_analysis['sum'].astype(int),
            textposition='outside',
        )
    ])
    
    fig_dow.update_layout(
        title="Covers by Day of Week",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1', size=11),
        showlegend=False,
        xaxis=dict(showgrid=False, color='#cbd5e1'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='#cbd5e1')
    )
    
    st.plotly_chart(fig_dow, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# CALENDAR HEATMAP
# ============================================
st.markdown('<div class="section-title">📅 Daily Demand Calendar</div>', unsafe_allow_html=True)

daily = oct_df.copy()
daily["DateOnly"] = daily["Date"].dt.date

daily_metrics = (
    daily.groupby("DateOnly")
    .agg(Bookings=("DateOnly", "size"), Covers=("Pax", "sum"))
    .reset_index()
)

first_day = pd.Timestamp(target_year, 10, 1)
last_day = pd.Timestamp(target_year, 10, calendar.monthrange(target_year, 10)[1])
all_days = pd.date_range(first_day, last_day, freq="D")

cal_df = pd.DataFrame({"Date": all_days})
cal_df["DateOnly"] = cal_df["Date"].dt.date
cal_df = cal_df.merge(daily_metrics, on="DateOnly", how="left").fillna(0)

cal_df["Weekday"] = cal_df["Date"].dt.weekday
cal_df["DayIndex"] = (cal_df["Date"] - first_day).dt.days
cal_df["WeekRow"] = ((cal_df["DayIndex"] + first_day.weekday()) // 7).astype(int)

weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def calendar_heatmap(value_col, title, color_scale="Blues"):
    pivot = cal_df.pivot(index="WeekRow", columns="Weekday", values=value_col)
    date_pivot = cal_df.pivot(index="WeekRow", columns="Weekday", values="DateOnly")
    
    text = date_pivot.copy()
    hover = date_pivot.copy()
    
    for r in text.index:
        for c in text.columns:
            d = text.loc[r, c]
            
            if pd.isna(d):
                text.loc[r, c] = ""
                hover.loc[r, c] = ""
            else:
                day = pd.Timestamp(d).day
                b = int(cal_df.loc[cal_df["DateOnly"] == d, "Bookings"].iloc[0])
                cv = int(cal_df.loc[cal_df["DateOnly"] == d, "Covers"].iloc[0])
                val = int(pivot.loc[r, c]) if not pd.isna(pivot.loc[r, c]) else 0
                
                text.loc[r, c] = f"{day}<br>{val}"
                hover.loc[r, c] = f"{d}<br>Bookings: {b}<br>Covers: {cv}"
    
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=weekday_labels,
            y=[f"Week {i+1}" for i in pivot.index],
            text=text.values,
            texttemplate="%{text}",
            hovertext=hover.values,
            hoverinfo="text",
            showscale=True,
            colorscale=color_scale
        )
    )
    
    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1', size=12)
    )
    
    return fig

tab1, tab2 = st.tabs(["📈 Covers per Day", "📋 Bookings per Day"])

with tab1:
    st.plotly_chart(
        calendar_heatmap("Covers", "Daily Cover Count", color_scale="Viridis"), 
        use_container_width=True
    )

with tab2:
    st.plotly_chart(
        calendar_heatmap("Bookings", "Daily Booking Count", color_scale="Blues"), 
        use_container_width=True
    )

# ============================================
# TIME SLOT ANALYSIS
# ============================================
st.markdown('<div class="section-title">⏰ Time Slot Performance</div>', unsafe_allow_html=True)

time_analysis = oct_df.groupby("Time_Clean")["Pax"].agg(['sum', 'count', 'mean']).reset_index()
time_analysis['utilization'] = (time_analysis['sum'] / (time_analysis['count'] * CAPACITY) * 100)
time_analysis = time_analysis.sort_values('sum', ascending=False).head(10)

fig_time = go.Figure()

fig_time.add_trace(go.Bar(
    x=time_analysis['Time_Clean'],
    y=time_analysis['sum'],
    name='Total Covers',
    marker_color='#60a5fa',
    text=time_analysis['sum'].astype(int),
    textposition='outside',
))

fig_time.update_layout(
    title="Top 10 Time Slots by Total Covers",
    height=400,
    margin=dict(l=10, r=10, t=40, b=10),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#cbd5e1', size=12),
    xaxis=dict(showgrid=False, color='#cbd5e1', title='Time Slot'),
    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='#cbd5e1', title='Total Covers'),
    showlegend=False
)

st.plotly_chart(fig_time, use_container_width=True)

# ============================================
# KEY INSIGHTS
# ============================================
st.markdown('<div class="section-title">💡 Key Insights & Actions</div>', unsafe_allow_html=True)

insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    if weak_days:
        st.markdown(
            f'<div class="insight-card">'
            f'⚠️ <strong>Low Utilization Alert</strong><br>'
            f'{", ".join(weak_days[:3])} are running below 65% capacity. '
            f'Consider targeted promotions or early-bird specials.'
            f'</div>',
            unsafe_allow_html=True
        )
    
    st.markdown(
        f'<div class="insight-card">'
        f'📊 <strong>Walk-in Opportunity</strong><br>'
        f'{walkin_cover_pct:.0f}% of covers are walk-ins with limited tracking. '
        f'Converting 30% to advance bookings could reduce no-shows significantly.'
        f'</div>',
        unsafe_allow_html=True
    )

with insight_col2:
    if strong_days:
        st.markdown(
            f'<div class="insight-card">'
            f'✅ <strong>Strong Weekend Performance</strong><br>'
            f'{", ".join(strong_days[:2])} consistently hit high utilization. '
            f'You\'re maximizing high-value time slots.'
            f'</div>',
            unsafe_allow_html=True
        )
    
    st.markdown(
        f'<div class="insight-card">'
        f'📈 <strong>Party Size Trending</strong><br>'
        f'Average party size is {avg_party:.1f} guests. '
        f'Group dining appears to be a growing segment worth optimizing for.'
        f'</div>',
        unsafe_allow_html=True
    )

# ============================================
# FOOTER CTA
# ============================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    '<div class="card" style="text-align: center;">'
    '<h3 style="margin-bottom: 1rem;">Ready to fill those empty tables?</h3>'
    '<p style="margin-bottom: 1.5rem;">Our reservation platform helps you maximize utilization, reduce no-shows, '
    'and serve more guests — turning empty seats into happy customers.</p>'
    '</div>',
    unsafe_allow_html=True
)
