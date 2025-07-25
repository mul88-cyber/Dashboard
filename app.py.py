import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.title("🚀 Dashboard Analisis Saham Pro")

# --- Load Data & Kalkulasi ---
@st.cache_data(ttl=3600)
def load_data():
    """Memuat, membersihkan, dan menghitung semua indikator yang dibutuhkan."""
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
        numeric_cols = ['Volume', 'Value', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency', 'Change', 'Previous']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(0, inplace=True)
        
        df['Change %'] = np.where(df['Previous'] != 0, (df['Change'] / df['Previous']) * 100, 0)
        df = df.sort_values(by=['Stock Code', 'Last Trading Date'])
        df['MA20_vol'] = df.groupby('Stock Code')['Volume'].transform(lambda x: x.rolling(window=20, min_periods=1).mean())
        df['MA20_val'] = df.groupby('Stock Code')['Value'].transform(lambda x: x.rolling(window=20, min_periods=1).mean())
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        
        df.sort_values(by="Last Trading Date", inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik Final ---
def create_aligned_chart(data, x_axis_col, title):
    """
    Membuat grafik combo dengan teks Change % yang tampil permanen di atas/bawah marker.
    """
    if data.empty:
        st.warning("Tidak ada data untuk rentang minggu yang dipilih.")
        return

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{}]])

    # --- PERBAIKAN: Menyiapkan dan menampilkan teks Change % ---
    marker_colors = np.where(data['Change %'] >= 0, '#2ca02c', '#d62728')
    # Buat teks untuk ditampilkan di grafik, tambahkan '+' untuk angka positif
    data['text_change'] = data['Change %'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")

    # Bar volume
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Asing Beli', marker_color='#2ca02c'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Asing Jual', marker_color='#d62728'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Local Volume'], name='Lokal', marker_color='#1f77b4'), row=1, col=1)
    
    # Garis harga dengan teks permanen
    fig.add_trace(go.Scatter(
        x=data[x_axis_col],
        y=data['Close'],
        name='Harga',
        # Tampilkan teks dari kolom 'text_change'
        text=data['text_change'],
        textposition="bottom center", # Posisi teks: bawah tengah dari marker
        textfont=dict(
            size=10,
            color='white'
        ),
        mode='lines+markers+text', # Tambahkan 'text' ke mode
        line=dict(color='white', width=2),
        marker=dict(color=marker_colors, size=6, line=dict(width=1, color='white'))
    ), secondary_y=True, row=1, col=1)

    # Grafik Bawah: Frekuensi
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Frequency'], name='Frekuensi', mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'), row=2, col=1)

    # Logika rentang sumbu Y
    max_vol = data['Volume'].max() if not data['Volume'].empty else 1
    max_price = data['Close'].max() if not data['Close'].empty else 1
    min_price = data['Close'].min() if not data['Close'].empty else 0
    if max_price == min_price:
        price_range_min, price_range_max = (min_price * 0.95, max_price * 1.05)
    else:
        proportion, price_data_range = 0.70, max_price - min_price
        price_total_range = price_data_range / proportion
        price_range_max = max_price + (price_data_range * 0.05)
        price_range_min = price_range_max - price_total_range
        
    fig.update_layout(title_text=title, title_font_size=22, template='plotly_dark', height=600, barmode='stack', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14)))
    fig.update_xaxes(tickfont_size=12)
    fig.update_yaxes(title_font_size=16, tickfont_size=12)
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1, range=[0, max_vol * 1.05])
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, showgrid=False, range=[price_range_min, price_range_max])
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# --- Tampilan Utama dengan Tab ---
tab_chart, tab_screener = st.tabs(["📊 Analisis Detail", "🔥 Screener Volume & Value"])

