import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from textwrap import wrap
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham", layout="wide")
st.title("📊 Dashboard Analisis Top Picks")

# --- Load Data ---
CSV_URL = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv" 

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL)
    df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['VWAP'] = pd.to_numeric(df['VWAP'], errors='coerce')
    df['Foreign Buy'] = pd.to_numeric(df['Foreign Buy'], errors='coerce')
    df['Foreign Sell'] = pd.to_numeric(df['Foreign Sell'], errors='coerce')
    return df

df = load_data()

# --- Format Angka ---
def format_angka(x):
    return f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else "-"

# --- Kolom Tambahan: Avg Volume 5 Hari ---
df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
df["Avg Volume 5D"] = df.groupby("Stock Code")["Volume"].transform(lambda x: x.rolling(5).mean())

# --- Perubahan Volume Mingguan ---
if "Week" not in df.columns:
    df["Week"] = df["Last Trading Date"].dt.strftime("%Y-%U")

weekly_volume = df.groupby(["Stock Code", "Week"])["Volume"].sum().reset_index()
weekly_volume["Prev Week Volume"] = weekly_volume.groupby("Stock Code")["Volume"].shift(1)
weekly_volume["Volume Change Positive"] = (weekly_volume["Volume"] > weekly_volume["Prev Week Volume"]).astype(int)

latest_week = df.groupby("Stock Code")["Week"].last().reset_index().rename(columns={"Week": "Latest Week"})
weekly_volume = weekly_volume.merge(latest_week, on="Stock Code")
weekly_volume = weekly_volume[weekly_volume["Week"] == weekly_volume["Latest Week"]][["Stock Code", "Volume Change Positive"]]
df = df.merge(weekly_volume, on="Stock Code", how="left")

# --- Skoring Saham ---
def calculate_score(df):
    df = df.copy()
    df["Score"] = 0
    df["Score"] += (df["Signal"] == "Akumulasi") * 2
    df["Score"] += (df["Foreign Flow"] == "Inflow") * 2
    df["Score"] += ((df["Volume"] / df["Avg Volume 5D"]) > 1.5).astype(int) * 2
    df["Score"] += (df["Close"] <= df["VWAP"]).astype(int)
    df["Score"] += df["Volume Change Positive"].fillna(0).astype(int)
    df["Score"] += df["Unusual Volume"].astype(int)
    return df

scored_df = calculate_score(df)
top_picks = (
    scored_df.sort_values(by="Score", ascending=False)
    .drop_duplicates("Stock Code")
    .head(20)
)

# --- Alerts Saham Mencurigakan ---
alert_stocks = scored_df[
    (scored_df["Unusual Volume"] == 1) &
    (scored_df["Foreign Flow"] == "Inflow")
]

# --- Sidebar Ringkasan Harian ---
max_date = df["Last Trading Date"].max()
daily_data = df[df["Last Trading Date"] == max_date]
st.sidebar.header("📈 Ringkasan Harian")
st.sidebar.metric("Total Volume Hari Ini", format_angka(daily_data["Volume"].sum()))
st.sidebar.metric("Jumlah Saham Naik", format_angka((daily_data["Change"] > 0).sum()))
st.sidebar.metric("Jumlah Saham Turun", format_angka((daily_data["Change"] < 0).sum()))

# --- Tombol Refresh Manual ---
if st.sidebar.button("🔄 Perbarui Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# --- Tab Navigation ---
tab1, tab2, tab3 = st.tabs(["📈 Top 20 Picks", "📊 Grafik Volume & Harga", "📉 Analisis Teknikal"])

with tab1:
    st.subheader("Top 20 Picks Saham Hari Ini")
    st.dataframe(
        top_picks[["Stock Code", "Company Name", "Close", "VWAP", "Volume", "Score", "Signal", "Foreign Flow"]]
        .sort_values(by="Score", ascending=False)
        .style.format({
            "Close": format_angka,
            "VWAP": format_angka,
            "Volume": format_angka,
            "Score": "{:.0f}"
        })
    )
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(top_picks)
    st.download_button("📥 Download Top Picks", data=csv, file_name="top_picks.csv", mime="text/csv")

with tab2:
    st.subheader("📊 Grafik Volume (Foreign, Non-Foreign) + Close Price")

    selected_stock = st.selectbox("Pilih Stock Code", df["Stock Code"].unique())
    min_date = df["Last Trading Date"].min()
    max_date = df["Last Trading Date"].max()
    date_range = st.date_input("Pilih Rentang Tanggal", [min_date, max_date])

    filtered = df[
        (df["Stock Code"] == selected_stock) &
        (df["Last Trading Date"] >= pd.to_datetime(date_range[0])) &
        (df["Last Trading Date"] <= pd.to_datetime(date_range[1]))
    ].copy()

    filtered.sort_values("Last Trading Date", inplace=True)
    filtered["Non Foreign Volume"] = filtered["Volume"] - filtered["Foreign Buy"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=filtered["Last Trading Date"],
        y=filtered["Foreign Buy"],
        name="Foreign Buy",
        marker_color="green"
    ))

    fig.add_trace(go.Bar(
        x=filtered["Last Trading Date"],
        y=filtered["Foreign Sell"],
        name="Foreign Sell",
        marker_color="sandybrown"
    ))

    fig.add_trace(go.Bar(
        x=filtered["Last Trading Date"],
        y=filtered["Non Foreign Volume"],
        name="Volume (Non Foreign)",
        marker_color="royalblue"
    ))

    fig.add_trace(go.Scatter(
        x=filtered["Last Trading Date"],
        y=filtered["Close"],
        name="Close Price",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="black", dash="dot")
    ))

    fig.update_layout(
        barmode="stack",
        xaxis_title="Tanggal",
        yaxis=dict(title="Volume", side="left"),
        yaxis2=dict(title="Close Price", overlaying="y", side="right"),
        title=f"Volume Saham dan Harga Penutupan - {selected_stock}",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=550,
        margin=dict(l=40, r=40, t=50, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📉 Analisis Teknikal (Moving Average)")
    selected_stock_tech = st.selectbox("Pilih Saham untuk Analisis Teknikal", df["Stock Code"].unique())
    filtered_tech = df[df["Stock Code"] == selected_stock_tech].copy()
    filtered_tech.sort_values("Last Trading Date", inplace=True)

    # Hitung Indikator
    filtered_tech['SMA_20'] = filtered_tech['Close'].rolling(window=20).mean()
    filtered_tech['EMA_12'] = filtered_tech['Close'].ewm(span=12, adjust=False).mean()

    fig_tech = go.Figure()
    fig_tech.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["Close"], name="Close Price", line=dict(color="blue")))
    fig_tech.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["SMA_20"], name="SMA 20", line=dict(color="orange")))
    fig_tech.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["EMA_12"], name="EMA 12", line=dict(color="red")))

    fig_tech.update_layout(
        title=f"Analisis Teknikal - {selected_stock_tech}",
        xaxis_title="Tanggal",
        yaxis_title="Harga",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    st.plotly_chart(fig_tech, use_container_width=True)

# --- Alert Saham Mencurigakan ---
if not alert_stocks.empty:
    st.warning("🚨 Ada saham mencurigakan: Foreign Inflow + Unusual Volume!")
    st.dataframe(alert_stocks[["Stock Code", "Company Name", "Signal", "Score"]])
