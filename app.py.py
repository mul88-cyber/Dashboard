import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_js_eval import streamlit_js_eval
from streamlit_copy_button import copy_button # PERBAIKAN: Import library yang benar

# --- Konfigurasi Halaman & CSS Kustom ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.markdown("""
<style>
/* CSS Kustom */
button[data-baseweb="tab"] {
    font-size: 18px; font-weight: bold; padding-top: 10px !important; padding-bottom: 10px !important;
}
div[data-testid="stMetricValue"] { font-size: 22px; }
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

# --- Fungsi Grafik ---
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
                if group.empty or len(group) < 2: continue
                latest_row = group.iloc[-1]
                latest_date_stock = latest_row['Last Trading Date']
                
                def get_perf(offset):
                    past_date = latest_date_stock - offset
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
            eligible_stocks.loc[latest_data['Change %'] > 0, 'Score'] += 1
            
            top_25_df = eligible_stocks.sort_values(by=['Score', 'Vol_Factor'], ascending=False).head(25)

        st.success(f"Ditemukan **{len(top_25_df)}** saham potensial (dari {len(eligible_stocks)} yang lolos filter risiko).")
        
        if not top_25_df.empty:
            codes_to_copy = "\n".join(top_25_df['Stock Code'].tolist())
            # PERBAIKAN: Panggil fungsi dari library yang benar
            copy_button(codes_to_copy, "Salin 25 Kode Saham")
            st.write("")

        display_cols = ['Stock Code', 'Company Name', 'Close', 'Change %', 'Score', 'Final Signal', 'Vol_Factor', 'Foreign Flow Signal']
        rename_cols = {'Stock Code': 'Saham', 'Company Name': 'Nama Perusahaan', 'Final Signal': 'Sinyal Utama', 'Vol_Factor': 'Vol x MA20', 'Foreign Flow Signal': 'Foreign Flow'}
        df_to_display = top_25_df[display_cols].rename(columns=rename_cols)

        response = create_interactive_table(df_to_display, 'top25_table')
        if response['selected_rows'] is not None and not response['selected_rows'].empty:
            selected_code = response['selected_rows'].iloc[0]['Saham']
            if st.session_state.selected_stock != selected_code:
                st.session_state.selected_stock = selected_code
                st.warning(f"Saham {st.session_state.selected_stock} dipilih. Silakan pindah ke tab 'Analisis Detail'.")
                st.rerun()
    else:
        st.warning("Data tidak tersedia.")

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
            df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
            latest_day_data = stock_data.iloc[-1]
            company_name = latest_day_data.get('Company Name', selected_stock)
            st.markdown(f"### Analisis Detail: {selected_stock} - {company_name}")
            st.markdown(f"**Ringkasan Hari Terakhir ({latest_day_data['Last Trading Date'].strftime('%d %b %Y')})**")
            
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

        if not stock_data.empty and 'Week' in stock_data.columns:
            stock_data['Month_Year_Display'] = stock_data['Last Trading Date'].dt.strftime('%b-%Y')
            stock_data['Month_Year_Sort'] = stock_data['Last Trading Date'].dt.strftime('%Y-%m')
            month_year_df = stock_data[['Month_Year_Sort', 'Month_Year_Display']].drop_duplicates().sort_values(by='Month_Year_Sort', ascending=False)
            available_months = month_year_df['Month_Year_Display'].tolist()
            selected_months = st.sidebar.multiselect("2. Pilih Bulan-Tahun", available_months, key="selected_months", default=available_months[0] if available_months else None)
            if selected_months: weeks_in_months = sorted(stock_data[stock_data['Month_Year_Display'].isin(selected_months)]['Week'].unique(), reverse=True)
            else: weeks_in_months = []
            if 'selected_weeks' in st.session_state: st.session_state.selected_weeks = [w for w in st.session_state.selected_weeks if w in weeks_in_months]
            btn_col1, btn_col2 = st.sidebar.columns(2)
            if btn_col1.button("Pilih Semua Minggu", key="select_all_weeks", use_container_width=True): st.session_state.selected_weeks = weeks_in_months; st.rerun()
            if btn_col2.button("Hapus Pilihan", key="clear_weeks", use_container_width=True): st.session_state.selected_weeks = []; st.rerun()
            selected_weeks = st.sidebar.multiselect("3. Pilih Minggu", weeks_in_months, key='selected_weeks')
        else:
            selected_weeks = []
        
        st.sidebar.divider()
        if st.sidebar.button("🔄 Perbarui Data", use_container_width=True): st.cache_data.clear(); st.rerun()
        
        if selected_weeks:
            filtered_daily_data = stock_data[stock_data['Week'].isin(selected_weeks)]
            st.caption(f"Menampilkan data untuk minggu: **{', '.join(sorted(selected_weeks))}**")
            create_aligned_chart(data=filtered_daily_data, x_axis_col='Last Trading Date', title="")
        else: st.info("Pilih setidaknya satu bulan dan minggu dari sidebar untuk menampilkan data.")
    else:
        st.warning("Gagal memuat data.")

with tab_screener:
    st.header("Screener Saham Berdasarkan Lonjakan Volume & Value")
    st.markdown("Cari saham yang menunjukkan **lonjakan volume/nilai hari ini** dibandingkan rata-rata 20 hari sebelumnya.")
    if not df.empty:
        latest_data_screener = df.loc[df.groupby('Stock Code')['Last Trading Date'].idxmax()].copy()
        filter_col1, filter_col2 = st.columns([2,1])
        with filter_col1:
            filter_vol = st.checkbox("Filter Lonjakan Volume", value=True, key="vol_filter")
            filter_val = st.checkbox("Filter Lonjakan Nilai", value=False, key="val_filter")
        with filter_col2: multiplier = st.number_input("Minimal Kenaikan (x lipat)", min_value=1.0, value=5.0, step=0.5, key="multiplier")
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
            mobile_cols = ['Stock Code', 'Close', 'Change %', 'Vol_Factor']
            desktop_cols = ['Stock Code', 'Close', 'Change %', 'Volume', 'Vol_Factor', 'MA20_vol', 'Value', 'Val_Factor', 'MA20_val']
            rename_cols = {'Stock Code': 'Saham', 'Vol_Factor': 'Vol x MA20', 'MA20_vol': 'Rata2 Vol 20D', 'Val_Factor': 'Val x MA20', 'MA20_val': 'Rata2 Val 20D'}
            
            df_to_display_screener = result_df[desktop_cols if not is_mobile else mobile_cols].rename(columns=rename_cols)
            response_screener = create_interactive_table(df_to_display_screener, 'screener_table')

            if response_screener['selected_rows'] is not None and not response_screener['selected_rows'].empty:
                selected_code = response_screener['selected_rows'].iloc[0]['Saham']
                if st.session_state.selected_stock != selected_code:
                    st.session_state.selected_stock = selected_code
                    st.warning(f"Saham {st.session_state.selected_stock} dipilih. Silakan pindah ke tab 'Analisis Detail'.")
                    st.rerun()
        else:
            st.info("Pilih setidaknya satu kriteria di atas untuk memulai screening.")
    else:
        st.warning("Data tidak tersedia untuk melakukan screening.")
