import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.preprocessing import MinMaxScaler # Library baru untuk normalisasi

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Pro", layout="wide")
st.title("🚀 Dashboard Analisis Saham Pro")

# --- Load Data ---
@st.cache_data(ttl=3600)
def load_data():
    """Memuat dan membersihkan data dari URL."""
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
        numeric_cols = ['Volume', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(0, inplace=True)
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        df.sort_values(by="Last Trading Date", inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik Inovatif ---
def create_normalized_chart(data, x_axis_col, title):
    """
    Membuat grafik dengan data yang dinormalisasi untuk visualisasi yang sejajar.
    """
    if data.empty or len(data) < 2:
        st.warning("Data tidak cukup untuk membuat grafik normalisasi.")
        return

    # Salin data agar tidak mengubah data asli
    plot_data = data.copy()

    # Inisialisasi Scaler
    scaler = MinMaxScaler(feature_range=(0, 100))

    # Normalisasi Volume dan Harga ke skala 0-100
    plot_data['Volume_scaled'] = scaler.fit_transform(plot_data[['Volume']])
    plot_data['Close_scaled'] = scaler.fit_transform(plot_data[['Close']])
    
    # Buat teks hover untuk menampilkan data asli
    plot_data['text_volume'] = plot_data['Volume'].apply(lambda x: f'{x:,.0f}')
    plot_data['text_price'] = plot_data['Close'].apply(lambda x: f'Rp {x:,.0f}')

    # --- Pembuatan Grafik ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # GRAFIK ATAS (NORMALISASI)
    # Tampilkan bar volume yang sudah dinormalisasi
    fig.add_trace(go.Bar(
        x=plot_data[x_axis_col],
        y=plot_data['Volume_scaled'],
        name='Volume',
        text=plot_data['text_volume'],
        hoverinfo='x+text+name',
        marker_color='royalblue',
        opacity=0.6
    ), row=1, col=1)

    # Tampilkan garis harga yang sudah dinormalisasi
    fig.add_trace(go.Scatter(
        x=plot_data[x_axis_col],
        y=plot_data['Close_scaled'],
        name='Harga',
        text=plot_data['text_price'],
        hoverinfo='x+text+name',
        line=dict(color='white', width=2.5)
    ), row=1, col=1)
    
    # GRAFIK BAWAH (FREKUENSI - tidak perlu normalisasi)
    fig.add_trace(go.Scatter(
        x=plot_data[x_axis_col], y=plot_data['Frequency'], name='Frekuensi',
        mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'
    ), row=2, col=1)

    # LAYOUT
    fig.update_layout(
        title_text=title, title_font_size=22, template='plotly_dark', height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=14)
    )
    fig.update_yaxes(title_text="Skala Normalisasi (0-100)", row=1, col=1, title_font_size=16, tickfont_size=12, range=[0, 105])
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1, title_font_size=16, tickfont_size=12)
    fig.update_xaxes(tickfont_size=12)

    st.plotly_chart(fig, use_container_width=True)

# --- Sidebar & Tampilan Utama (Tidak ada perubahan) ---
st.sidebar.header("🔍 Filter")
st.sidebar.divider()
if not df.empty:
    all_stocks = sorted(df['Stock Code'].unique())
    selected_stock = st.sidebar.selectbox("1. Pilih Kode Saham", all_stocks, index=all_stocks.index("BBRI") if "BBRI" in all_stocks else 0)
    stock_data = df[df["Stock Code"] == selected_stock]
    if not stock_data.empty and 'Week' in stock_data.columns:
        week_mapping = stock_data.groupby('Week')['Last Trading Date'].max().reset_index()
        sorted_weeks_df = week_mapping.sort_values(by='Last Trading Date', ascending=False)
        available_weeks = sorted_weeks_df['Week'].tolist()
        selected_weeks = st.sidebar.multiselect(
            "2. Pilih Minggu (bisa lebih dari satu)",
            options=available_weeks,
            default=available_weeks[:4] if len(available_weeks) > 4 else available_weeks
        )
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
        create_normalized_chart(
            data=filtered_daily_data,
            x_axis_col='Last Trading Date',
            title=f"Analisis Normalisasi untuk {selected_stock}"
        )
    else:
        st.info("Pilih setidaknya satu minggu dari sidebar untuk menampilkan data.")
else:
    st.warning("Gagal memuat data.")
