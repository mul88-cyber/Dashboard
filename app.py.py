import streamlit as st
import pandas as pd
import numpy as np

# URL CSV dari GCS
CSV_URL = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
SEKTOR_CSV = "https://storage.googleapis.com/stock-csvku/sector.csv"

st.set_page_config(page_title="📈 Dashboard Saham", layout="wide")
st.title("📊 Dashboard Analisis Saham Indonesia")

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL)
    df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['VWAP'] = pd.to_numeric(df['VWAP'], errors='coerce')
    df['Foreign Buy'] = pd.to_numeric(df['Foreign Buy'], errors='coerce')
    df['Foreign Sell'] = pd.to_numeric(df['Foreign Sell'], errors='coerce')
    df['Volume'] = df['Volume'].fillna(0)
    return df

@st.cache_data(ttl=3600)
def load_sector():
    try:
        df = pd.read_csv(SEKTOR_CSV)
        return df
    except:
        return pd.DataFrame()

df = load_data()
df_sector = load_sector()

# Tambahkan sektor jika ada
if not df_sector.empty:
    df = df.merge(df_sector, on='Stock Code', how='left')

# Format angka
def format_angka(x):
    return f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else "-"

# --- 📌 Watchlist Saham ---
st.subheader("📌 Watchlist Saham Potensial")
watchlist = df[(df["Signal"] == "Akumulasi") & (df["Foreign Flow"] == "Inflow")]
st.dataframe(
    watchlist[["Stock Code", "Company Name", "Close", "VWAP", "Volume", "Signal", "Foreign Flow"]]
    .sort_values(by="Volume", ascending=False)
    .head(20)
    .style.format({
        "Close": format_angka,
        "VWAP": format_angka,
        "Volume": format_angka,
    })
)

# --- 🔥 Heatmap Sektor ---
st.subheader("🔥 Heatmap Sektor Berdasarkan Volume")
if 'Sector' in df.columns:
    sector_summary = df.groupby("Sector").agg({
        "Volume": "sum",
        "Stock Code": "count"
    }).rename(columns={"Stock Code": "Jumlah Saham"}).sort_values(by="Volume", ascending=False)

    st.bar_chart(sector_summary["Volume"])
    st.dataframe(sector_summary.style.format({"Volume": format_angka}))
else:
    st.warning("📌 File sektor (sector.csv) belum tersedia di GCS.")

# --- 📆 Analisis Mingguan ---
st.subheader("📆 Analisis Volume & Foreign Flow Mingguan")
selected_stock = st.selectbox("Pilih Saham", sorted(df["Stock Code"].unique()))
stock_df = df[df["Stock Code"] == selected_stock]

weekly = stock_df.groupby("Week").agg({
    "Volume": "sum",
    "Foreign Buy": "sum",
    "Foreign Sell": "sum"
}).reset_index()

st.line_chart(weekly.set_index("Week")[["Volume", "Foreign Buy", "Foreign Sell"]])

# --- 📣 Notifikasi Saham Menarik ---
st.subheader("📣 Alert Saham dengan Volume Tidak Wajar")
alert_df = df[df["Unusual Volume"] == True]
st.dataframe(
    alert_df[["Stock Code", "Company Name", "Close", "Volume", "Signal", "Foreign Flow", "Last Trading Date"]]
    .sort_values(by="Volume", ascending=False)
    .head(20)
    .style.format({
        "Close": format_angka,
        "Volume": format_angka,
    })
)
