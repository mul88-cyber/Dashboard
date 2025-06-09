import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from google.cloud import storage
from io import BytesIO

# Konfigurasi halaman
st.set_page_config(page_title="Dashboard Analisis Saham", layout="wide")
st.title("📊 Dashboard Analisis Saham Indonesia")

# Fungsi load data dari GCS
@st.cache_data

def load_data_from_gcs(bucket_name, file_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = blob.download_as_bytes()
    return pd.read_csv(BytesIO(data))

# Load data utama
bucket_name = "stock-csvku"
data_file = "hasil_gabungan.csv"
sector_file = "sector.csv"

try:
    df = load_data_from_gcs(bucket_name, data_file)
    sector_df = load_data_from_gcs(bucket_name, sector_file)
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.stop()

# Gabungkan dengan sector
df = df.merge(sector_df, on="Stock Code", how="left")

# Format angka
def format_number(x):
    try:
        return f"{int(x):,}"
    except:
        return x

for col in ["Close", "VWAP", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Hitung skor untuk AI Watchlist
watchlist_df = df.copy()
watchlist_df["Score"] = 0
watchlist_df.loc[watchlist_df["Signal"] == "Akumulasi", "Score"] += 1
watchlist_df.loc[watchlist_df["Foreign Flow"] == "Inflow", "Score"] += 1
watchlist_df.loc[watchlist_df["Close"] > watchlist_df["VWAP"], "Score"] += 1
watchlist_df.loc[watchlist_df["Volume"] > watchlist_df["Volume"].quantile(0.75), "Score"] += 1

watchlist_top = watchlist_df.sort_values("Score", ascending=False).head(10)

# Hitung ranking per sektor
top_per_sector = df[df["Signal"] == "Akumulasi"].groupby("Sector", group_keys=False).apply(
    lambda x: x.sort_values("Volume", ascending=False).head(3)
)

# Tabs UI
tab1, tab2, tab3, tab4 = st.tabs([
    "📌 Watchlist", "🔥 Heatmap Sektor", "📈 Analisis Mingguan", "📣 Alert Saham"
])

with tab1:
    st.subheader("📌 Watchlist Saham Potensial (AI)")
    show_cols = ["Stock Code", "Company Name", "Sector", "Close", "VWAP", "Volume", "Signal", "Foreign Flow"]
    temp_df = watchlist_top[show_cols].copy()
    temp_df["Close"] = temp_df["Close"].apply(format_number)
    temp_df["VWAP"] = temp_df["VWAP"].apply(format_number)
    temp_df["Volume"] = temp_df["Volume"].apply(format_number)
    st.dataframe(temp_df, use_container_width=True)

with tab2:
    st.subheader("🔥 Heatmap Sektor Berdasarkan Volume")
    sector_vol = df.groupby("Sector")["Volume"].sum().reset_index()
    sector_vol = sector_vol.sort_values("Volume", ascending=False)
    
    chart = alt.Chart(sector_vol).mark_bar().encode(
        x=alt.X("Sector", sort="-y"),
        y=alt.Y("Volume", title="Total Volume"),
        tooltip=["Sector", "Volume"]
    ).properties(width=900, height=400)
    
    st.altair_chart(chart, use_container_width=True)

with tab3:
    st.subheader("📈 Analisis Mingguan per Saham")
    stock_options = df["Stock Code"].unique()
    selected_stock = st.selectbox("Pilih Saham", stock_options)
    
    stock_data = df[df["Stock Code"] == selected_stock].copy()
    stock_data = stock_data.sort_values("Date")
    stock_data["Date"] = pd.to_datetime(stock_data["Date"])

    volume_chart = alt.Chart(stock_data).mark_line(point=True).encode(
        x="Date:T",
        y="Volume",
        tooltip=["Date", "Volume"]
    ).properties(title=f"Volume Harian - {selected_stock}", height=300)

    foreign_chart = alt.Chart(stock_data).mark_line(point=True, color="orange").encode(
        x="Date:T",
        y="Net Foreign",
        tooltip=["Date", "Net Foreign"]
    ).properties(title=f"Net Foreign Harian - {selected_stock}", height=300)

    st.altair_chart(volume_chart, use_container_width=True)
    st.altair_chart(foreign_chart, use_container_width=True)

with tab4:
    st.subheader("📣 Notifikasi Saham Menarik Hari Ini")
    alerts = df[
        (df["Signal"] == "Akumulasi") &
        (df["Foreign Flow"] == "Inflow") &
        (df["Volume"] > df["Volume"].quantile(0.8))
    ][show_cols].copy()
    alerts["Close"] = alerts["Close"].apply(format_number)
    alerts["VWAP"] = alerts["VWAP"].apply(format_number)
    alerts["Volume"] = alerts["Volume"].apply(format_number)

    st.dataframe(alerts, use_container_width=True)
