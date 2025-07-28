import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_js_eval import streamlit_js_eval

# --- Konfigurasi Halaman & CSS Kustom ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.markdown("""
<style>
/* Ukuran font Tab */
button[data-baseweb="tab"] {
    font-size: 18px; font-weight: bold; padding-top: 10px !important; padding-bottom: 10px !important;
}
/* Ukuran font nilai di kartu metrik */
div[data-testid="stMetricValue"] { font-size: 22px; }
/* Ukuran font label di kartu metrik */
div[data-testid="stMetricLabel"] { font-size: 15px; }
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
        numeric_cols = ['Volume', 'Value', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency', 'Change', 'Previous', 'Change %', 'MA20_vol', 'MA20_val', 'Net Foreign Flow']
        for col in numeric_cols:
             if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(0, inplace=True)
        df.sort_values(by="Last Trading Date", inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik (Tidak ada perubahan) ---
def create_aligned_chart(data, x_axis_col, title):
    if data.empty: return
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3], specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    marker_colors_price = np.where(data['Change %'] >= 0, '#2ca02c', '#d62728')
    data['text_change'] = data['Change %'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")
    fig.add_trace(go.Bar(
        x=data[x_axis_col], y=data['Volume'], name='Total Volume', marker_color=marker_colors_price, opacity=0.9
    ), secondary_y=False, row=1, col=1)
    fig.add_trace(go.Scatter(
        x=data[x_axis_col], y=data['Close'], name='Harga', text=data['text_change'], textposition="bottom center", textfont=dict(size=10, color='rgba(135, 206, 250, 0.7)'),
        mode='lines+markers+text', customdata=data[['Change %']], hovertemplate='<b>%{x|%d %b %Y}</b><br>Harga: %{y:,.0f}<br>Change: %{customdata[0]:.2f}%<extra></extra>',
        line=dict(color='white', width=2), marker=dict(color=marker_colors_price, size=6, line=dict(width=1, color='white'))
    ), secondary_y=True, row=1, col=1)
    marker_colors_ff = np.where(data['Net Foreign Flow'] >= 0, '#2ca02c', '#d62728')
    fig.add_trace(go.Bar(
        x=data[x_axis_col], y=data['Net Foreign Flow'], name='Net Foreign Flow', marker_color=marker_colors_ff, opacity=0.7
    ), row=2, col=1)
    max_price, min_price, max_vol = (data['Close'].max(), data['Close'].min(), data['Volume'].max()) if not data.empty else (1, 0, 1)
    if max_price == min_price: price_range_min, price_range_max = (min_price * 0.95, max_price * 1.05)
    else:
        proportion, price_data_range = 0.70, max_price - min_price
        price_total_range = price_data_range / proportion
        price_range_max, price_range_min = (max_price + (price_data_range * 0.05)), (max_price + (price_data_range * 0.05)) - price_total_range
    fig.update_layout(title_text=title, title_font_size=22, template='plotly_dark', height=700, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14)))
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(title_text="Tanggal", tickfont_size=12, row=2, col=1)
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1, title_font_size=14, tickfont_size=12, range=[0, max_vol * 1.05])
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, title_font_size=14, tickfont_size=12, showgrid=False, range=[price_range_min, price_range_max])
    fig.update_yaxes(title_text="Net FF", row=2, col=1, title_font_size=14, tickfont_size=12)
    st.plotly_chart(fig, use_container_width=True)

# --- Fungsi Tabel Interaktif ---
def create_interactive_table(data, key):
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(domLayout='autoHeight')
    gridOptions = gb.build()
    
    return AgGrid(
        data, gridOptions=gridOptions, key=key,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True, theme='streamlit-dark', fit_columns_on_grid_load=True
    )

# --- Inisialisasi Session State ---
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "BBRI" if "BBRI" in df['Stock Code'].unique() else df['Stock Code'].unique()[0]

# --- Tampilan Utama dengan Tab ---
tab_top25, tab_chart, tab_screener = st.tabs(["🏆 Top 25 Saham Potensial", "📊 Analisis Detail", "🔥 Screener Volume & Value"])

