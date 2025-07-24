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
@st.cache_data(ttl=3600)
def load_data():
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    df = pd.read_csv(csv_url)
    df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
    
    numeric_cols = ['Volume', 'Close', 'VWAP', 'Foreign Buy', 'Foreign Sell', 'Change', 'Previous']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Simulasi Data Sektor
    sektors = ['FINANCE', 'TECHNOLOGY', 'INFRASTRUCTURE', 'ENERGY', 'HEALTHCARE', 'INDUSTRY', 'CONSUMER']
    np.random.seed(42)
    df['Sector'] = np.random.choice(sektors, size=len(df))
    
    df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
    return df

df = load_data()

# --- Kalkulasi & Persiapan Data ---
df['Change %'] = np.where(df['Previous'] != 0, (df['Change'] / df['Previous']) * 100, 0)
df.fillna(0, inplace=True) 
df["Week"] = df["Last Trading Date"].dt.strftime("%Y-%U")

# Data untuk Tab Money Flow (Agregasi Mingguan)
df['Money Flow'] = df['Close'] * df['Volume']
df['Net Foreign Flow'] = df['Foreign Buy'] - df['Foreign Sell']
weekly_flow_df = df.groupby(['Stock Code', 'Week']).agg(
    Total_Money_Flow=('Money Flow', 'sum'),
    Total_Net_Foreign=('Net Foreign Flow', 'sum')
).reset_index()

# Kalkulasi Analitis Lainnya
df["Avg Volume 5D"] = df.groupby("Stock Code")["Volume"].transform(lambda x: x.rolling(5).mean())
weekly_volume = df.groupby(["Stock Code", "Week"])["Volume"].sum().reset_index()
weekly_volume["Prev Week Volume"] = weekly_volume.groupby("Stock Code")["Volume"].shift(1)
weekly_volume["Volume Change Positive"] = (weekly_volume["Volume"] > weekly_volume["Prev Week Volume"]).astype(int)
latest_week = df.groupby("Stock Code")["Week"].last().reset_index().rename(columns={"Week": "Latest Week"})
weekly_volume = weekly_volume.merge(latest_week, on="Stock Code")
weekly_volume = weekly_volume[weekly_volume["Week"] == weekly_volume["Latest Week"]][["Stock Code", "Volume Change Positive"]]
df = df.merge(weekly_volume, on="Stock Code", how="left")

# --- Format Angka & Skoring Saham ---
def format_angka(x):
    return f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else "-"

def calculate_score(df_to_score):
    df_scored = df_to_score.copy()
    df_scored["Score"] = 0
    df_scored["Score"] += (df_scored["Signal"] == "Akumulasi") * 2
    df_scored["Score"] += (df_scored["Foreign Flow"] == "Inflow") * 2
    df_scored["Score"] += np.where(df_scored["Avg Volume 5D"] > 0, ((df_scored["Volume"] / df_scored["Avg Volume 5D"]) > 1.5).astype(int) * 2, 0)
    df_scored["Score"] += (df_scored["Close"] <= df_scored["VWAP"]).astype(int)
    df_scored["Score"] += df_scored["Volume Change Positive"].fillna(0).astype(int)
    df_scored["Score"] += df_scored["Unusual Volume"].astype(int)
    return df_scored

scored_df = calculate_score(df)
top_picks = scored_df.sort_values(by="Score", ascending=False).drop_duplicates("Stock Code").head(20)

# --- Sidebar ---
st.sidebar.header("📈 Ringkasan Harian")
max_date = df["Last Trading Date"].max()
daily_data = df[df["Last Trading Date"] == max_date]
st.sidebar.metric("Total Volume Hari Ini", format_angka(daily_data["Volume"].sum()))
st.sidebar.metric("Jumlah Saham Naik", format_angka((daily_data["Change"] > 0).sum()))
st.sidebar.metric("Jumlah Saham Turun", format_angka((daily_data["Change"] < 0).sum()))

if st.sidebar.button("🔄 Perbarui Data"):
    st.rerun()

st.sidebar.info("Dashboard ini menampilkan data historis dan analisis teknikal dasar. Selalu lakukan riset mandiri (DYOR).")

# --- Navigasi Tab Utama ---
tab1, tab2, tab5, tab3, tab4 = st.tabs([
    "🏆 Top 20 Picks", 
    "🔥 Analisis Sektoral",
    "💰 Money & Foreign Flow",
    "📊 Grafik Volume & Harga", 
    "📉 Analisis Teknikal Lengkap"
])

with tab1:
    st.subheader("🏆 Top 20 Picks Saham Hari Ini")
    st.dataframe(
        top_picks[["Stock Code", "Company Name", "Close", "VWAP", "Volume", "Score", "Signal", "Foreign Flow"]]
        .sort_values(by="Score", ascending=False)
        .style.format({ "Close": format_angka, "VWAP": format_angka, "Volume": format_angka, "Score": "{:.0f}" })
    )
    
