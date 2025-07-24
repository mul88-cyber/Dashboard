import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.title("🚀 Dashboard Analisis Saham Pro")

# --- Load Data ---
@st.cache_data(ttl=3600)
def load_data():
    """Memuat, membersihkan, dan menghitung indikator teknikal."""
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
        numeric_cols = ['Volume', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(0, inplace=True)
        
        # --- KALKULASI BARU ---
        # Hitung Value Perdagangan
        df['TradeValue'] = df['Close'] * df['Volume']
        
        # Hitung Moving Average untuk Volume dan Value per saham
        df = df.sort_values(by=['Stock Code', 'Last Trading Date'])
        df['MA3_vol'] = df.groupby('Stock Code')['Volume'].transform(lambda x: x.rolling(window=3).mean())
        df['MA20_vol'] = df.groupby('Stock Code')['Volume'].transform(lambda x: x.rolling(window=20).mean())
        df['MA3_val'] = df.groupby('Stock Code')['TradeValue'].transform(lambda x: x.rolling(window=3).mean())
        df['MA20_val'] = df.groupby('Stock Code')['TradeValue'].transform(lambda x: x.rolling(window=20).mean())

        # Kalkulasi lama tetap ada
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        df.sort_values(by="Last Trading Date", inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik (Tidak ada perubahan) ---
def create_aligned_chart(data, x_axis_col, title):
    if data.empty:
        st.warning("Tidak ada data untuk rentang minggu yang dipilih.")
        return
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], specs=[[{"secondary_y": True}], [{}]])
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Asing Beli', marker_color='#2ca02c'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Asing Jual', marker_color='#d62728'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Local Volume'], name='Lokal', marker_color='#1f77b4'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Close'], name='Harga', line=dict(color='white', width=2)), secondary_y=True, row=1, col=1)
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Frequency'], name='Frekuensi', mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'), row=2, col=1)
    max_vol = data['Volume'].max() if not data['Volume'].empty else 1
    max_price = data['Close'].max() if not data['Close'].empty else 1
    min_price = data['Close'].min() if not data['Close'].empty else 0
    if max_price == min_price:
        price_range_min = min_price * 0.95
        price_range_max = max_price * 1.05
    else:
        proportion = 0.70
        price_data_range = max_price - min_price
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
    # --- Sidebar Filter ---
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

        # --- Tampilan Grafik ---
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
    st.markdown("Cari saham yang menunjukkan aktivitas perdagangan signifikan berdasarkan perbandingan Moving Average (MA).")

    if not df.empty:
        # Ambil data terbaru untuk setiap saham
        latest_data = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()]

        # Opsi Filter
        col1, col2 = st.columns(2)
        with col1:
            filter_vol = st.checkbox("Lonjakan Volume (MA3 > 5x MA20)", value=True)
        with col2:
            filter_val = st.checkbox("Lonjakan Nilai (MA3 > 5x MA20)", value=False)
        
        conditions = []
        if filter_vol:
            conditions.append(latest_data['MA3_vol'] >= 5 * latest_data['MA20_vol'])
        if filter_val:
            conditions.append(latest_data['MA3_val'] >= 5 * latest_data['MA20_val'])
        
        st.divider()

        if conditions:
            # Gabungkan kondisi dengan logika OR
            final_condition = pd.concat(conditions, axis=1).any(axis=1)
            result_df = latest_data[final_condition]
            
            st.success(f"Ditemukan **{len(result_df)}** saham yang memenuhi kriteria.")
            
            # Tampilkan hasil
            display_cols = ['Stock Code', 'Close', 'Volume', 'TradeValue', 'MA3_vol', 'MA20_vol', 'MA3_val', 'MA20_val']
            
            # Format angka agar mudah dibaca
            styled_df = result_df[display_cols].style.format({
                'Close': "{:,.0f}",
                'Volume': "{:,.0f}",
                'TradeValue': "{:,.0f}",
                'MA3_vol': "{:,.0f}",
                'MA20_vol': "{:,.0f}",
                'MA3_val': "{:,.0f}",
                'MA20_val': "{:,.0f}"
            })
            
            st.dataframe(styled_df, use_container_width=True)
            
        else:
            st.info("Pilih setidaknya satu kriteria di atas untuk memulai screening.")

    else:
        st.warning("Data tidak tersedia untuk melakukan screening.")