with tab_chart:
    st.sidebar.header("🔍 Filter Analisis Detail")
    st.sidebar.divider()
    if not df.empty:
        all_stocks = sorted(df['Stock Code'].unique())
        selected_stock = st.sidebar.selectbox("1. Pilih Kode Saham", all_stocks, index=all_stocks.index("BBRI") if "BBRI" in all_stocks else 0)
        stock_data = df[df["Stock Code"] == selected_stock]
        if not stock_data.empty and 'Week' in stock_data.columns:
            week_mapping = stock_data.groupby('Week')['Last Trading Date'].max().reset_index()
            sorted_weeks_df = week_mapping.sort_values(by='Last Trading Date', ascending=False)
            available_weeks = sorted_weeks_df['Week'].tolist()
            selected_weeks = st.sidebar.multiselect("2. Pilih Minggu", options=available_weeks, default=available_weeks[:4] if len(available_weeks) > 4 else available_weeks)
        else:
            selected_weeks = []
        st.sidebar.divider()
        if st.sidebar.button("🔄 Perbarui Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if selected_weeks:
            filtered_daily_data = stock_data[stock_data['Week'].isin(selected_weeks)]
            st.header(f"Analisis Harian untuk {selected_stock}")
            st.markdown(f"##### Menampilkan data untuk minggu: **{', '.join(selected_weeks)}**")
            create_aligned_chart(data=filtered_daily_data, x_axis_col='Last Trading Date', title=f"Analisis Detail Harian untuk {selected_stock}")
        else:
            st.info("Pilih setidaknya satu minggu dari sidebar untuk menampilkan data.")
    else:
        st.warning("Gagal memuat data.")

with tab_screener:
    st.header("Screener Saham Berdasarkan Lonjakan Volume & Value")
    st.markdown("Cari saham yang menunjukkan **lonjakan volume/nilai hari ini** dibandingkan rata-rata 20 hari sebelumnya.")
    if not df.empty:
        latest_data = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_vol = st.checkbox("Filter Lonjakan Volume", value=True, key="vol_filter")
        with col2:
            filter_val = st.checkbox("Filter Lonjakan Nilai", value=False, key="val_filter")
        with col3:
            multiplier = st.number_input("Minimal Kenaikan (x kali lipat)", min_value=1.0, value=5.0, step=0.5, key="multiplier")
        latest_data['Vol_Factor'] = (latest_data['Volume'] / latest_data['MA20_vol']).replace([np.inf, -np.inf], 0).fillna(0)
        latest_data['Val_Factor'] = (latest_data['Value'] / latest_data['MA20_val']).replace([np.inf, -np.inf], 0).fillna(0)
        conditions = []
        if filter_vol:
            conditions.append(latest_data['Vol_Factor'] >= multiplier)
        if filter_val:
            conditions.append(latest_data['Val_Factor'] >= multiplier)
        st.divider()
        if conditions:
            final_condition = pd.concat(conditions, axis=1).any(axis=1)
            result_df = latest_data[final_condition].copy()
            result_df.sort_values(by='Vol_Factor', ascending=False, inplace=True)
            st.success(f"Ditemukan **{len(result_df)}** saham yang memenuhi kriteria.")
            display_cols = ['Stock Code', 'Close', 'Change %', 'Volume', 'Vol_Factor', 'MA20_vol', 'Value', 'Val_Factor', 'MA20_val']
            rename_cols = {'Stock Code': 'Saham', 'Vol_Factor': 'Vol x MA20', 'MA20_vol': 'Rata2 Vol 20D', 'Val_Factor': 'Val x MA20', 'MA20_val': 'Rata2 Val 20D'}
            styled_df = result_df[display_cols].rename(columns=rename_cols).style.format({
                'Close': "{:,.0f}", 'Change %': "{:,.2f}%", 'Volume': "{:,.0f}", 'Vol x MA20': "{:,.1f}x",
                'Rata2 Vol 20D': "{:,.0f}", 'Value': "{:,.0f}", 'Val x MA20': "{:,.1f}x", 'Rata2 Val 20D': "{:,.0f}"
            }).background_gradient(cmap='Greens', subset=['Vol x MA20', 'Val x MA20'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("Pilih setidaknya satu kriteria di atas untuk memulai screening.")
    else:
        st.warning("Data tidak tersedia untuk melakukan screening.")
