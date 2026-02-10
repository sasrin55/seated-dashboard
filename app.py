import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar

st.set_page_config(page_title="October Analytics", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      
      * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      
      .block-container { 
        padding-top: 2rem; 
        padding-bottom: 2rem; 
        max-width: 1600px;
      }
      
      /* Light clean theme */
      .stApp {
        background: #f8f9fb;
      }
      
      /* Hide Streamlit branding */
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      header {visibility: hidden;}
      
      /* Header styling - minimal */
      .main-title {
        font-size: 2rem;
        font-weight: 600;
        color: #1a1d29;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
      }
      
      .date-range {
        color: #6b7280;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 2rem;
      }
      
      /* Metric cards - clean and simple */
      div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      
      div[data-testid="stMetricValue"] { 
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1d29;
        letter-spacing: -0.03em;
      }
      
      div[data-testid="stMetricLabel"] { 
        font-size: 0.8rem;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      
      div[data-testid="stMetricDelta"] {
        font-size: 0.85rem;
        font-weight: 600;
      }
      
      /* Chart containers */
      .chart-container {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
      }
      
      .card-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 1.25rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      
      /* Override Streamlit tabs */
      .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: transparent;
        border-bottom: 1px solid #e5e7eb;
      }
      
      .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: #6b7280;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 0.9rem;
      }
      
      .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid #3b82f6;
        color: #3b82f6;
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
    st.error(f"Missing column: '{TIME_COL}'")
    st.stop()

df["Time_Clean"] = pd.to_datetime(df[TIME_COL], errors="coerce").dt.strftime("%H:%M")
df = df.dropna(subset=["Pax", "Date", "Time_Clean", "Source"])

# Force October view
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month

oct_years = sorted(df.loc[df["Month"] == 10, "Year"].dropna().unique().tolist())
if not oct_years:
    st.error("No October data found")
    st.stop()

target_year = oct_years[-1]
oct_df = df[(df["Year"] == target_year) & (df["Month"] == 10)].copy()

if oct_df.empty:
    st.error("October dataset is empty")
    st.stop()

# Day of week
oct_df["DayOfWeek"] = oct_df["Date"].dt.day_name()
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Calculate metrics
CAPACITY = 100
total_covers = int(oct_df["Pax"].sum())
total_bookings = int(len(oct_df))
avg_party = float(oct_df["Pax"].mean())
utilization = (total_covers / (len(oct_df) * CAPACITY) * 100)

# ============================================
# HEADER
# ============================================
st.markdown('<div class="main-title">October 2025</div>', unsafe_allow_html=True)
st.markdown('<div class="date-range">Monthly Overview</div>', unsafe_allow_html=True)

# ============================================
# KEY METRICS
# ============================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Covers", value=f"{total_covers:,}", delta="+8%")

with col2:
    st.metric(label="Bookings", value=f"{total_bookings:,}", delta="+12%")

with col3:
    st.metric(label="Utilization", value=f"{utilization:.1f}%", delta="-5%", delta_color="inverse")

with col4:
    st.metric(label="Avg Party", value=f"{avg_party:.1f}", delta="+0.8")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# CALENDAR HEATMAP
# ============================================
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

def calendar_heatmap(value_col, color_scale):
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
                
                text.loc[r, c] = f"{day}<br><b>{val}</b>"
                hover.loc[r, c] = f"{d}<br>Bookings: {b}<br>Covers: {cv}"
    
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=weekday_labels,
            y=[f"W{i+1}" for i in pivot.index],
            text=text.values,
            texttemplate="%{text}",
            hovertext=hover.values,
            hoverinfo="text",
            showscale=False,
            colorscale=color_scale
        )
    )
    
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='#6b7280', size=11, family='Inter'),
        xaxis=dict(side='top')
    )
    
    return fig

