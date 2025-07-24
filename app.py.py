import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.title("🚀 Dashboard Analisis Saham Pro")

# --- Load Data ---
CSV_URL = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv" 

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL)
    df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
    
    # Konversi kolom numerik, paksa error menjadi NaN
    numeric_cols = ['Volume', 'Close', 'VWAP', 'Foreign Buy', 'Foreign Sell', 'Change', 'Previous']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Simulasi Data Sektor untuk Heatmap
    # PENTING: Ganti bagian ini dengan data sektor riil Anda.
    sektors = ['FINANCE', 'TECHNOLOGY', 'INFRASTRUCTURE', 'ENERGY', 'HEALTHCARE', 'INDUSTRY', 'CONSUMER']
    np.random.seed(42) # Agar hasil random konsisten
    df['Sector'] = np.random.choice(sektors, size=len(df))
    
    return df

df = load_data()

# Kalkulasi Kolom 'Change %' dan penanganan data kosong
df['Change %'] = np.where(df['Previous'] != 0, (df['Change'] / df['Previous']) * 100, 0)
df.fillna(0, inplace=True) # Isi semua sisa NaN di dataframe dengan 0

# --- Format Angka ---
def format_angka(x):
    return f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else "-"

# --- Kalkulasi Analitis Tambahan ---
df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
df["Avg Volume 5D"] = df.groupby("Stock Code")["Volume"].transform(lambda x: x.rolling(5).mean())

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
    # Pastikan Avg Volume 5D tidak nol untuk menghindari error
    df["Score"] += np.where(df["Avg Volume 5D"] > 0, ((df["Volume"] / df["Avg Volume 5D"]) > 1.5).astype(int) * 2, 0)
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

# --- Sidebar ---
st.sidebar.header("📈 Ringkasan Harian")
max_date = df["Last Trading Date"].max()
daily_data = df[df["Last Trading Date"] == max_date]
st.sidebar.metric("Total Volume Hari Ini", format_angka(daily_data["Volume"].sum()))
st.sidebar.metric("Jumlah Saham Naik", format_angka((daily_data["Change"] > 0).sum()))
st.sidebar.metric("Jumlah Saham Turun", format_angka((daily_data["Change"] < 0).sum()))

