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

        sektors = ['FINANCE', 'TECHNOLOGY', 'INFRASTRUCTURE', 'ENERGY', 'HEALTHCARE', 'INDUSTRY', 'CONSUMER']
        df['Sector'] = df.groupby('Stock Code')['Stock Code'].transform(lambda x: sektors[hash(x.name) % len(sektors)])
        
        df.fillna(0, inplace=True)
        df['Sector'] = df['Sector'].astype('category')
        
        # Hitung volume lokal di awal
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        
        df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Sidebar Filter ---
st.sidebar.header("🔍 Filter Data")
if not df.empty:
    selected_sector = st.sidebar.selectbox("Pilih Sektor", sorted(df['Sector'].unique()))
    # Menghindari error jika ada stock code kosong
    stocks_in_sector = sorted(df[df['Stock Code'].str.strip() != ''][df['Sector'] == selected_sector]['Stock Code'].unique())
    selected_stock = st.sidebar.selectbox("Pilih Kode Saham", stocks_in_sector)
    
    if st.sidebar.button("🔄 Perbarui Data"):
        st.cache_data.clear()
        st.rerun()

    stock_data = df[df["Stock Code"] == selected_stock]
else:
    st.warning("Gagal memuat data. Aplikasi tidak dapat berjalan.")
    stock_data = pd.DataFrame()

# --- Fungsi Grafik Optimal ---
def create_optimal_chart(data, x_axis_col, title):
    """
    Membuat grafik combo dengan secondary axis yang sudah dideklarasikan dengan benar.
    """
    # --- PERBAIKAN KUNCI: Deklarasikan 'specs' untuk mendaftarkan secondary_y ---
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, 
        vertical_spacing=0.05, row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}],  # Baris 1 punya 2 sumbu Y
               [{}]])                    # Baris 2 normal

    # --- GRAFIK ATAS (Harga & Volume) ---
    # Sumbu Y1 (Kiri) untuk Volume
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Local Volume'], name='Lokal', marker_color='#1f77b4'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Asing Beli', marker_color='#2ca02c'), row=1, col=1)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Asing Jual', marker_color='#d62728'), row=1, col=1)
    
    # Sumbu Y2 (Kanan) untuk Harga
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Close'], name='Harga', line=dict(color='white', width=2)), secondary_y=True, row=1, col=1)

    # --- GRAFIK BAWAH (Frekuensi) ---
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Frequency'], name='Frekuensi', 
                           mode='lines', line=dict(color='#ff7f0e', width=2), fill='tozeroy'), row=2, col=1)

    fig.update_layout(
        title_text=title,
        template='plotly_dark',
        height=600,
        barmode='stack',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Update Sumbu Y Grafik Atas
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, showgrid=False)

    # Update Sumbu Y Grafik Bawah
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# --- Tampilan Utama dengan Tab ---
tab_harian, tab_mingguan = st.tabs(["📈 Analisis Harian", "📅 Analisis Mingguan"])

with tab_harian:
    if not stock_data.empty:
        st.header(f"Analisis Harian: {selected_stock}")
        daily_data = stock_data[stock_data['Last Trading Date'] >= (stock_data['Last Trading Date'].max() - pd.Timedelta(days=120))]
        # Tab Harian PASTI menggunakan 'Last Trading Date'
        create_optimal_chart(daily_data, 'Last Trading Date', "Analisis Harga, Volume & Frekuensi Harian")
    else:
        st.info("Silakan pilih saham di sidebar.")

with tab_mingguan:
    if not stock_data.empty and 'Week' in stock_data.columns:
        st.header(f"Analisis Mingguan: {selected_stock}")
        
        # Agregasi data mingguan
        weekly_data = stock_data.groupby('Week').agg(
            Last_Date=('Last Trading Date', 'last'), # Ambil tanggal terakhir untuk sorting
            Close=('Close', 'last'),
            Local_Volume=('Local Volume', 'sum'),
            Foreign_Buy=('Foreign Buy', 'sum'),
            Foreign_Sell=('Foreign Sell', 'sum'),
            Frequency=('Frequency', 'sum')
        ).reset_index()

        # Mengurutkan berdasarkan tanggal terakhir di minggu itu untuk memastikan urutan benar
        weekly_data.sort_values('Last_Date', inplace=True)
        
        # Tab Mingguan PASTI menggunakan kolom 'Week'
        create_optimal_chart(weekly_data, 'Week', "Analisis Harga, Volume & Frekuensi Mingguan")
    else:
        st.info("Silakan pilih saham di sidebar.")
