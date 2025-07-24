import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Simple", layout="wide")
st.title("📊 Dashboard Analisis Saham Sederhana")

# --- Load Data (menggunakan cache agar cepat) ---
@st.cache_data(ttl=3600)
def load_data():
    """
    Memuat data dari URL, mengkonversi tipe data, dan menambahkan data sektor.
    """
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])

        # Kolom numerik yang akan dikonversi, termasuk 'Frequency' dari data asli
        numeric_cols = ['Volume', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Menambahkan data sektor (karena tidak ada di file asli)
        sektors = ['FINANCE', 'TECHNOLOGY', 'INFRASTRUCTURE', 'ENERGY', 'HEALTHCARE', 'INDUSTRY', 'CONSUMER']
        df['Sector'] = df.groupby('Stock Code')['Stock Code'].transform(lambda x: sektors[hash(x.name) % len(sektors)])
        df['Sector'] = df['Sector'].astype('category')

        df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
        df.fillna(0, inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Sidebar untuk Filter ---
st.sidebar.header("🔍 Filter Data")

if not df.empty:
    # Filter Sektor
    unique_sectors = sorted(df['Sector'].unique())
    selected_sector = st.sidebar.selectbox(
        "Langkah 1: Pilih Sektor",
        options=unique_sectors
    )

    # Filter Kode Saham (berdasarkan sektor yang dipilih)
    stocks_in_sector = sorted(df[df['Sector'] == selected_sector]['Stock Code'].unique())
    selected_stock = st.sidebar.selectbox(
        "Langkah 2: Pilih Kode Saham",
        options=stocks_in_sector
    )

    # Tombol Refresh
    if st.sidebar.button("🔄 Perbarui Data"):
        st.cache_data.clear()
        st.rerun()

    # Filter data utama berdasarkan pilihan user
    stock_data = df[df["Stock Code"] == selected_stock].copy()

else:
    st.warning("Gagal memuat data saham. Aplikasi tidak dapat berjalan.")
    selected_stock = None
    stock_data = pd.DataFrame()

# --- Membuat Tab ---
tab_harian, tab_mingguan = st.tabs(["Analisis Harian", "Analisis Mingguan"])

# --- Fungsi untuk membuat grafik ---
def create_charts(data, title_suffix):
    """
    Membuat 4 grafik terpisah untuk Close, Volume, Foreign Flow, dan Frequency.
    """
    if data.empty:
        st.warning(f"Tidak ada data {title_suffix} untuk saham {selected_stock}.")
        return

    st.subheader(f"Grafik {title_suffix} untuk {selected_stock}")

    # 1. Grafik Harga Penutupan (Close Price)
    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(
        x=data['Last Trading Date'], y=data['Close'],
        mode='lines', name='Close Price', line=dict(color='cyan', width=2)
    ))
    fig_close.update_layout(
        title='Harga Penutupan (Close Price)',
        yaxis_title='Harga (Rp)', height=350, template='plotly_dark'
    )
    st.plotly_chart(fig_close, use_container_width=True)

    # 2. Grafik Volume
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        x=data['Last Trading Date'], y=data['Volume'],
        name='Volume', marker_color='royalblue'
    ))
    fig_vol.update_layout(
        title='Volume Transaksi',
        yaxis_title='Jumlah Lembar Saham', height=350, template='plotly_dark'
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    # 3. Grafik Aliran Dana Asing (Foreign Flow)
    fig_foreign = go.Figure()
    fig_foreign.add_trace(go.Bar(
        x=data['Last Trading Date'], y=data['Foreign Buy'],
        name='Foreign Buy', marker_color='green'
    ))
    fig_foreign.add_trace(go.Bar(
        x=data['Last Trading Date'], y=data['Foreign Sell'],
        name='Foreign Sell', marker_color='red'
    ))
    fig_foreign.update_layout(
        barmode='group',
        title='Aliran Dana Asing (Foreign Flow)',
        yaxis_title='Nilai Transaksi', height=350, template='plotly_dark'
    )
    st.plotly_chart(fig_foreign, use_container_width=True)

    # 4. Grafik Frekuensi
    fig_freq = go.Figure()
    fig_freq.add_trace(go.Bar(
        x=data['Last Trading Date'], y=data['Frequency'],
        name='Frequency', marker_color='orange'
    ))
    fig_freq.update_layout(
        title='Frekuensi Transaksi',
        yaxis_title='Jumlah Transaksi', height=350, template='plotly_dark'
    )
    st.plotly_chart(fig_freq, use_container_width=True)

# --- Konten Tab Harian ---
with tab_harian:
    if selected_stock and not stock_data.empty:
        # Menampilkan data 90 hari terakhir untuk default view
        daily_data = stock_data[stock_data['Last Trading Date'] >= (stock_data['Last Trading Date'].max() - pd.Timedelta(days=90))]
        create_charts(daily_data, "Harian")
    else:
        st.info("Silakan pilih saham di sidebar untuk memulai analisis.")

# --- Konten Tab Mingguan ---
with tab_mingguan:
    if selected_stock and not stock_data.empty:
        # Mengelompokkan data per minggu. 'W-FRI' berarti akhir minggu adalah hari Jumat.
        stock_data_weekly = stock_data.set_index('Last Trading Date').resample('W-FRI').agg({
            'Close': 'last',
            'Volume': 'sum',
            'Foreign Buy': 'sum',
            'Foreign Sell': 'sum',
            'Frequency': 'sum'
        }).reset_index()

        # Menghapus minggu yang tidak memiliki data (misal: di awal periode)
        stock_data_weekly = stock_data_weekly[stock_data_weekly['Volume'] > 0]

        create_charts(stock_data_weekly, "Mingguan")
    else:
        st.info("Silakan pilih saham di sidebar untuk memulai analisis.")