if st.sidebar.button("🔄 Perbarui Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.info("Dashboard ini menampilkan data historis dan analisis teknikal dasar. Selalu lakukan riset mandiri (DYOR).")

# --- Tab Navigation ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Top 20 Picks", "🔥 Analisis Sektoral", "📊 Grafik Volume & Harga", "📉 Analisis Teknikal Lengkap"])

with tab1:
    st.subheader("🏆 Top 20 Picks Saham Hari Ini")
    st.dataframe(
        top_picks[["Stock Code", "Company Name", "Close", "VWAP", "Volume", "Score", "Signal", "Foreign Flow"]]
        .sort_values(by="Score", ascending=False)
        .style.format({ "Close": format_angka, "VWAP": format_angka, "Volume": format_angka, "Score": "{:.0f}" })
    )
    @st.cache_data
    def convert_df(df_to_convert):
        return df_to_convert.to_csv(index=False).encode('utf-8')

    csv = convert_df(top_picks)
    st.download_button("📥 Download Top Picks", data=csv, file_name="top_picks.csv", mime="text/csv")
    
    alert_stocks = scored_df[
        (scored_df["Unusual Volume"] == 1) &
        (scored_df["Foreign Flow"] == "Inflow")
    ].drop_duplicates("Stock Code")
    if not alert_stocks.empty:
        st.warning("🚨 Alert: Saham dengan Foreign Inflow + Unusual Volume")
        st.dataframe(alert_stocks[["Stock Code", "Company Name", "Close", "Volume", "Score"]])

with tab2:
    st.subheader("🔥 Heatmap Performa Sektoral Harian")
    st.markdown("Menunjukkan performa rata-rata (perubahan harga) dari setiap sektor pada hari perdagangan terakhir.")
    
    if 'Sector' in daily_data.columns and 'Change %' in daily_data.columns:
        sector_performance = daily_data.groupby('Sector')['Change %'].mean().sort_values(ascending=False)

        fig_heatmap = go.Figure(go.Heatmap(
                           z=[sector_performance.values],
                           x=sector_performance.index,
                           y=['Performa %'],
                           colorscale='RdYlGn',
                           zmin=-2, zmax=2, 
                           text=[f'{p:.2f}%' for p in sector_performance.values],
                           texttemplate="%{text}",
                           textfont={"size":12}))
        fig_heatmap.update_layout(title='Performa Rata-Rata Sektor Hari Ini', height=300)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("Data sektor atau 'Change %' tidak ditemukan.")

with tab3:
    st.subheader("📊 Grafik Volume & Harga")
    selected_stock_vol = st.selectbox("Pilih Stock Code", df["Stock Code"].unique(), key="vol_chart_selectbox")
    
    if selected_stock_vol:
        stock_data = df[df["Stock Code"] == selected_stock_vol]
        min_date = stock_data["Last Trading Date"].min().date()
        max_date_vol = stock_data["Last Trading Date"].max().date()

        date_range = st.date_input("Pilih Rentang Tanggal", [max_date_vol - pd.Timedelta(days=90), max_date_vol], min_value=min_date, max_value=max_date_vol, key="vol_date_range")

        if len(date_range) == 2:
            filtered = stock_data[
                (stock_data["Last Trading Date"].dt.date >= date_range[0]) &
                (stock_data["Last Trading Date"].dt.date <= date_range[1])
            ].copy()

            filtered.sort_values("Last Trading Date", inplace=True)
            filtered["Non Foreign Volume"] = filtered["Volume"] - (filtered["Foreign Buy"] + filtered["Foreign Sell"])

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.3, 0.7])
            
            fig.add_trace(go.Bar(x=filtered["Last Trading Date"], y=filtered["Foreign Buy"], name="Foreign Buy", marker_color="green"), row=1, col=1)
            fig.add_trace(go.Bar(x=filtered["Last Trading Date"], y=filtered["Foreign Sell"], name="Foreign Sell", marker_color="red"), row=1, col=1)
            fig.add_trace(go.Bar(x=filtered["Last Trading Date"], y=filtered["Non Foreign Volume"], name="Lokal", marker_color="royalblue"), row=1, col=1)

            fig.add_trace(go.Scatter(x=filtered["Last Trading Date"], y=filtered["Close"], name="Close Price", mode="lines+markers", line=dict(color="white", width=2)), row=2, col=1)
            
            fig.update_layout(title_text=f"Analisis Volume & Harga: {selected_stock_vol}", height=600, barmode="stack", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_yaxes(title_text="Volume", row=1, col=1)
            fig.update_yaxes(title_text="Close Price", row=2, col=1)
            fig.update_xaxes(showticklabels=False, row=1, col=1)
            fig.update_xaxes(title_text="Tanggal", row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📉 Analisis Teknikal Lengkap")
    selected_stock_tech = st.selectbox("Pilih Saham untuk Analisis Teknikal", df["Stock Code"].unique(), key="tech_selectbox")

    if selected_stock_tech:
        filtered_tech = df[df["Stock Code"] == selected_stock_tech].copy()
        filtered_tech.sort_values("Last Trading Date", inplace=True)
        
        # Hitung Indikator Teknikal
        filtered_tech['SMA_20'] = filtered_tech['Close'].rolling(window=20).mean()
        filtered_tech['SMA_50'] = filtered_tech['Close'].rolling(window=50).mean()
        
        filtered_tech['BB_Mid'] = filtered_tech['SMA_20']
        filtered_tech['BB_Upper'] = filtered_tech['SMA_20'] + 2 * filtered_tech['Close'].rolling(window=20).std()
        filtered_tech['BB_Lower'] = filtered_tech['SMA_20'] - 2 * filtered_tech['Close'].rolling(window=20).std()
        
        exp1 = filtered_tech['Close'].ewm(span=12, adjust=False).mean()
        exp2 = filtered_tech['Close'].ewm(span=26, adjust=False).mean()
        filtered_tech['MACD'] = exp1 - exp2
        filtered_tech['MACD_Signal'] = filtered_tech['MACD'].ewm(span=9, adjust=False).mean()
        
        delta = filtered_tech['Close'].diff(1)
        gain = delta.where(delta > 0, 0).fillna(0)
        loss = -delta.where(delta < 0, 0).fillna(0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        # Hindari pembagian dengan nol untuk RSI
        rs = np.where(avg_loss == 0, np.nan, avg_gain / avg_loss)
        filtered_tech['RSI'] = 100 - (100 / (1 + rs))

        # Visualisasi Utama: Harga, MA, Bollinger Bands
        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["Close"], name="Close Price", line=dict(color="white", width=2)))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["SMA_20"], name="SMA 20", line=dict(color="orange", dash='dot')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["SMA_50"], name="SMA 50", line=dict(color="cyan", dash='dot')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["BB_Upper"], name="Upper Band", line=dict(color='rgba(152,251,152,0.5)')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["BB_Lower"], name="Lower Band", line=dict(color='rgba(152,251,152,0.5)'), fill='tonexty', fillcolor='rgba(152,251,152,0.2)'))
        fig_main.update_layout(title=f"Harga, Moving Averages & Bollinger Bands - {selected_stock_tech}", yaxis_title="Harga", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_main, use_container_width=True)
        
        # Visualisasi MACD
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["MACD"], name="MACD", line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["MACD_Signal"], name="Signal Line", line=dict(color='red', dash='dot')))
        fig_macd.add_trace(go.Bar(x=filtered_tech["Last Trading Date"], y=(filtered_tech['MACD'] - filtered_tech['MACD_Signal']), name="Histogram", marker_color='rgba(255,255,255,0.3)'))
        fig_macd.update_layout(title="MACD (Moving Average Convergence Divergence)", yaxis_title="Value", height=300)
        st.plotly_chart(fig_macd, use_container_width=True)

        # Visualisasi RSI
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["RSI"], name="RSI", line=dict(color="purple")))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)", annotation_position="bottom right")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)", annotation_position="bottom right")
        fig_rsi.update_layout(title="RSI (Relative Strength Index)", yaxis_title="RSI", yaxis=dict(range=[0, 100]), height=300)
        st.plotly_chart(fig_rsi, use_container_width=True)
