import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_js_eval import streamlit_js_eval

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
        numeric_cols = ['Volume', 'Value', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency', 'Change', 'Previous', 'Change %', 'MA20_vol', 'MA20_val', 'Net Foreign Flow']
        for col in numeric_cols:
             if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(0, inplace=True)
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        df.sort_values(by="Last Trading Date", inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik ---
def create_aligned_chart(data, x_axis_col, title):
    if data.empty: return
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], specs=[[{"secondary_y": True}], [{}]])
    def format_volume_text_id(num):
        if num == 0: return ''
        if abs(num) >= 1_000_000_000: return f'{num / 1_000_000_000:.1f}M'
        if abs(num) >= 1_000_000: return f'{num / 1_000_000:.1f}Jt'
        if abs(num) >= 1_000: return f'{num / 1_000:.1f}Rb'
        return f'{num:.0f}'
    text_fb, text_fs, text_local = (data['Foreign Buy'].apply(format_volume_text_id), data['Foreign Sell'].apply(format_volume_text_id), data['Local Volume'].apply(format_volume_text_id))
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Asing Beli', marker_color='#2ca02c', text=text_fb, textposition='inside', textangle=-90, insidetextanchor='middle', textfont=dict(color='white', size=10)), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Asing Jual', marker_color='#d62728', text=text_fs, textposition='inside', textangle=-90, insidetextanchor='middle', textfont=dict(color='white', size=10)), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Local Volume'], name='Lokal', marker_color='#1f77b4', text=text_local, textposition='inside', textangle=-90, insidetextanchor='middle', textfont=dict(color='white', size=10)), row=1, col=1)
    marker_colors = np.where(data['Change %'] >= 0, '#2ca02c', '#d62728')
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Close'], name='Harga', customdata=data[['Change %']], hovertemplate='<b>%{x|%d %b %Y}</b><br>Harga: %{y:,.0f}<br>Change: %{customdata[0]:.2f}%<extra></extra>', line=dict(color='white', width=2), mode='lines+markers', marker=dict(color=marker_colors, size=6, line=dict(width=1, color='white'))), secondary_y=True, row=1, col=1)
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Frequency'], name='Frekuensi', mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'), row=2, col=1)
    max_vol, max_price, min_price = (data['Volume'].max(), data['Close'].max(), data['Close'].min()) if not data.empty else (1, 1, 0)
    if max_price == min_price: price_range_min, price_range_max = (min_price * 0.95, max_price * 1.05)
    else:
        proportion, price_data_range = 0.70, max_price - min_price
        price_total_range = price_data_range / proportion
        price_range_max, price_range_min = (max_price + (price_data_range * 0.05), (max_price + (price_data_range * 0.05)) - price_total_range)
    fig.update_layout(title_text=title, title_font_size=22, template='plotly_dark', barmode='stack', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14)))
    fig.update_xaxes(tickfont_size=12)
    fig.update_yaxes(title_font_size=16, tickfont_size=12)
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1, range=[0, max_vol * 1.05])
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, showgrid=False, range=[price_range_min, price_range_max])
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

# --- Tampilan Utama dengan Tab ---
tab_top25, tab_chart, tab_screener = st.tabs(["🏆 Top 25 Saham Potensial", "📊 Analisis Detail", "🔥 Screener Volume & Value"])

with tab_top25:
    # ... (Tidak ada perubahan di tab ini)
    st.header("Top 25 Saham Paling Potensial Hari Ini")
    st.markdown("Saham-saham ini diurutkan berdasarkan **Sistem Skor Cerdas** yang menggabungkan sinyal akumulasi, lonjakan volume, aliran dana asing, dan momentum harga positif.")
    if not df.empty:
        latest_data = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
        latest_data['Vol_Factor'] = (latest_data['Volume'] / latest_data['MA20_vol']).replace([np.inf, -np.inf], 0).fillna(0)
        latest_data['Score'] = 0
        latest_data.loc[latest_data['Final Signal'] == 'Strong Akumulasi', 'Score'] += 4
        latest_data.loc[latest_data['Final Signal'] == 'Akumulasi', 'Score'] += 2
        latest_data.loc[latest_data['Vol_Factor'] >= 10, 'Score'] += 3
        latest_data.loc[(latest_data['Vol_Factor'] >= 5) & (latest_data['Vol_Factor'] < 10), 'Score'] += 2
        latest_data.loc[latest_data['Foreign Flow Signal'] == 'Inflow', 'Score'] += 2
        latest_data.loc[latest_data['Change %'] > 0, 'Score'] += 1
        top_25_df = latest_data.sort_values(by='Score', ascending=False).head(25)
        st.success(f"Menampilkan **{len(top_25_df)}** saham teratas berdasarkan data tanggal **{latest_data['Last Trading Date'].max().strftime('%d %b %Y')}**")
        display_cols = ['Stock Code', 'Close', 'Change %', 'Score', 'Final Signal', 'Vol_Factor', 'Foreign Flow Signal']
        rename_cols = {'Stock Code': 'Saham', 'Final Signal': 'Sinyal Utama', 'Vol_Factor': 'Vol x MA20', 'Foreign Flow Signal': 'Foreign Flow'}
        format_dict = {'Close': "{:,.0f}", 'Change %': "{:,.2f}%", 'Score': "{:,.0f} Poin", 'Vol x MA20': "{:,.1f}x"}
        st.dataframe(top_25_df[display_cols].rename(columns=rename_cols).style.format(format_dict).background_gradient(cmap='Greens', subset=['Score']), use_container_width=True)
    else: st.warning("Data tidak tersedia untuk menampilkan Top 25.")

