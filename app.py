import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Seated Analytics", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("master.csv")

df = load_data()

# Clean types
df["Pax"] = pd.to_numeric(df["Pax"], errors="coerce")

# Date
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Time (use your cleaned column)
TIME_COL = "Time Updated"  # change if your CSV uses a different column name
df["Time_Clean"] = pd.to_datetime(df[TIME_COL], errors="coerce").dt.strftime("%H:%M")

# Remove bad rows
df = df.dropna(subset=["Pax", "Date", "Time_Clean", "Source"])

# Day of week
df["DayOfWeek"] = df["Date"].dt.day_name()

# Sidebar: date range with full default
st.sidebar.title("Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]

st.title("Seated Restaurant Performance Dashboard")
st.caption("Insights from reservation and walk-in data")

# KPI row
total_covers = int(df["Pax"].sum())
total_bookings = int(df.shape[0])
avg_party = round(df["Pax"].mean(), 2)

k1, k2, k3 = st.columns(3)
k1.metric("Total covers", total_covers)
k2.metric("Total bookings", total_bookings)
k3.metric("Average party size", avg_party)

st.divider()

# 1) Busiest time overall (by covers)
st.subheader("Busiest time overall")

time_covers = df.groupby("Time_Clean")["Pax"].sum().reset_index().sort_values("Pax", ascending=False)
busiest_time = time_covers.iloc[0]["Time_Clean"]
busiest_time_covers = int(time_covers.iloc[0]["Pax"])

st.write(f"Peak time: {busiest_time} with {busiest_time_covers} total covers in the selected range.")

fig_time = px.bar(
    time_covers.sort_values("Time_Clean"),
    x="Time_Clean",
    y="Pax",
    labels={"Time_Clean": "Time", "Pax": "Total covers"}
)
st.plotly_chart(fig_time, use_container_width=True)

st.divider()

# 2) Busiest day of week overall (by covers)
st.subheader("Busiest day of week overall")

dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow_covers = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).reset_index()
dow_covers = dow_covers.dropna()

busiest_dow_row = dow_covers.sort_values("Pax", ascending=False).iloc[0]
busiest_dow = busiest_dow_row["DayOfWeek"]
busiest_dow_covers = int(busiest_dow_row["Pax"])

st.write(f"Peak day: {busiest_dow} with {busiest_dow_covers} total covers in the selected range.")

fig_dow = px.bar(
    dow_covers,
    x="DayOfWeek",
    y="Pax",
    labels={"DayOfWeek": "Day of week", "Pax": "Total covers"},
    category_orders={"DayOfWeek": dow_order}
)
st.plotly_chart(fig_dow, use_container_width=True)

st.divider()

# 3) Busiest day x time (heatmap by covers)
st.subheader("Busiest day and time")

heat = df.groupby(["DayOfWeek", "Time_Clean"])["Pax"].sum().reset_index()

fig_heat = px.density_heatmap(
    heat,
    x="Time_Clean",
    y="DayOfWeek",
    z="Pax",
    category_orders={"DayOfWeek": dow_order},
    labels={"Time_Clean": "Time", "DayOfWeek": "Day of week", "Pax": "Total covers"}
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# 4) Reservations vs walk-in
st.subheader("Reservations vs walk-in")

col_a, col_b = st.columns(2)

bookings_by_source = df.groupby("Source").size().reset_index(name="Bookings").sort_values("Bookings", ascending=False)
covers_by_source = df.groupby("Source")["Pax"].sum().reset_index(name="Covers").sort_values("Covers", ascending=False)

with col_a:
    st.write("Bookings (count of entries)")
    fig_bookings = px.bar(
        bookings_by_source,
        x="Source",
        y="Bookings",
        labels={"Source": "Source", "Bookings": "Bookings"}
    )
    st.plotly_chart(fig_bookings, use_container_width=True)

with col_b:
    st.write("Covers (sum of Pax)")
    fig_covers = px.bar(
        covers_by_source,
        x="Source",
        y="Covers",
        labels={"Source": "Source", "Covers": "Covers"}
    )
    st.plotly_chart(fig_covers, use_container_width=True)

with st.expander("View filtered data"):
    out = df.copy()
    out["Date"] = out["Date"].dt.date
    st.dataframe(out, use_container_width=True)
