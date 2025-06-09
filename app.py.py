import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# Konfigurasi halaman
# ----------------------------
st.set_page_config(
    page_title="Dashboard Analisis Saham Indonesia",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# Load data dari GCS (public URL)
# ----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data
def load_sector_data():
    sector_df = pd.read_csv("https://storage.googleapis.com/stock-csvku/sector.csv")
    return sector_df

# ----------------------------
# Format angka ribuan
# ----------------------------
def format_angka(x):
    return f"{x:,.0f}" if isinstance(x, (int, float, np.integer, np.float64)) else x

# ----------------------------
# Load data
# ----------------------------
df = load_data()
sector_df = load_sector_data()

# Gabungkan sektor ke data utama
df = df.merge(sector_df, on="Stock Code", how="left")

# ----------------------------
# Sidebar filter
# ----------------------------
st.sidebar.title("📌 Filter")
pilih_tanggal = st.sidebar.date_input("Pilih Tanggal", df["Date"].max())
pilih_saham = st.sidebar.multiselect("Pilih Saham", df["Stock Code"].unique())

# Filter data berdasarkan input
filtered_df = df[df["Date"] == pd.to_datetime(pilih_tanggal)]

if pilih_saham:
    filtered_df = filtered_df[filtered_df["Stock Code"].isin(pilih_saham)]

# ----------------------------
# Header
# ----------------------------
st.markdown("# 📊 Dashboard Analisis Saham Indonesia")

# ----------------------------
# Watchlist / Tabel Ringkas
# ----------------------------
st.subheader("📋 Tabel Saham Terpilih")
tabel_ringkas = filtered_df[[
    "Date", "Stock Code", "Close", "Volume", "Value",
    "Foreign Buy", "Foreign Sell", "Net Foreign", "Sector"
]].copy()

tabel_ringkas = tabel_ringkas.sort_values(by="Net Foreign", ascending=False)
tabel_ringkas = tabel_ringkas.fillna(0)
tabel_ringkas = tabel_ringkas.applymap(format_angka)

st.dataframe(tabel_ringkas, use_container_width=True)

# ----------------------------
# Sektor Heatmap
# ----------------------------
st.subheader("🔥 Heatmap Volume per Sektor")
sector_volume = (
    filtered_df.groupby("Sector")["Volume"]
    .sum()
    .reset_index()
    .sort_values(by="Volume", ascending=False)
)
sector_volume["Volume"] = sector_volume["Volume"].apply(format_angka)
st.dataframe(sector_volume, use_container_width=True)

# ----------------------------
# Top Net Buy (Big Player)
# ----------------------------
st.subheader("🏦 Top Saham Net Buy")
top_net_buy = (
    filtered_df.sort_values(by="Net Foreign", ascending=False)
    [["Stock Code", "Net Foreign", "Foreign Buy", "Foreign Sell"]]
    .head(10)
)
top_net_buy = top_net_buy.fillna(0)
top_net_buy = top_net_buy.applymap(format_angka)
st.dataframe(top_net_buy, use_container_width=True)

# ----------------------------
# Alert Saham Menarik
# ----------------------------
st.subheader("🚨 Saham Potensi Akumulasi (Alert)")
alert_df = filtered_df[
    (filtered_df["Net Foreign"] > 1_000_000_000) & (filtered_df["Volume"] > 10_000_000)
]
alert_df = alert_df[["Stock Code", "Net Foreign", "Volume", "Value"]]
alert_df = alert_df.sort_values(by="Net Foreign", ascending=False)
alert_df = alert_df.fillna(0)
alert_df = alert_df.applymap(format_angka)
st.dataframe(alert_df, use_container_width=True)

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.caption("Dibuat oleh AI untuk analisis pasar saham Indonesia. Data berdasarkan `hasil_gabungan.csv` dan `sector.csv` dari GCS.")
