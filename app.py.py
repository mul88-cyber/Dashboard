import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard Analisis Saham Indonesia", layout="wide")

# ------------------------ Load Data ------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv")
    sector = pd.read_csv("https://storage.googleapis.com/stock-csvku/sector.csv")
    
    # Pastikan kolom tanggal benar dan bertipe datetime
    if "Last Trading Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Last Trading Date"])
    else:
        st.error("❌ Kolom 'Last Trading Date' tidak ditemukan.")
        st.stop()

    df = df.merge(sector, how="left", on="Stock Code")
    df = df.sort_values("Date")
    return df

df = load_data()

# ------------------------ Watchlist & Filter ------------------------
st.title("📈 Dashboard Analisis Saham Indonesia")

with st.sidebar:
    st.header("📌 Watchlist")
    all_stocks = sorted(df["Stock Code"].dropna().unique())
    watchlist = st.multiselect("Pilih saham untuk watchlist:", all_stocks, default=["BBRI", "BBCA", "TLKM"])
    df_watch = df[df["Stock Code"].isin(watchlist)]

    st.divider()
    st.markdown("🗓️ **Filter Mingguan**")
    selected_week = st.date_input("Pilih tanggal akhir minggu:", value=pd.Timestamp(df["Date"].max()))
    selected_week = pd.Timestamp(selected_week)  # Convert ke pandas Timestamp agar bisa operasi timedelta
    df_week = df[df["Date"] >= selected_week - pd.Timedelta(days=7)]

# ------------------------ Weekly Accumulation ------------------------
st.subheader("🧠 Akumulasi Mingguan")

akumulasi = (
    df_week.groupby("Stock Code")
    .agg({"Value": "sum", "Foreign Buy": "sum", "Foreign Sell": "sum"})
    .assign(Net_Foreign=lambda x: x["Foreign Buy"] - x["Foreign Sell"])
    .sort_values("Net_Foreign", ascending=False)
)

st.dataframe(akumulasi.style.format(thousands=","), use_container_width=True)

# ------------------------ Sektor Heatmap ------------------------
st.subheader("🌐 Heatmap Sektor (Net Foreign Flow)")

sector_heatmap = (
    df_week.groupby("Sector")
    .agg({"Foreign Buy": "sum", "Foreign Sell": "sum"})
    .assign(Net_Foreign=lambda x: x["Foreign Buy"] - x["Foreign Sell"])
    .reset_index()
)

fig = px.density_heatmap(
    sector_heatmap,
    x="Sector",
    y=["Net_Foreign"],
    z="Net_Foreign",
    color_continuous_scale="RdYlGn",
    title="Net Foreign Flow per Sektor",
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------ Notifikasi Saham Menarik ------------------------
st.subheader("🚨 Alert Saham Menarik")

latest = df[df["Date"] == df["Date"].max()].copy()
latest["Net Foreign"] = latest["Foreign Buy"] - latest["Foreign Sell"]

alerts = latest[(latest["Net Foreign"] > 5_000_000_000) & (latest["Value"] > 10_000_000_000)]
alerts = alerts[["Date", "Stock Code", "Value", "Foreign Buy", "Foreign Sell", "Net Foreign"]]
st.dataframe(alerts.style.format(thousands=","), use_container_width=True)

# ------------------------ Tabel Watchlist ------------------------
st.subheader("📋 Data Watchlist")

if not df_watch.empty:
    latest_watch = df_watch[df_watch["Date"] == df_watch["Date"].max()].copy()
    latest_watch["Net Foreign"] = latest_watch["Foreign Buy"] - latest_watch["Foreign Sell"]
    st.dataframe(
        latest_watch[["Date", "Stock Code", "Close", "Volume", "Value", "Foreign Buy", "Foreign Sell", "Net Foreign"]]
        .sort_values("Net Foreign", ascending=False)
        .style.format(thousands=","),
        use_container_width=True
    )
else:
    st.info("Pilih saham di watchlist terlebih dahulu.")
