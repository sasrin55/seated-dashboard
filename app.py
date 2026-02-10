import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Seated Analytics",
    layout="wide"
)

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("master.csv")

df = load_data()

# -----------------------------
# Clean Columns
# -----------------------------

# Convert Pax to number
df["Pax"] = pd.to_numeric(df["Pax"], errors="coerce")

# Change this if your time column name is different
TIME_COL = "Time Updated"

df["Time_Clean"] = pd.to_datetime(
    df[TIME_COL],
    errors="coerce"
).dt.strftime("%H:%M")

# Remove bad rows
df = df.dropna(subset=["Pax", "Time_Clean", "Source", "Date"])

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.title("Filters")

dates = sorted(df["Date"].unique())

selected_dates = st.sidebar.multiselect(
    "Select Dates",
    dates,
    default=dates
)

df = df[df["Date"].isin(selected_dates)]

# -----------------------------
# Header
# -----------------------------
st.title("📊 Seated – Restaurant Performance Dashboard")

st.markdown("Real-time insights from reservation and walk-in data")

# -----------------------------
# KPI Row
# -----------------------------
total_covers = int(df["Pax"].sum())
total_bookings = len(df)
avg_party = round(df["Pax"].mean(), 2)
walkin_share = round(
    (df[df["Source"]=="Walk-in"].shape[0] / len(df)) * 100,
    1
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Covers", total_covers)
c2.metric("Total Bookings", total_bookings)
c3.metric("Avg Party Size", avg_party)
c4.metric("Walk-in %", f"{walkin_share}%")

# -----------------------------
# Walk-in vs Reservation
# -----------------------------
st.subheader("Walk-in vs Reservation Mix")

source_df = df.groupby("Source").size().reset_index(name="Bookings")

fig1 = px.pie(
    source_df,
    names="Source",
    values="Bookings",
    hole=0.45
)

st.plotly_chart(fig1, use_container_width=True)

# -----------------------------
# Busiest Times
# -----------------------------
st.subheader("Busiest Times (Total Covers)")

busy = df.groupby("Time_Clean")["Pax"].sum().reset_index()

fig2 = px.bar(
    busy,
    x="Time_Clean",
    y="Pax",
    labels={"Pax":"Total Covers","Time_Clean":"Time"},
)

st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# Walk-in vs Reservation by Time
# -----------------------------
st.subheader("Demand by Time & Source")

time_source = (
    df.groupby(["Time_Clean","Source"])
      .size()
      .reset_index(name="Count")
)

fig3 = px.bar(
    time_source,
    x="Time_Clean",
    y="Count",
    color="Source",
    barmode="group"
)

st.plotly_chart(fig3, use_container_width=True)

# -----------------------------
# Avg Reservation Table Size
# -----------------------------
st.subheader("Average Table Size (Advance Reservations)")

res_df = df[df["Source"]=="Reservation"]

avg_res = (
    res_df.groupby("Time_Clean")["Pax"]
          .mean()
          .reset_index()
)

fig4 = px.line(
    avg_res,
    x="Time_Clean",
    y="Pax",
    markers=True,
    labels={"Pax":"Avg Guests","Time_Clean":"Time"}
)

st.plotly_chart(fig4, use_container_width=True)

# -----------------------------
# Daily Covers Trend
# -----------------------------
st.subheader("Daily Covers Trend")

daily = df.groupby("Date")["Pax"].sum().reset_index()

fig5 = px.line(
    daily,
    x="Date",
    y="Pax",
    markers=True
)

st.plotly_chart(fig5, use_container_width=True)

# -----------------------------
# Raw Data
# -----------------------------
with st.expander("View Raw Data"):
    st.dataframe(df, use_container_width=True)
