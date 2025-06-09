import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# URL data di GCS
DATA_URL = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(DATA_URL, parse_dates=["Last Trading Date"])
    df["Volume"] = pd.to_numeric(df["Volume"], errors='coerce')
    df["Close"] = pd.to_numeric(df["Close"], errors='coerce')
    df["VWAP"] = pd.to_numeric(df["VWAP"], errors='coerce')
    df["Foreign Buy"] = pd.to_numeric(df["Foreign Buy"], errors='coerce')
    df["Foreign Sell"] = pd.to_numeric(df["Foreign Sell"], errors='coerce')
    return df

# Load data
df = load_data()
st.title("📈 Stock Analysis Dashboard")

# Sidebar filter
with st.sidebar:
    st.header("🔍 Filter")
    selected_date = st.date_input("Tanggal", df["Last Trading Date"].max())
    selected_signal = st.multiselect("Signal", df["Signal"].unique(), default=["Akumulasi"])
    unusual_only = st.checkbox("Volume Mencurigakan", value=True)
    foreign_flow = st.multiselect("Foreign Flow", df["Foreign Flow"].unique(), default=df["Foreign Flow"].unique())

# Filter data
filtered_df = df[df["Last Trading Date"] == pd.to_datetime(selected_date)]
filtered_df = filtered_df[filtered_df["Signal"].isin(selected_signal)]
if unusual_only:
    filtered_df = filtered_df[filtered_df["Unusual Volume"] == True]
filtered_df = filtered_df[filtered_df["Foreign Flow"].isin(foreign_flow)]

# Tampilkan hasil screener
st.subheader("📊 Hasil Screener Saham")
st.dataframe(
    filtered_df[["Stock Code", "Company Name", "Close", "VWAP", "Volume", "Signal", "Foreign Flow"]]
    .sort_values("Volume", ascending=False)
    .reset_index(drop=True),
    use_container_width=True
)

# Pilih saham untuk analisis visual
st.subheader("📌 Analisis Per Saham")
unique_stocks = df["Stock Code"].unique()
selected_stock = st.selectbox("Pilih Saham", sorted(unique_stocks))
stock_df = df[df["Stock Code"] == selected_stock].sort_values("Last Trading Date")

# Chart harga dan VWAP
st.markdown("### Harga vs VWAP")
chart_data = stock_df[["Last Trading Date", "Close", "VWAP"]].melt("Last Trading Date")
st.altair_chart(
    alt.Chart(chart_data).mark_line().encode(
        x="Last Trading Date:T", y="value:Q", color="variable:N"
    ).properties(height=300),
    use_container_width=True
)

# Foreign flow dan volume
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Foreign Buy/Sell")
    st.line_chart(stock_df.set_index("Last Trading Date")[[
        "Foreign Buy", "Foreign Sell"]])
with col2:
    st.markdown("### Volume")
    st.bar_chart(stock_df.set_index("Last Trading Date")["Volume"])

st.caption("Data sumber: Google Cloud Storage (hasil_gabungan.csv)")
