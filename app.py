import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar

st.set_page_config(page_title="Paola's October Reservation Report", layout="centered")

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 920px; }
      div[data-testid="stMetricValue"] { font-size: 1.6rem; }
      div[data-testid="stMetricLabel"] { font-size: 0.95rem; }
      .subtle { color: rgba(49,51,63,0.65); font-size: 0.95rem; }
      .card { border: 1px solid rgba(49,51,63,0.12); border-radius: 16px; padding: 16px 16px; background: white; }
      .title { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.2rem; }
      .section { margin-top: 1.2rem; }
      .pill { display:inline-block; padding: 6px 10px; border-radius: 999px; border: 1px solid rgba(49,51,63,0.14); background: rgba(49,51,63,0.03); font-size: 0.85rem; margin-right: 6px; }
      .tight { margin-top: 0.35rem; }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data
def load_data():
    return pd.read_csv("master.csv")

df = load_data()

# Clean types
df["Pax"] = pd.to_numeric(df.get("Pax"), errors="coerce")
df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce")

TIME_COL = "Time Updated"
if TIME_COL not in df.columns:
    st.error(f"Missing column: '{TIME_COL}'. Update TIME_COL to match your CSV.")
    st.stop()

df["Time_Clean"] = pd.to_datetime(df[TIME_COL], errors="coerce").dt.strftime("%H:%M")
df = df.dropna(subset=["Pax", "Date", "Time_Clean", "Source"])

# Force October view (choose most recent October available)
df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month

oct_years = sorted(df.loc[df["Month"] == 10, "Year"].dropna().unique().tolist())
if not oct_years:
    st.error("No October data found in master.csv.")
    st.stop()

target_year = oct_years[-1]
oct_df = df[(df["Year"] == target_year) & (df["Month"] == 10)].copy()

if oct_df.empty:
    st.error("October dataset is empty after cleaning.")
    st.stop()

# Day of week
oct_df["DayOfWeek"] = oct_df["Date"].dt.day_name()
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Optional Branch filter, only if column exists
branch_choice = "All"
if "Branch" in oct_df.columns:
    branches = ["All"] + sorted([b for b in oct_df["Branch"].dropna().unique().tolist()])
    branch_choice = st.selectbox("Branch", branches, index=0)
    if branch_choice != "All":
        oct_df = oct_df[oct_df["Branch"] == branch_choice]

if oct_df.empty:
    st.title("Paola's October Reservation Report")
    st.write("No data for this selection.")
    st.stop()

# Header
st.markdown('<div class="title">Paola\'s October Reservation Report</div>', unsafe_allow_html=True)

# Report pills
total_covers_preview = int(oct_df["Pax"].sum())
total_bookings_preview = int(len(oct_df))

st.markdown(
    f'<span class="pill">October {target_year}</span>'
    f'<span class="pill">Covers: {total_covers_preview:,}</span>'
    f'<span class="pill">Bookings: {total_bookings_preview:,}</span>'
    + (f'<span class="pill">Branch: {branch_choice}</span>' if branch_choice != "All" else ""),
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtle tight">A simple monthly view of demand, pressure windows, and missed revenue from empty tables.</div>',
    unsafe_allow_html=True
)

# Assumptions (not a sidebar, and not always visible)
with st.expander("Assumptions used in this report", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        AVG_TICKET = st.number_input("Avg ticket (PKR)", min_value=0, value=20000, step=500)
    with c2:
        CAPACITY = st.number_input("Covers capacity per time-slot", min_value=1, value=100, step=10)

# Defaults if expander not touched
if "AVG_TICKET" not in locals():
    AVG_TICKET = 20000
if "CAPACITY" not in locals():
    CAPACITY = 100

# Money layer
oct_df["Revenue"] = oct_df["Pax"] * float(AVG_TICKET)

total_covers = int(oct_df["Pax"].sum())
total_bookings = int(len(oct_df))
avg_party = float(oct_df["Pax"].mean())
total_revenue = int(oct_df["Revenue"].sum())

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

# Peaks
time_covers = oct_df.groupby("Time_Clean")["Pax"].sum().reset_index().sort_values("Pax", ascending=False)
peak_time = str(time_covers.iloc[0]["Time_Clean"])
peak_time_covers = int(time_covers.iloc[0]["Pax"])

dow_covers_full = oct_df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).reset_index().dropna()
dow_sorted = dow_covers_full.sort_values("Pax", ascending=False)
peak_dow = str(dow_sorted.iloc[0]["DayOfWeek"])
peak_dow_covers = int(dow_sorted.iloc[0]["Pax"])

