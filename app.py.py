import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_js_eval import streamlit_js_eval

# --- Konfigurasi Halaman & CSS Kustom ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.markdown("""
<style>
/* ... CSS styles ... */
</style>
""", unsafe_allow_html=True)
st.title("🚀 Dashboard Analisis Saham Pro")

# --- Load Data & Kalkulasi ---
@st.cache_data(ttl=3600)
def load_data():
    """Memuat dan membersihkan data dari URL."""
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
        # ... (sisa fungsi load_data tidak berubah) ...
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik (Tidak ada perubahan) ---
def create_aligned_chart(data, x_axis_col, title):
    # ... (sisa fungsi grafik tidak berubah) ...
    pass

# --- Tampilan Utama dengan Tab ---
# Inisialisasi tab_selection di session state
if 'tab_selection' not in st.session_state:
    st.session_state.tab_selection = "🏆 Top 25 Saham Potensial"

# Buat placeholder untuk tab
tab_placeholders = st.tabs(["🏆 Top 25 Saham Potensial", "📊 Analisis Detail", "🔥 Screener Volume & Value"])

# --- Logika Interaksi & Tampilan Tab ---
# Ambil data terbaru untuk semua saham
latest_data = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()

# Fungsi untuk membuat tabel interaktif
def create_interactive_table(data, key):
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(domLayout='autoHeight')
    gridOptions = gb.build()
    
    grid_response = AgGrid(
        data,
        gridOptions=gridOptions,
        key=key,
        update_mode='MODEL_CHANGED',
        allow_unsafe_jscode=True,
        theme='streamlit-dark'
    )
    return grid_response

# --- Tab 1: Top 25 ---
with tab_placeholders[0]:
    st.header("Top 25 Saham Paling Potensial Hari Ini")
    st.markdown("Saham diurutkan berdasarkan **Sistem Skor Cerdas**, dengan syarat **belum naik >70%** dalam 1, 3, atau 6 bulan terakhir.")
    
    if not df.empty:
        # --- Filter Risiko Kenaikan Harga ---
        st.info("Menghitung performa historis untuk filter risiko...")
        
        today = latest_data['Last Trading Date'].max()
        perf_data = []
        for code, group in df.groupby('Stock Code'):
            latest_row = group.loc[group['Last Trading Date'].idxmax()]
            
            p_1m = group[group['Last Trading Date'] <= today - pd.DateOffset(months=1)]
            p_3m = group[group['Last Trading Date'] <= today - pd.DateOffset(months=3)]
            p_6m = group[group['Last Trading Date'] <= today - pd.DateOffset(months=6)]

            perf_1m = (latest_row['Close'] - p_1m['Close'].iloc[-1]) / p_1m['Close'].iloc[-1] * 100 if not p_1m.empty else 0
            perf_3m = (latest_row['Close'] - p_3m['Close'].iloc[-1]) / p_3m['Close'].iloc[-1] * 100 if not p_3m.empty else 0
            perf_6m = (latest_row['Close'] - p_6m['Close'].iloc[-1]) / p_6m['Close'].iloc[-1] * 100 if not p_6m.empty else 0
            
            perf_data.append({'Stock Code': code, 'Perf_1M': perf_1m, 'Perf_3M': perf_3m, 'Perf_6M': perf_6m})

        perf_df = pd.DataFrame(perf_data)
        latest_data = pd.merge(latest_data, perf_df, on='Stock Code')

        # Terapkan filter risiko
        eligible_stocks = latest_data[~((latest_data['Perf_1M'] > 70) | (latest_data['Perf_3M'] > 70) | (latest_data['Perf_6M'] > 70))]

        # --- Scoring ---
        eligible_stocks['Vol_Factor'] = (eligible_stocks['Volume'] / eligible_stocks['MA20_vol']).replace([np.inf, -np.inf], 0).fillna(0)
        eligible_stocks['Score'] = 0
        eligible_stocks.loc[eligible_stocks['Final Signal'] == 'Strong Akumulasi', 'Score'] += 4
        # ... (sisa logika skor) ...
        
        top_25_df = eligible_stocks.sort_values(by='Score', ascending=False).head(25)

        st.success(f"Ditemukan **{len(top_25_df)}** saham potensial (dari {len(eligible_stocks)} yang lolos filter risiko).")
        
        # Tampilkan tabel interaktif
        response_top25 = create_interactive_table(top_25_df, 'top25_table')
        if response_top25['selected_rows']:
            selected_stock_code = response_top25['selected_rows'][0]['Stock Code']
            st.session_state.selected_stock_sidebar = selected_stock_code
            st.session_state.tab_selection = "📊 Analisis Detail"
            st.rerun()

# --- Sidebar & Logika Umum ---
st.sidebar.header("🔍 Filter Analisis Detail")
# ... (sisa sidebar) ...

# --- Tab 2: Analisis Detail ---
with tab_placeholders[1]:
    # ... (logika tab detail) ...
    # Di dalam selectbox:
    # selected_stock = st.sidebar.selectbox("1. ...", key='selected_stock_sidebar')

# --- Tab 3: Screener ---
with tab_placeholders[2]:
    # ... (logika tab screener) ...
    # response_screener = create_interactive_table(result_df, 'screener_table')
    # if response_screener['selected_rows']:
    #     ... (logika serupa untuk update session state)

# Logika untuk mengatur tab aktif
# (Ditempatkan di akhir skrip)
# default_tab_index = ["🏆 Top 25 Saham Potensial", "📊 Analisis Detail", "🔥 Screener Volume & Value"].index(st.session_state.tab_selection)
# st.tabs(..., default_index=default_tab_index) # sayangnya Streamlit belum support default_index
