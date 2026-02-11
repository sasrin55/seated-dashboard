import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar
from datetime import datetime

st.set_page_config(page_title="Seated Dashboard", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
      * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
      .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1600px; }
      .stApp { background: #f8f9fb; }
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      header {visibility: hidden;}

      .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
      }
      .sub-title {
        color: #6b7280;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 1.5rem;
      }

      div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.03em;
      }
      div[data-testid="stMetricLabel"] {
        font-size: 0.78rem;
        font-weight: 700;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }

      .chart-container {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
      }
      .card-title {
        font-size: 0.8rem;
        font-weight: 800;
        color: #6b7280;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }

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
        padding: 12px 20px;
        font-weight: 700;
        font-size: 0.9rem;
      }
      .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid #2563eb;
        color: #2563eb;
      }
    </style>
    """,
    unsafe_allow_html=True
)

MONTH_FILES = {
    "October 2025": "master_2025_10.csv",
    "November 2025": "master_2025_11.csv",
    "December 2025": "master_2025_12.csv",
}

TIME_COL_CANDIDATES = ["Time Updated", "Time", "Time_Updated"]

@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def find_time_col(df: pd.DataFrame) -> str:
    for c in TIME_COL_CANDIDATES:
        if c in df.columns:
            return c
    return ""

def clean_month_df(df: pd.DataFrame) -> pd.DataFrame:
    needed = ["Date", "Name", "Source", "Pax", "Table"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        st.stop()

    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Pax"] = pd.to_numeric(df["Pax"], errors="coerce")
    df["Name"] = df["Name"].astype(str).str.strip()
    df["Source"] = df["Source"].astype(str).str.strip()

    time_col = find_time_col(df)
    if not time_col:
        st.error("Missing time column. Expected one of: Time Updated, Time, Time_Updated")
        st.stop()

    t = df[time_col].astype(str).str.strip()

    def normalize_time_label(x: str) -> str:
        if not x or x.lower() in ["nan", "none"]:
            return ""
        x = x.replace(".", "").upper()
        x = x.replace("  ", " ")
        return x

    df["Time_Label"] = t.map(normalize_time_label)

    df = df.dropna(subset=["Date", "Pax"])
    df = df[(df["Pax"] > 0)]
    df = df[df["Name"].notna() & (df["Name"].str.len() > 0)]
    df = df[df["Time_Label"].notna() & (df["Time_Label"].str.len() > 0)]
    df = df[df["Source"].notna() & (df["Source"].str.len() > 0)]

    df["DayOfWeek"] = df["Date"].dt.day_name()
    df["DateOnly"] = df["Date"].dt.date

    return df

def month_calendar_df(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    daily_metrics = (
        df.groupby("DateOnly")
        .agg(Bookings=("DateOnly", "size"), Covers=("Pax", "sum"))
        .reset_index()
    )

    first_day = pd.Timestamp(year, month, 1)
    last_day = pd.Timestamp(year, month, calendar.monthrange(year, month)[1])
    all_days = pd.date_range(first_day, last_day, freq="D")

    cal_df = pd.DataFrame({"Date": all_days})
    cal_df["DateOnly"] = cal_df["Date"].dt.date
    cal_df = cal_df.merge(daily_metrics, on="DateOnly", how="left").fillna(0)

    cal_df["Weekday"] = cal_df["Date"].dt.weekday
    cal_df["DayIndex"] = (cal_df["Date"] - first_day).dt.days
    cal_df["WeekRow"] = ((cal_df["DayIndex"] + first_day.weekday()) // 7).astype(int)

    return cal_df

def calendar_heatmap(cal_df: pd.DataFrame, value_col: str, colorscale) -> go.Figure:
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

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
                bookings = int(cal_df.loc[cal_df["DateOnly"] == d, "Bookings"].iloc[0])
                covers = int(cal_df.loc[cal_df["DateOnly"] == d, "Covers"].iloc[0])
                val = int(pivot.loc[r, c]) if not pd.isna(pivot.loc[r, c]) else 0

                text.loc[r, c] = f"{day_num}<br><b>{val}</b>"
                hover.loc[r, c] = f"{d}<br>Bookings: {bookings}<br>Covers: {covers}"

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
            colorscale=colorscale,
        )
    )

    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#6b7280", size=11, family="Inter"),
        xaxis=dict(side="top"),
    )
    return fig

def weekly_view_fig(df: pd.DataFrame, metric: str) -> go.Figure:
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    if metric == "Covers":
        agg = df.groupby(["DayOfWeek", "Time_Label"])["Pax"].sum().reset_index()
        agg.rename(columns={"Pax": "Value"}, inplace=True)
    else:
        agg = df.groupby(["DayOfWeek", "Time_Label"]).size().reset_index(name="Value")

    pivot = agg.pivot(index="Time_Label", columns="DayOfWeek", values="Value").reindex(columns=dow_order).fillna(0)

    # Focus on top 14 time slots for readability
    top_times = agg.groupby("Time_Label")["Value"].sum().sort_values(ascending=False).head(14).index
    pivot = pivot.loc[pivot.index.isin(top_times)]

    # Sort time labels
    def time_sort_key(t: str):
        try:
            return datetime.strptime(t.replace(" ", ""), "%I:%M%p")
        except Exception:
            try:
                return datetime.strptime(t.replace(" ", ""), "%I%p")
            except Exception:
                return datetime.min

    pivot = pivot.reindex(sorted(pivot.index, key=time_sort_key))

    # Clean text values
    z_values = pivot.values
    text_values = [[f'{int(val)}' if val > 0 else '' for val in row] for row in z_values]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=dow_labels,
            y=pivot.index.tolist(),
            colorscale=[[0, "#eff6ff"], [0.5, "#60a5fa"], [1, "#1e40af"]] if metric == "Covers"
                      else [[0, "#f0fdf4"], [0.5, "#34d399"], [1, "#166534"]],
            showscale=False,
            text=text_values,
            texttemplate='%{text}',
            textfont=dict(size=10, family='Inter', color='#1a1d29'),
            hovertemplate="%{y}<br>%{x}<br>Value: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        height=320,
        margin=dict(l=70, r=10, t=10, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#6b7280", size=10, family="Inter"),
        yaxis=dict(autorange="reversed", fixedrange=True),
        xaxis=dict(fixedrange=True)
    )
    return fig

def top_summary(df: pd.DataFrame):
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    busiest_day_covers = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).idxmax()
    busiest_day_bookings = df.groupby("DayOfWeek").size().reindex(dow_order).idxmax()

    busiest_time_covers = df.groupby("Time_Label")["Pax"].sum().sort_values(ascending=False).head(1)
    busiest_time_bookings = df.groupby("Time_Label").size().sort_values(ascending=False).head(1)

    day_time_covers = df.groupby(["DayOfWeek", "Time_Label"])["Pax"].sum().sort_values(ascending=False).head(1)
    day_time_bookings = df.groupby(["DayOfWeek", "Time_Label"]).size().sort_values(ascending=False).head(1)

    return {
        "busiest_day_covers": busiest_day_covers,
        "busiest_day_bookings": busiest_day_bookings,
        "busiest_time_covers": busiest_time_covers.index[0] if len(busiest_time_covers) else "",
        "busiest_time_bookings": busiest_time_bookings.index[0] if len(busiest_time_bookings) else "",
        "busiest_day_time_covers": f"{day_time_covers.index[0][0]} at {day_time_covers.index[0][1]}" if len(day_time_covers) else "",
        "busiest_day_time_bookings": f"{day_time_bookings.index[0][0]} at {day_time_bookings.index[0][1]}" if len(day_time_bookings) else "",
    }

# Main dashboard
st.markdown('<div class="main-title">Seated Performance Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Monthly views for covers, bookings, calendar demand, and busiest patterns</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

month_tabs = st.tabs(list(MONTH_FILES.keys()))

for tab_name, tab in zip(MONTH_FILES.keys(), month_tabs):
    with tab:
        file_path = MONTH_FILES[tab_name]
        raw = load_csv(file_path)
        df = clean_month_df(raw)

        year = int(df["Date"].dt.year.dropna().unique()[-1])
        month = int(df["Date"].dt.month.dropna().unique()[-1])

        total_covers = int(df["Pax"].sum())
        total_bookings = int(len(df))
        avg_party = float(df["Pax"].mean()) if total_bookings else 0.0

        summary = top_summary(df)

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Covers", f"{total_covers:,}")
        with c2:
            st.metric("Total Bookings", f"{total_bookings:,}")
        with c3:
            st.metric("Average Party Size", f"{avg_party:.2f}")
        with c4:
            st.metric("Busiest Day (Covers)", summary["busiest_day_covers"])

        st.markdown("<br>", unsafe_allow_html=True)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Busiest Time (Covers)", summary["busiest_time_covers"])
        with s2:
            st.metric("Busiest Day & Time", summary["busiest_day_time_covers"])
        with s3:
            st.metric("Busiest Day (Bookings)", summary["busiest_day_bookings"])
        with s4:
            st.metric("Busiest Time (Bookings)", summary["busiest_time_bookings"])

        st.markdown("<br>", unsafe_allow_html=True)

        cal_df = month_calendar_df(df, year, month)

        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Calendar View</div>', unsafe_allow_html=True)

        t1, t2 = st.tabs(["Covers", "Bookings"])
        with t1:
            st.plotly_chart(
                calendar_heatmap(cal_df, "Covers", [[0, "#eff6ff"], [0.5, "#3b82f6"], [1, "#1e3a8a"]]),
                use_container_width=True,
                config={'displayModeBar': False}
            )
        with t2:
            st.plotly_chart(
                calendar_heatmap(cal_df, "Bookings", [[0, "#f0fdf4"], [0.5, "#22c55e"], [1, "#166534"]]),
                use_container_width=True,
                config={'displayModeBar': False}
            )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        left, right = st.columns(2)

        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_covers = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order)
        dow_bookings = df.groupby("DayOfWeek").size().reindex(dow_order)

        with left:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Busiest Day of Week</div>', unsafe_allow_html=True)

            fig_dow = go.Figure()
            fig_dow.add_trace(go.Bar(
                x=dow_covers.index,
                y=dow_covers.values,
                marker_color='#3b82f6',
                marker_line_width=0,
                text=dow_covers.fillna(0).astype(int),
                textposition="outside",
                textfont=dict(size=11, color='#6b7280', family='Inter')
            ))
            fig_dow.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=40),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#6b7280", size=11, family="Inter"),
                showlegend=False,
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6", showline=False, zeroline=False),
            )
            st.plotly_chart(fig_dow, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">Reservations vs Walk-ins</div>', unsafe_allow_html=True)

            mix = df.groupby("Source").agg(
                Covers=("Pax", "sum"),
                Bookings=("Source", "size")
            ).reset_index()

            fig_mix = go.Figure()
            fig_mix.add_trace(go.Bar(
                x=mix["Source"],
                y=mix["Bookings"],
                name="Bookings",
                marker_color='#3b82f6'
            ))
            fig_mix.add_trace(go.Bar(
                x=mix["Source"],
                y=mix["Covers"],
                name="Covers",
                marker_color='#8b5cf6'
            ))
            fig_mix.update_layout(
                barmode="group",
                height=320,
                margin=dict(l=10, r=10, t=10, b=40),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#6b7280", size=11, family="Inter"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6", showline=False, zeroline=False),
            )
            st.plotly_chart(fig_mix, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Weekly View</div>', unsafe_allow_html=True)

        w1, w2 = st.tabs(["Covers", "Bookings"])
        with w1:
            st.plotly_chart(weekly_view_fig(df, "Covers"), use_container_width=True, config={'displayModeBar': False})
        with w2:
            st.plotly_chart(weekly_view_fig(df, "Bookings"), use_container_width=True, config={'displayModeBar': False})

        st.markdown("</div>", unsafe_allow_html=True)