heat = oct_df.groupby(["DayOfWeek", "Time_Clean"])["Pax"].sum().reset_index()
heat_sorted = heat.sort_values("Pax", ascending=False)
peak_dow_time = str(heat_sorted.iloc[0]["DayOfWeek"])
peak_time_slot = str(heat_sorted.iloc[0]["Time_Clean"])
peak_dow_time_covers = int(heat_sorted.iloc[0]["Pax"])

# Utilization + Lost revenue
slot_util = oct_df.groupby(["Date", "Time_Clean"])["Pax"].sum().reset_index()
slot_util["Capacity"] = float(CAPACITY)
slot_util["Utilization"] = (slot_util["Pax"] / slot_util["Capacity"]).clip(0, 1)
slot_util["LostCovers"] = (slot_util["Capacity"] - slot_util["Pax"]).clip(lower=0)
slot_util["LostRevenue"] = slot_util["LostCovers"] * float(AVG_TICKET)
lost_rev = int(slot_util["LostRevenue"].sum())

st.markdown('<div class="section"></div>', unsafe_allow_html=True)

# Executive summary
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Executive Summary")
st.write(
    f"Estimated revenue influenced by tracked covers: Rs. {total_revenue:,}. "
    f"Estimated missed revenue from empty time-slots (capacity model): Rs. {lost_rev:,}. "
    f"Peak pressure window: {peak_dow_time} at {peak_time_slot}. "
    f"Walk-in share: {walkin_booking_pct:.1f}% of bookings and {walkin_cover_pct:.1f}% of covers."
)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section"></div>', unsafe_allow_html=True)

# October Calendar View
st.subheader("October Calendar View")

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
cal_df = cal_df.merge(daily_metrics, on="DateOnly", how="left").fillna({"Bookings": 0, "Covers": 0})

cal_df["Weekday"] = cal_df["Date"].dt.weekday
weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

first_weekday = first_day.weekday()
cal_df["DayIndex"] = (cal_df["Date"] - first_day).dt.days
cal_df["WeekRow"] = ((cal_df["DayIndex"] + first_weekday) // 7).astype(int)

def calendar_heatmap(value_col: str, title: str):
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
                day_num = pd.Timestamp(d).day
                b = int(cal_df.loc[cal_df["DateOnly"] == d, "Bookings"].iloc[0])
                cv = int(cal_df.loc[cal_df["DateOnly"] == d, "Covers"].iloc[0])
                val = int(pivot.loc[r, c]) if not pd.isna(pivot.loc[r, c]) else 0
                text.loc[r, c] = f"{day_num}\n{val}"
                hover.loc[r, c] = f"{d}<br>Bookings: {b:,}<br>Covers: {cv:,}"

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=weekday_labels,
            y=[f"Week {i+1}" for i in pivot.index.tolist()],
            text=text.values,
            texttemplate="%{text}",
            hovertext=hover.values,
            hoverinfo="text",
            showscale=True
        )
    )
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
        xaxis=dict(title=""),
        yaxis=dict(title="", autorange="reversed")
    )
    return fig

tab1, tab2 = st.tabs(["Bookings per day", "Covers per day"])
with tab1:
    st.plotly_chart(calendar_heatmap("Bookings", "Bookings by Day (October)"), use_container_width=True)
with tab2:
    st.plotly_chart(calendar_heatmap("Covers", "Covers by Day (October)"), use_container_width=True)