with tab_top25:
    st.header("Top 25 Saham Paling Potensial Hari Ini")
    st.markdown("Saham diurutkan berdasarkan **Sistem Skor Cerdas**, dengan syarat **belum naik >70%** dalam 1, 3, atau 6 bulan terakhir.")
    
    if not df.empty:
        with st.spinner("Menghitung performa historis dan skor..."):
            latest_data = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
            today = latest_data['Last Trading Date'].max()
            perf_data = []
            
            for code, group in df.groupby('Stock Code'):
                if group.empty: continue
                latest_row = group.iloc[-1]
                
                def get_perf(offset):
                    past_date = today - offset
                    past_data = group[group['Last Trading Date'] <= past_date]
                    if not past_data.empty:
                        past_price = past_data['Close'].iloc[-1]
                        if past_price > 0:
                            return (latest_row['Close'] - past_price) / past_price * 100
                    return 0
                
                perf_data.append({'Stock Code': code, 'Perf_1M': get_perf(pd.DateOffset(months=1)), 'Perf_3M': get_perf(pd.DateOffset(months=3)), 'Perf_6M': get_perf(pd.DateOffset(months=6))})

            perf_df = pd.DataFrame(perf_data)
            latest_data = pd.merge(latest_data, perf_df, on='Stock Code', how='left').fillna(0)
            eligible_stocks = latest_data[~((latest_data['Perf_1M'] > 70) | (latest_data['Perf_3M'] > 70) | (latest_data['Perf_6M'] > 70))].copy()

            eligible_stocks['Vol_Factor'] = (eligible_stocks['Volume'] / eligible_stocks['MA20_vol']).replace([np.inf, -np.inf], 0).fillna(0)
            eligible_stocks['Score'] = 0
            eligible_stocks.loc[eligible_stocks['Final Signal'] == 'Strong Akumulasi', 'Score'] += 4
            eligible_stocks.loc[eligible_stocks['Final Signal'] == 'Akumulasi', 'Score'] += 2
            eligible_stocks.loc[eligible_stocks['Vol_Factor'] >= 10, 'Score'] += 3
            eligible_stocks.loc[(eligible_stocks['Vol_Factor'] >= 5) & (eligible_stocks['Vol_Factor'] < 10), 'Score'] += 2
            eligible_stocks.loc[eligible_stocks['Foreign Flow Signal'] == 'Inflow', 'Score'] += 2
            eligible_stocks.loc[eligible_stocks['Change %'] > 0, 'Score'] += 1
            
            top_25_df = eligible_stocks.sort_values(by='Score', ascending=False).head(25)

        st.success(f"Ditemukan **{len(top_25_df)}** saham potensial (dari {len(eligible_stocks)} yang lolos filter risiko).")
        
        display_cols = ['Stock Code', 'Company Name', 'Close', 'Change %', 'Score', 'Final Signal', 'Vol_Factor', 'Foreign Flow Signal']
        rename_cols = {'Stock Code': 'Saham', 'Company Name': 'Nama Perusahaan', 'Final Signal': 'Sinyal Utama', 'Vol_Factor': 'Vol x MA20', 'Foreign Flow Signal': 'Foreign Flow'}
        df_to_display = top_25_df[display_cols].rename(columns=rename_cols)

        response = create_interactive_table(df_to_display, 'top25_table')
        if response['selected_rows']:
            selected_code = response['selected_rows'][0]['Saham']
            if st.session_state.selected_stock != selected_code:
                st.session_state.selected_stock = selected_code
                st.warning(f"Saham {st.session_state.selected_stock} dipilih. Silakan pindah ke tab 'Analisis Detail'.")
                st.rerun()

with tab_chart:
    st.sidebar.header("🔍 Filter Analisis Detail")
    st.sidebar.divider()
    if not df.empty:
        all_stocks = sorted(df['Stock Code'].unique())
        try:
            default_index = all_stocks.index(st.session_state.selected_stock)
        except (ValueError, KeyError):
            default_index = all_stocks.index("BBRI") if "BBRI" in all_stocks else 0
        
        selected_stock = st.sidebar.selectbox("1. Pilih Kode Saham", all_stocks, index=default_index, key="stock_selector_detail")
        st.session_state.selected_stock = selected_stock
        stock_data = df[df["Stock Code"] == selected_stock].copy()
        
        if not stock_data.empty:
            latest_day_data = stock_data.iloc[-1]
            st.header(f"Analisis Detail: {selected_stock}")
            # ... (sisa logika ringkasan KPI tidak berubah) ...
        
        if not stock_data.empty and 'Week' in stock_data.columns:
            # ... (sisa logika filter minggu tidak berubah) ...
        
        # ... (sisa logika display grafik) ...
        pass

with tab_screener:
    st.header("Screener Saham Berdasarkan Lonjakan Volume & Value")
    st.markdown("Cari saham yang menunjukkan **lonjakan volume/nilai hari ini** dibandingkan rata-rata 20 hari sebelumnya.")
    if not df.empty:
        latest_data_screener = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
        # ... (sisa logika screener tidak berubah) ...
        
        if 'final_condition' in locals() and final_condition.any():
            result_df = latest_data_screener[final_condition].copy()
            result_df.sort_values(by='Vol_Factor', ascending=False, inplace=True)
            # ...
            df_to_display_screener = result_df[desktop_cols].rename(columns=rename_cols)
            response_screener = create_interactive_table(df_to_display_screener, 'screener_table')
            if response_screener['selected_rows']:
                selected_code = response_screener['selected_rows'][0]['Saham']
                if st.session_state.selected_stock != selected_code:
                    st.session_state.selected_stock = selected_code
                    st.warning(f"Saham {st.session_state.selected_stock} dipilih. Silakan pindah ke tab 'Analisis Detail'.")
                    st.rerun()