with tab_chart:
    st.sidebar.header("🔍 Filter Analisis Detail")
    st.sidebar.divider()
    if not df.empty:
        all_stocks = sorted(df['Stock Code'].unique())
        selected_stock = st.sidebar.selectbox("1. Pilih Kode Saham", all_stocks, index=all_stocks.index("BBRI") if "BBRI" in all_stocks else 0, key="stock_selector")
        stock_data = df[df["Stock Code"] == selected_stock].copy()
        
        if not stock_data.empty:
            latest_day_data = stock_data.iloc[-1]
            st.header(f"Analisis Detail: {selected_stock}")
            st.subheader(f"Ringkasan Hari Terakhir ({latest_day_data['Last Trading Date'].strftime('%d %b %Y')})")
            def get_status_display(signal):
                if signal == "Strong Akumulasi": return "🚀 Strong Akumulasi"
                if signal == "Akumulasi": return "🟢 Akumulasi"
                if signal == "Strong Distribusi": return "📉 Strong Distribusi"
                if signal == "Distribusi": return "🔴 Distribusi"
                return "⚪️ Netral"
            vol_factor = latest_day_data['Volume'] / latest_day_data['MA20_vol'] if latest_day_data['MA20_vol'] > 0 else 0
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label="Status Terkini", value=get_status_display(latest_day_data.get('Final Signal', 'N/A')))
            kpi2.metric(label="Net Foreign Flow", value=f"{latest_day_data.get('Net Foreign Flow', 0):,.0f}")
            kpi3.metric(label="Lonjakan Volume (vs MA20)", value=f"{vol_factor:.1f}x")
            kpi4.metric(label="Sektor", value=latest_day_data.get('Sector', 'N/A'))
            st.divider()

        # --- PERBAIKAN: Logika Filter Minggu Cerdas ---
        if not stock_data.empty and 'Week' in stock_data.columns:
            stock_data['Month_Year_Display'] = stock_data['Last Trading Date'].dt.strftime('%b-%Y')
            stock_data['Month_Year_Sort'] = stock_data['Last Trading Date'].dt.strftime('%Y-%m')
            month_year_df = stock_data[['Month_Year_Sort', 'Month_Year_Display']].drop_duplicates().sort_values(by='Month_Year_Sort', ascending=False)
            available_months = month_year_df['Month_Year_Display'].tolist()
            
            # Inisialisasi session state
            if 'last_selected_month' not in st.session_state:
                st.session_state.last_selected_month = None
            
            selected_month = st.sidebar.selectbox("2. Pilih Bulan-Tahun", available_months, key="month_selector")
            
            # Logika untuk mereset pilihan minggu jika bulan berubah
            if st.session_state.last_selected_month != selected_month:
                st.session_state.selected_weeks = []
                st.session_state.last_selected_month = selected_month

            weeks_in_month = sorted(stock_data[stock_data['Month_Year_Display'] == selected_month]['Week'].unique(), reverse=True)
            
            btn_col1, btn_col2 = st.sidebar.columns(2)
            if btn_col1.button("Pilih Semua Minggu", key="select_all_weeks", use_container_width=True):
                st.session_state.selected_weeks = weeks_in_month
                st.rerun()
            if btn_col2.button("Hapus Pilihan", key="clear_weeks", use_container_width=True):
                st.session_state.selected_weeks = []
                st.rerun()
            
            selected_weeks = st.sidebar.multiselect(
                "3. Pilih Minggu", weeks_in_month, 
                key='selected_weeks_multiselect', # Ganti key agar tidak konflik
                default=st.session_state.get('selected_weeks', [])
            )
            st.session_state.selected_weeks = selected_weeks # Simpan pilihan terbaru
        else:
            selected_weeks = []
        
        st.sidebar.divider()
        if st.sidebar.button("🔄 Perbarui Data", use_container_width=True): st.cache_data.clear(); st.rerun()
        
        if selected_weeks:
            filtered_daily_data = stock_data[stock_data['Week'].isin(selected_weeks)]
            st.markdown(f"##### Menampilkan data untuk minggu: **{', '.join(sorted(selected_weeks))}**")
            create_aligned_chart(data=filtered_daily_data, x_axis_col='Last Trading Date', title="Grafik Detail Harian")
        else: st.info("Pilih setidaknya satu minggu dari sidebar untuk menampilkan data.")
    else: st.warning("Gagal memuat data.")

