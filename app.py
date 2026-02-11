import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar
from datetime import datetime
import json
from openai import OpenAI

st.set_page_config(page_title="Seated Dashboard", layout="wide")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
      }
      div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.03em;
        line-height: 1.2;
        word-wrap: break-word;
        overflow-wrap: break-word;
      }
      div[data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        font-weight: 700;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        line-height: 1.3;
        margin-bottom: 0.5rem;
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
    needed = ["Date", "Name", "Source", "Pax"]
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

    # Focus on top 10 time slots for better readability
    top_times = agg.groupby("Time_Label")["Value"].sum().sort_values(ascending=False).head(10).index
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

    # Clean text values - only show if > 50 to reduce clutter
    z_values = pivot.values
    text_values = [[f'{int(val)}' if val > 50 else '' for val in row] for row in z_values]

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
            textfont=dict(size=11, family='Inter', color='#1a1d29', weight=600),
            hovertemplate="%{y}<br>%{x}<br>" + metric + ": %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        height=380,
        margin=dict(l=80, r=10, t=10, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#6b7280", size=11, family="Inter"),
        yaxis=dict(autorange="reversed", fixedrange=True),
        xaxis=dict(fixedrange=True)
    )
    return fig

def top_summary(df: pd.DataFrame):
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Busiest day by covers
    day_covers = df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order)
    busiest_day_covers = day_covers.idxmax()
    busiest_day_covers_count = int(day_covers.max())
    
    # Busiest day by bookings
    day_bookings = df.groupby("DayOfWeek").size().reindex(dow_order)
    busiest_day_bookings = day_bookings.idxmax()
    busiest_day_bookings_count = int(day_bookings.max())

    # Busiest time by covers
    time_covers = df.groupby("Time_Label")["Pax"].sum().sort_values(ascending=False)
    busiest_time_covers = time_covers.index[0] if len(time_covers) else ""
    busiest_time_covers_count = int(time_covers.iloc[0]) if len(time_covers) else 0
    
    # Busiest time by bookings
    time_bookings = df.groupby("Time_Label").size().sort_values(ascending=False)
    busiest_time_bookings = time_bookings.index[0] if len(time_bookings) else ""
    busiest_time_bookings_count = int(time_bookings.iloc[0]) if len(time_bookings) else 0

    # Busiest day+time by covers
    day_time_covers = df.groupby(["DayOfWeek", "Time_Label"])["Pax"].sum().sort_values(ascending=False)
    if len(day_time_covers) > 0:
        peak_dow, peak_time = day_time_covers.index[0]
        peak_covers_count = int(day_time_covers.iloc[0])
        busiest_day_time_covers = f"{peak_dow} @ {peak_time}"
    else:
        busiest_day_time_covers = ""
        peak_covers_count = 0
    
    # Busiest day+time by bookings
    day_time_bookings = df.groupby(["DayOfWeek", "Time_Label"]).size().sort_values(ascending=False)
    if len(day_time_bookings) > 0:
        peak_dow_b, peak_time_b = day_time_bookings.index[0]
        peak_bookings_count = int(day_time_bookings.iloc[0])
        busiest_day_time_bookings = f"{peak_dow_b} @ {peak_time_b}"
    else:
        busiest_day_time_bookings = ""
        peak_bookings_count = 0

    return {
        "busiest_day_covers": busiest_day_covers,
        "busiest_day_covers_count": busiest_day_covers_count,
        "busiest_day_bookings": busiest_day_bookings,
        "busiest_day_bookings_count": busiest_day_bookings_count,
        "busiest_time_covers": busiest_time_covers,
        "busiest_time_covers_count": busiest_time_covers_count,
        "busiest_time_bookings": busiest_time_bookings,
        "busiest_time_bookings_count": busiest_time_bookings_count,
        "busiest_day_time_covers": busiest_day_time_covers,
        "busiest_day_time_covers_count": peak_covers_count,
        "busiest_day_time_bookings": busiest_day_time_bookings,
        "busiest_day_time_bookings_count": peak_bookings_count,
    }

# Chat analytics functions using OpenAI
def get_data_summary(df: pd.DataFrame) -> dict:
    """Generate a summary of the dataset for context"""
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    summary = {
        "total_covers": int(df["Pax"].sum()),
        "total_bookings": int(len(df)),
        "avg_party_size": float(df["Pax"].mean()),
        "date_range": f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}",
        "sources": df["Source"].value_counts().to_dict(),
        "busiest_day": df.groupby("DayOfWeek")["Pax"].sum().reindex(dow_order).idxmax(),
        "busiest_time": df.groupby("Time_Label")["Pax"].sum().sort_values(ascending=False).index[0],
        "unique_tables": df["Table"].nunique(),
    }
    return summary

