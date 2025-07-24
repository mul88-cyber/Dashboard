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

# --- Fungsi Grafik Final ---
def create_aligned_chart(data, x_axis_col, title):
    """
    Membuat grafik combo dengan sumbu nol yang sejajar secara visual
    menggunakan metode rentang proporsional yang stabil.
    """
    if data.empty:
        st.warning("Tidak ada data untuk rentang minggu yang dipilih.")
        return

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}], [{}]])

    # Grafik Atas: Harga & Volume
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Local Volume'], name='Lokal', marker_color='#1f77b4'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Asing Beli', marker_color='#2ca02c'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Asing Jual', marker_color='#d62728'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Close'], name='Harga', line=dict(color='white', width=2)), secondary_y=True, row=1, col=1)

    # Grafik Bawah: Frekuensi
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Frequency'], name='Frekuensi',
                           mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'), row=2, col=1)

    # --- PERBAIKAN FINAL: Logika Rentang Sumbu Y Proporsional ---
    max_vol = data['Volume'].max() if not data['Volume'].empty else 1
    max_price = data['Close'].max() if not data['Close'].empty else 1
    min_price = data['Close'].min() if not data['Close'].empty else 0

    # Handle kasus jika semua harga sama untuk menghindari pembagian dengan nol
    if max_price == min_price:
        price_range_min = min_price * 0.95
        price_range_max = max_price * 1.05
    else:
        # Data harga akan menempati 70% bagian atas dari total rentang sumbu Y-nya
        proportion = 0.70
        price_data_range = max_price - min_price
        price_total_range = price_data_range / proportion
        
        # Tambahkan sedikit padding di atas
        price_range_max = max_price + (price_data_range * 0.05)
        price_range_min = price_range_max - price_total_range

    fig.update_layout(
        title_text=title, title_font_size=22, template='plotly_dark', height=600, barmode='stack',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14))
    )
    fig.update_xaxes(tickfont_size=12)
    fig.update_yaxes(title_font_size=16, tickfont_size=12)

    # Terapkan rentang yang sudah dihitung
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1, range=[0, max_vol * 1.05])
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, showgrid=False, range=[price_range_min, price_range_max])
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)

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
        create_aligned_chart(
            data=filtered_daily_data,
            x_axis_col='Last Trading Date',
            title=f"Analisis Detail Harian untuk {selected_stock}"
        )
    else:
        st.info("Pilih setidaknya satu minggu dari sidebar untuk menampilkan data.")
else:
    st.warning("Gagal memuat data.")