with tab_screener:
    st.header("Screener Saham Berdasarkan Lonjakan Volume & Value")
    st.markdown("Cari saham yang menunjukkan **lonjakan volume/nilai hari ini** dibandingkan rata-rata 20 hari sebelumnya.")
    if not df.empty:
        latest_data_screener = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
        filter_col1, filter_col2 = st.columns([2,1])
        with filter_col1:
            filter_vol = st.checkbox("Filter Lonjakan Volume", value=True, key="vol_filter")
            filter_val = st.checkbox("Filter Lonjakan Nilai", value=False, key="val_filter")
        with filter_col2:
            multiplier = st.number_input("Minimal Kenaikan (x lipat)", min_value=1.0, value=5.0, step=0.5, key="multiplier")
        latest_data_screener['Vol_Factor'] = (latest_data_screener['Volume'] / latest_data_screener['MA20_vol']).replace([np.inf, -np.inf], 0).fillna(0)
        latest_data_screener['Val_Factor'] = (latest_data_screener['Value'] / latest_data_screener['MA20_val']).replace([np.inf, -np.inf], 0).fillna(0)
        conditions = []
        if filter_vol: conditions.append(latest_data_screener['Vol_Factor'] >= multiplier)
        if filter_val: conditions.append(latest_data_screener['Val_Factor'] >= multiplier)
        st.divider()
        if conditions:
            final_condition = pd.concat(conditions, axis=1).any(axis=1)
            result_df = latest_data_screener[final_condition].copy()
            result_df.sort_values(by='Vol_Factor', ascending=False, inplace=True)
            st.success(f"Ditemukan **{len(result_df)}** saham yang memenuhi kriteria.")
            screen_width = streamlit_js_eval(js_expressions='screen.width', key='SCR_WIDTH')
            is_mobile = (screen_width < 768) if screen_width is not None else False
            mobile_cols, desktop_cols = ['Stock Code', 'Close', 'Change %', 'Vol_Factor'], ['Stock Code', 'Close', 'Change %', 'Volume', 'Vol_Factor', 'MA20_vol', 'Value', 'Val_Factor', 'MA20_val']
            rename_cols = {'Stock Code': 'Saham', 'Vol_Factor': 'Vol x MA20', 'MA20_vol': 'Rata2 Vol 20D', 'Val_Factor': 'Val x MA20', 'MA20_val': 'Rata2 Val 20D'}
            format_dict = {'Close': "{:,.0f}", 'Change %': "{:,.2f}%", 'Volume': "{:,.0f}", 'Vol x MA20': "{:,.1f}x", 'Rata2 Vol 20D': "{:,.0f}", 'Value': "{:,.0f}", 'Val x MA20': "{:,.1f}x", 'Rata2 Val 20D': "{:,.0f}"}
            if is_mobile:
                st.dataframe(result_df[mobile_cols].rename(columns=rename_cols).style.format(format_dict).background_gradient(cmap='Greens', subset=['Vol x MA20']), use_container_width=True)
                with st.expander("Tampilkan Detail Tabel"):
                    st.dataframe(result_df[desktop_cols].rename(columns=rename_cols).style.format(format_dict).background_gradient(cmap='Greens', subset=['Vol x MA20', 'Val x MA20']), use_container_width=True)
            else:
                st.dataframe(result_df[desktop_cols].rename(columns=rename_cols).style.format(format_dict).background_gradient(cmap='Greens', subset=['Vol x MA20', 'Val x MA20']), use_container_width=True)
        else: st.info("Pilih setidaknya satu kriteria di atas untuk memulai screening.")
    else: st.warning("Data tidak tersedia untuk melakukan screening.")