def run_analytics_with_ai(df: pd.DataFrame, question: str) -> str:
    """Use OpenAI to answer questions about the data"""
    
    # Get data summary for context
    summary = get_data_summary(df)
    
    # Prepare data samples for the AI
    # Top days by covers
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_stats = df.groupby("DayOfWeek").agg(
        Covers=("Pax", "sum"),
        Bookings=("DayOfWeek", "size")
    ).reindex(dow_order).to_dict()
    
    # Top times by covers
    time_stats = df.groupby("Time_Label").agg(
        Covers=("Pax", "sum"),
        Bookings=("Time_Label", "size")
    ).sort_values("Covers", ascending=False).head(10).to_dict()
    
    # Source breakdown
    source_stats = df.groupby("Source").agg(
        Covers=("Pax", "sum"),
        Bookings=("Source", "size")
    ).to_dict()
    
    # Top tables
    table_stats = df.groupby("Table").size().sort_values(ascending=False).head(10).to_dict()
    
    # Create context for OpenAI
    context = f"""
You are analyzing restaurant reservation data. Answer the user's question using ONLY the data provided below.

Dataset Summary:
- Total Covers: {summary['total_covers']:,}
- Total Bookings: {summary['total_bookings']:,}
- Average Party Size: {summary['avg_party_size']:.2f}
- Date Range: {summary['date_range']}
- Busiest Day: {summary['busiest_day']}
- Busiest Time: {summary['busiest_time']}

Day of Week Statistics (Covers):
{json.dumps(day_stats['Covers'], indent=2)}

Day of Week Statistics (Bookings):
{json.dumps(day_stats['Bookings'], indent=2)}

Top Time Slots by Covers:
{json.dumps(time_stats['Covers'], indent=2)}

Source Breakdown (Covers):
{json.dumps(source_stats['Covers'], indent=2)}

Source Breakdown (Bookings):
{json.dumps(source_stats['Bookings'], indent=2)}

Top Tables by Usage:
{json.dumps(table_stats, indent=2)}

Instructions:
- Answer clearly and concisely
- Use specific numbers from the data
- Format large numbers with commas (e.g., 1,234)
- Use markdown formatting for emphasis
- If the data doesn't contain the answer, say so
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}\n\nPlease try rephrasing your question."

@st.cache_data
def load_all_months(month_files: dict) -> pd.DataFrame:
    """Load and combine all monthly CSV files"""
    frames = []
    for file_path in month_files.values():
        frames.append(clean_month_df(load_csv(file_path)))
    return pd.concat(frames, ignore_index=True)

# Main dashboard
st.markdown('<div class="main-title">Seated Performance Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Monthly views for covers, bookings, calendar demand, and busiest patterns</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Add Chat to the tabs
month_tabs = st.tabs(list(MONTH_FILES.keys()) + ["Chat"])

for tab_name, tab in zip(MONTH_FILES.keys(), month_tabs[:-1]):
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
            st.metric(
                "Busiest Day (Covers)", 
                summary["busiest_day_covers"],
                delta=f"{summary['busiest_day_covers_count']:,} covers"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric(
                "Busiest Time (Covers)", 
                summary["busiest_time_covers"],
                delta=f"{summary['busiest_time_covers_count']:,} covers"
            )
        with s2:
            st.metric(
                "Peak Slot", 
                summary["busiest_day_time_covers"],
                delta=f"{summary['busiest_day_time_covers_count']:,} covers"
            )
        with s3:
            st.metric(
                "Busiest Day (Bookings)", 
                summary["busiest_day_bookings"],
                delta=f"{summary['busiest_day_bookings_count']:,} bookings"
            )
        with s4:
            st.metric(
                "Busiest Time (Bookings)", 
                summary["busiest_time_bookings"],
                delta=f"{summary['busiest_time_bookings_count']:,} bookings"
            )

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

        # Just show Walk-ins vs Reservations chart (removing Busiest Day of Week)
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Walk-ins vs Reservations</div>', unsafe_allow_html=True)

        # Get total covers by source, removing any invalid values
        source_totals = df[df["Source"].notna() & (df["Source"].str.strip().str.len() > 0)].groupby("Source")["Pax"].sum().reset_index()
        source_totals.columns = ["Source", "Covers"]
        
        # Filter out 'nan' strings
        source_totals = source_totals[source_totals["Source"].str.lower() != 'nan']

        fig_mix = go.Figure(data=[
            go.Bar(
                x=source_totals["Source"],
                y=source_totals["Covers"],
                marker_color='#3b82f6',
                marker_line_width=0,
                text=source_totals["Covers"].astype(int),
                textposition="outside",
                textfont=dict(size=11, color='#6b7280', family='Inter')
            )
        ])
        
        fig_mix.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=40),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#6b7280", size=11, family="Inter"),
            showlegend=False,
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor="#f3f4f6", showline=False, zeroline=False, title="Total Covers"),
        )
        st.plotly_chart(fig_mix, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Source Analysis Section
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Source Analysis - Walk-ins vs Reservations</div>', unsafe_allow_html=True)
        
        source_col1, source_col2 = st.columns(2)
        
        # Clean dataframe to remove nan sources
        df_clean = df[df["Source"].notna() & (df["Source"].str.strip().str.len() > 0)].copy()
        df_clean = df_clean[df_clean["Source"].str.lower() != 'nan']
        
        # Walk-ins vs Reservations by Day of Week
        with source_col1:
            source_dow = df_clean.groupby(["DayOfWeek", "Source"])["Pax"].sum().reset_index()
            source_dow_pivot = source_dow.pivot(index="DayOfWeek", columns="Source", values="Pax").reindex(dow_order).fillna(0)
            
            fig_source_dow = go.Figure()
            
            for source in source_dow_pivot.columns:
                fig_source_dow.add_trace(go.Bar(
                    x=source_dow_pivot.index,
                    y=source_dow_pivot[source],
                    name=source,
                    marker_color='#3b82f6' if source == 'Reservation' else '#f59e0b',
                    text=source_dow_pivot[source].astype(int),
                    textposition="inside",
                    textfont=dict(size=10, color='white', family='Inter')
                ))
            
            fig_source_dow.update_layout(
                title=dict(text="Covers by Day of Week", font=dict(size=13, color='#6b7280')),
                barmode="stack",
                height=300,
                margin=dict(l=10, r=10, t=40, b=40),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#6b7280", size=10, family="Inter"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6", showline=False, zeroline=False),
            )
            
            st.plotly_chart(fig_source_dow, use_container_width=True, config={'displayModeBar': False})
        
        # Walk-ins vs Reservations by Time
        with source_col2:
            source_time = df_clean.groupby(["Time_Label", "Source"])["Pax"].sum().reset_index()
            top_times_source = source_time.groupby("Time_Label")["Pax"].sum().sort_values(ascending=False).head(10).index
            source_time_filtered = source_time[source_time["Time_Label"].isin(top_times_source)]
            
            source_time_pivot = source_time_filtered.pivot(index="Time_Label", columns="Source", values="Pax").fillna(0)
            
            # Sort by time
            def time_sort_key(t: str):
                try:
                    return datetime.strptime(t.replace(" ", ""), "%I:%M%p")
                except Exception:
                    try:
                        return datetime.strptime(t.replace(" ", ""), "%I%p")
                    except Exception:
                        return datetime.min
            
            source_time_pivot = source_time_pivot.reindex(sorted(source_time_pivot.index, key=time_sort_key))
            
            fig_source_time = go.Figure()
            
            for source in source_time_pivot.columns:
                fig_source_time.add_trace(go.Bar(
                    x=source_time_pivot.index,
                    y=source_time_pivot[source],
                    name=source,
                    marker_color='#3b82f6' if source == 'Reservation' else '#f59e0b',
                    text=source_time_pivot[source].astype(int),
                    textposition="inside",
                    textfont=dict(size=10, color='white', family='Inter')
                ))
            
            fig_source_time.update_layout(
                title=dict(text="Covers by Time Slot (Top 10)", font=dict(size=13, color='#6b7280')),
                barmode="stack",
                height=300,
                margin=dict(l=10, r=10, t=40, b=40),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#6b7280", size=10, family="Inter"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False, showline=False, tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="#f3f4f6", showline=False, zeroline=False),
            )
            
            st.plotly_chart(fig_source_time, use_container_width=True, config={'displayModeBar': False})
        
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

# Chat Tab
with month_tabs[-1]:
    st.markdown('<div class="main-title">Chat with Your Data</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Ask questions and get answers from your reservation data</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Load all months data
    df_all = load_all_months(MONTH_FILES)
    
    # Month selector
    months = sorted(df_all["Date"].dt.strftime("%B %Y").unique().tolist())
    month_scope = st.selectbox("Data scope", ["All months"] + months, key="chat_month_scope")
    
    if month_scope != "All months":
        working_df = df_all[df_all["Date"].dt.strftime("%B %Y") == month_scope].copy()
        st.caption(f"Analyzing data from: {month_scope}")
    else:
        working_df = df_all.copy()
        st.caption(f"Analyzing data from: All {len(months)} months")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Example questions
    st.markdown("**Example questions:**")
    st.caption("• What's the busiest day?  • What's the busiest time?  • Walk-ins vs reservations?  • Average party size?  • Most popular tables?")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your reservation data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response using OpenAI
        with st.chat_message("assistant"):
            with st.spinner("Analyzing data with AI..."):
                response = run_analytics_with_ai(working_df, prompt)
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
