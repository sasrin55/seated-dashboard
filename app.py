import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Seated Analytics", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("master.csv")

df = load_data()

# Clean types
df["Pax"] = pd.to_numeric(df["Pax"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

TIME_COL = "Time Updated"  # change only if your CSV uses a different name
df["Time_Clean"] = pd.to_datetime(df[TIME_COL], errors="coerce").dt.strftime("%H:%M")

df = df.dropna(subset=["Pax", "Date", "Time_Clean", "Source"])

# Day of week
df["DayOfWeek"] = df["Date"].dt.day_name()

dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Sidebar filter: date range defaults to full coverage
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

# Guard
if df.empty:
    st.title("Seated Restaurant Performance Dashboard")
    st.write("No data in the selected date range.")
    st.stop()

st.title("Seated Restaurant Performance Dashboard")
st.caption("Clear answers to the four questions you care about")

# Core totals
total_covers = int(df["Pax"].sum())
total_bookings = int(len(df))
avg_party = float(df["Pax"].mean())

# Source breakdown
bookings_by_source = df.groupby("Source").size().reset_index(name="Bookings")
covers_by_source = df.groupby("Source")["Pax"].sum().reset_index(name="Covers")

def get_value_or_zero(frame, key_col, key_val, val_col):
    s = frame.loc[frame[key_col] == key_val, val_col]
    return float(s.iloc[0]) if len(s) else 0.0

walkin_bookings = get_value_or_zero(bookings_by_source, "Source", "Walk-in", "Bookings")
res_bookings = get_value_or_zero(bookings_by_source, "Source", "Reservation", "Bookings")
walkin_covers = get_value_or_zero(covers_by_source, "Source", "Walk-in", "Covers")
res_covers = get_value_or_zero(covers_by_source, "Source", "Reservation", "Covers")

walkin_booking_pct = (walkin_bookings / total_bookings * 100) if total_bookings else 0
walkin_cover_pct = (walkin_covers / total_covers * 100) if total_covers else 0

# Busiest time overall by covers
time_covers = df.groupby("Time_Clean")["Pax"].sum().reset_index()
time_covers = time_covers.sort_values("Pax", ascending=False)

peak_time = str(time_covers.iloc[0]["Time_Clean"])
peak_time_covers = int(time_covers.iloc[0]["Pax"])

# Busiest day of week overall by covers
dow_covers = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).reset_index()
dow_covers = dow_covers.dropna()
dow_covers = dow_covers.sort_values("Pax", ascending=False)

peak_dow = str(dow_covers.iloc[0]["DayOfWeek"])
peak_dow_covers = int(dow_covers.iloc[0]["Pax"])

# Busiest day and time by covers
heat = df.groupby(["DayOfWeek", "Time_Clean"])["Pax"].sum().reset_index()
heat_sorted = heat.sort_values("Pax", ascending=False)
peak_dow_time = str(heat_sorted.iloc[0]["DayOfWeek"])
peak_time_slot = str(heat_sorted.iloc[0]["Time_Clean"])
peak_dow_time_covers = int(heat_sorted.iloc[0]["Pax"])

# Reservation avg party size
res_only = df[df["Source"] == "Reservation"]
avg_res_party = float(res_only["Pax"].mean()) if not res_only.empty else 0.0

# Summary block
st.subheader("Summary")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Total covers", total_covers)
s2.metric("Total bookings", total_bookings)
s3.metric("Average party size", round(avg_party, 2))
s4.metric("Walk in share of bookings", f"{walkin_booking_pct:.1f}%")

st.write(
    f"Peak time overall is {peak_time} with {peak_time_covers} covers. "
    f"Peak day of week is {peak_dow} with {peak_dow_covers} covers. "
    f"Peak day and time is {peak_dow_time} at {peak_time_slot} with {peak_dow_time_covers} covers. "
    f"Walk in share is {walkin_booking_pct:.1f}% of bookings and {walkin_cover_pct:.1f}% of covers. "
    f"Average party size for reservations is {avg_res_party:.2f}."
)

st.divider()

# Section 1: Reservations vs walk in
st.subheader("Reservations vs walk in")

left, right = st.columns(2)

mix_table = pd.DataFrame(
    [
        ["Reservation", int(res_bookings), int(res_covers)],
        ["Walk-in", int(walkin_bookings), int(walkin_covers)],
    ],
    columns=["Source", "Bookings", "Covers"]
)

mix_table["Bookings share"] = (mix_table["Bookings"] / mix_table["Bookings"].sum() * 100).round(1).astype(str) + "%"
mix_table["Covers share"] = (mix_table["Covers"] / mix_table["Covers"].sum() * 100).round(1).astype(str) + "%"

with left:
    st.write("Quick breakdown")
    st.dataframe(mix_table, use_container_width=True, hide_index=True)

with right:
    chart_mode = st.radio("Show", ["Bookings", "Covers"], horizontal=True)
    if chart_mode == "Bookings":
        fig_mix = px.bar(
            bookings_by_source.sort_values("Bookings", ascending=False),
            x="Source",
            y="Bookings",
            text="Bookings",
            labels={"Source": "Source", "Bookings": "Bookings"}
        )
        fig_mix.update_traces(textposition="outside", cliponaxis=False)
    else:
        fig_mix = px.bar(
            covers_by_source.sort_values("Covers", ascending=False),
            x="Source",
            y="Covers",
            text="Covers",
            labels={"Source": "Source", "Covers": "Covers"}
        )
        fig_mix.update_traces(textposition="outside", cliponaxis=False)

    st.plotly_chart(fig_mix, use_container_width=True)

st.divider()

# Section 2: Busiest time overall
st.subheader("Busiest time overall")

top_n = st.slider("How many time slots to show", min_value=5, max_value=20, value=10)

time_top = time_covers.head(top_n).sort_values("Pax", ascending=True)

fig_time = px.bar(
    time_top,
    x="Pax",
    y="Time_Clean",
    orientation="h",
    labels={"Time_Clean": "Time", "Pax": "Total covers"}
)
st.plotly_chart(fig_time, use_container_width=True)

st.divider()

# Section 3: Busiest day of week overall
st.subheader("Busiest day of week overall")

dow_covers_full = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).reset_index()
dow_covers_full = dow_covers_full.dropna()

fig_dow = px.bar(
    dow_covers_full,
    x="DayOfWeek",
    y="Pax",
    labels={"DayOfWeek": "Day of week", "Pax": "Total covers"},
    category_orders={"DayOfWeek": dow_order}
)
st.plotly_chart(fig_dow, use_container_width=True)

st.divider()

# Section 4: Busiest day and time heatmap
st.subheader("Busiest day and time")

heat_for_plot = heat.copy()
heat_for_plot["DayOfWeek"] = pd.Categorical(heat_for_plot["DayOfWeek"], categories=dow_order, ordered=True)

fig_heat = px.density_heatmap(
    heat_for_plot,
    x="Time_Clean",
    y="DayOfWeek",
    z="Pax",
    category_orders={"DayOfWeek": dow_order},
    labels={"Time_Clean": "Time", "DayOfWeek": "Day of week", "Pax": "Total covers"}
)
st.plotly_chart(fig_heat, use_container_width=True)

with st.expander("View filtered rows"):
    view_df = df.copy()
    view_df["Date"] = view_df["Date"].dt.date
    st.dataframe(view_df, use_container_width=True)