st.markdown('<div class="chart-container">', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Covers", "Bookings"])

with tab1:
    st.plotly_chart(
        calendar_heatmap("Covers", [[0, '#eff6ff'], [0.5, '#3b82f6'], [1, '#1e3a8a']]), 
        use_container_width=True
    )

with tab2:
    st.plotly_chart(
        calendar_heatmap("Bookings", [[0, '#f0fdf4'], [0.5, '#22c55e'], [1, '#166534']]), 
        use_container_width=True
    )

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# CHARTS ROW
# ============================================
chart_col1, chart_col2 = st.columns(2)

# Day of week analysis
dow_analysis = oct_df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order)

with chart_col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Day of Week</div>', unsafe_allow_html=True)
    
    fig_dow = go.Figure(data=[
        go.Bar(
            x=dow_analysis.index,
            y=dow_analysis.values,
            marker_color='#3b82f6',
            marker_line_width=0,
            text=dow_analysis.values.astype(int),
            textposition='outside',
            textfont=dict(size=11, color='#6b7280', family='Inter')
        )
    ])
    
    fig_dow.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='#6b7280', size=11, family='Inter'),
        showlegend=False,
        xaxis=dict(showgrid=False, showline=False, color='#9ca3af'),
        yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False, color='#9ca3af', zeroline=False)
    )
    
    st.plotly_chart(fig_dow, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with chart_col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Week View - Demand by Time Slot</div>', unsafe_allow_html=True)
    
    # Create heatmap of day of week vs time slot
    week_heatmap_data = oct_df.groupby(["DayOfWeek", "Time_Clean"])["Pax"].sum().reset_index()
    week_pivot = week_heatmap_data.pivot(index="Time_Clean", columns="DayOfWeek", values="Pax")
    week_pivot = week_pivot.reindex(columns=dow_order)
    
    # Get top time slots
    top_times = week_heatmap_data.groupby("Time_Clean")["Pax"].sum().nlargest(12).index
    week_pivot_filtered = week_pivot.loc[week_pivot.index.isin(top_times)]
    
    fig_week = go.Figure(data=go.Heatmap(
        z=week_pivot_filtered.values,
        x=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        y=week_pivot_filtered.index,
        colorscale=[[0, '#eff6ff'], [0.5, '#60a5fa'], [1, '#1e40af']],
        showscale=False,
        text=week_pivot_filtered.values.astype(int),
        texttemplate='%{text}',
        textfont=dict(size=10, family='Inter'),
        hovertemplate='%{y}<br>%{x}<br>Covers: %{z}<extra></extra>'
    ))
    
    fig_week.update_layout(
        height=280,
        margin=dict(l=60, r=10, t=10, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='#6b7280', size=10, family='Inter'),
        xaxis=dict(side='bottom'),
        yaxis=dict(autorange='reversed')
    )
    
    st.plotly_chart(fig_week, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# TIME SLOTS
# ============================================
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Peak Hours</div>', unsafe_allow_html=True)

time_analysis = oct_df.groupby("Time_Clean")["Pax"].sum().reset_index()
time_analysis = time_analysis.sort_values('Pax', ascending=False).head(8)

fig_time = go.Figure()

fig_time.add_trace(go.Bar(
    x=time_analysis['Time_Clean'],
    y=time_analysis['Pax'],
    marker_color='#3b82f6',
    marker_line_width=0,
    text=time_analysis['Pax'].astype(int),
    textposition='outside',
    textfont=dict(size=11, color='#6b7280', family='Inter')
))

fig_time.update_layout(
    height=300,
    margin=dict(l=10, r=10, t=10, b=40),
    paper_bgcolor='white',
    plot_bgcolor='white',
    font=dict(color='#6b7280', size=11, family='Inter'),
    xaxis=dict(showgrid=False, showline=False, color='#9ca3af', title=None),
    yaxis=dict(showgrid=True, gridcolor='#f3f4f6', showline=False, color='#9ca3af', zeroline=False, title=None),
    showlegend=False
)

st.plotly_chart(fig_time, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