with tab2:
    st.subheader("🔥 Heatmap Performa Sektoral Harian")
    st.markdown("Menunjukkan performa rata-rata (perubahan harga) dari setiap sektor pada hari perdagangan terakhir.")
    if 'Sector' in daily_data.columns and 'Change %' in daily_data.columns:
        sector_performance = daily_data.groupby('Sector')['Change %'].mean().sort_values(ascending=False)
        fig_heatmap = go.Figure(go.Heatmap(
                           z=[sector_performance.values], x=sector_performance.index, y=['Performa %'],
                           colorscale='RdYlGn', zmin=-2, zmax=2, 
                           text=[f'{p:.2f}%' for p in sector_performance.values], texttemplate="%{text}", textfont={"size":12}))
        fig_heatmap.update_layout(title='Performa Rata-Rata Sektor Hari Ini', height=300)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab5:
    st.subheader("💰 Analisis Mingguan: Money Flow & Foreign Flow")
    st.markdown("Grafik ini membandingkan total nilai transaksi (Money Flow) dengan aliran dana asing bersih (Net Foreign Flow) setiap minggu.")

    # --- [PERUBAHAN] Filter Bertingkat ---
    col1, col2 = st.columns(2)
    with col1:
        # Filter 1: Pilih Sektor
        unique_sectors = sorted(df['Sector'].unique())
        selected_sector = st.selectbox("Langkah 1: Pilih Sektor", unique_sectors)

    with col2:
        # Filter 2: Pilihan Saham menyesuaikan dengan Sektor
        stocks_in_sector = sorted(df[df['Sector'] == selected_sector]['Stock Code'].unique())
        selected_stock_flow = st.selectbox("Langkah 2: Pilih Stock Code", stocks_in_sector)
    # --- Akhir Perubahan ---

    if selected_stock_flow:
        filtered_flow = weekly_flow_df[weekly_flow_df['Stock Code'] == selected_stock_flow].sort_values('Week')
        if not filtered_flow.empty:
            fig_flow = make_subplots(specs=[[{"secondary_y": True}]])
            fig_flow.add_trace(go.Bar(x=filtered_flow['Week'], y=filtered_flow['Total_Money_Flow'], name='Money Flow (Nilai Transaksi)', marker_color='royalblue'), secondary_y=False)
            colors = ['green' if val >= 0 else 'red' for val in filtered_flow['Total_Net_Foreign']]
            fig_flow.add_trace(go.Bar(x=filtered_flow['Week'], y=filtered_flow['Total_Net_Foreign'], name='Net Foreign Flow', marker_color=colors), secondary_y=True)
            fig_flow.update_layout(title_text=f"Aliran Dana Mingguan untuk {selected_stock_flow}", xaxis_title='Minggu (Tahun-Minggu ke-)', barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_flow.update_yaxes(title_text="<b>Money Flow</b> (Nilai)", secondary_y=False)
            fig_flow.update_yaxes(title_text="<b>Net Foreign Flow</b> (Nilai)", secondary_y=True)
            st.plotly_chart(fig_flow, use_container_width=True)
        else:
            st.warning("Tidak ada data aliran dana mingguan untuk saham yang dipilih.")

with tab3:
    st.subheader("📊 Grafik Volume & Harga Harian")
    selected_stock_vol = st.selectbox("Pilih Stock Code ", df["Stock Code"].unique(), key="vol_chart_selectbox")
    if selected_stock_vol:
        stock_data = df[df["Stock Code"] == selected_stock_vol]
        min_date_vol = stock_data["Last Trading Date"].min().date()
        max_date_vol = stock_data["Last Trading Date"].max().date()
        date_range = st.date_input("Pilih Rentang Tanggal", [max_date_vol - pd.Timedelta(days=90), max_date_vol], min_value=min_date_vol, max_value=max_date_vol, key="vol_date_range")
        if len(date_range) == 2:
            filtered = stock_data[(stock_data["Last Trading Date"].dt.date >= date_range[0]) & (stock_data["Last Trading Date"].dt.date <= date_range[1])].copy()
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
    selected_stock_tech = st.selectbox("Pilih Saham untuk Analisis Teknikal ", df["Stock Code"].unique(), key="tech_selectbox")
    if selected_stock_tech:
        filtered_tech = df[df["Stock Code"] == selected_stock_tech].copy()
        filtered_tech.sort_values("Last Trading Date", inplace=True)
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
        rs = np.where(avg_loss == 0, np.nan, avg_gain / avg_loss)
        filtered_tech['RSI'] = 100 - (100 / (1 + rs))
        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["Close"], name="Close Price", line=dict(color="white", width=2)))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["SMA_20"], name="SMA 20", line=dict(color="orange", dash='dot')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["SMA_50"], name="SMA 50", line=dict(color="cyan", dash='dot')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["BB_Upper"], name="Upper Band", line=dict(color='rgba(152,251,152,0.5)')))
        fig_main.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["BB_Lower"], name="Lower Band", line=dict(color='rgba(152,251,152,0.5)'), fill='tonexty', fillcolor='rgba(152,251,152,0.2)'))
        fig_main.update_layout(title=f"Harga, Moving Averages & Bollinger Bands - {selected_stock_tech}", yaxis_title="Harga", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_main, use_container_width=True)
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["MACD"], name="MACD", line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["MACD_Signal"], name="Signal Line", line=dict(color='red', dash='dot')))
        fig_macd.add_trace(go.Bar(x=filtered_tech["Last Trading Date"], y=(filtered_tech['MACD'] - filtered_tech['MACD_Signal']), name="Histogram", marker_color='rgba(255,255,255,0.3)'))
        fig_macd.update_layout(title="MACD (Moving Average Convergence Divergence)", yaxis_title="Value", height=300)
        st.plotly_chart(fig_macd, use_container_width=True)
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=filtered_tech["Last Trading Date"], y=filtered_tech["RSI"], name="RSI", line=dict(color="purple")))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)", annotation_position="bottom right")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)", annotation_position="bottom right")
        fig_rsi.update_layout(title="RSI (Relative Strength Index)", yaxis_title="RSI", yaxis=dict(range=[0, 100]), height=300)
        st.plotly_chart(fig_rsi, use_container_width=True)
