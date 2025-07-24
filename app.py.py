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
        
        df['Local Volume'] = df['Volume'] - (df['Foreign Buy'] + df['Foreign Sell'])
        
        df.sort_values(by=["Stock Code", "Last Trading Date"], inplace=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari URL: {e}")
        return pd.DataFrame()

df = load_data()

# --- Fungsi Grafik Optimal ---
def create_optimal_chart(data, x_axis_col, title):
    """Membuat grafik combo untuk data harian yang sudah difilter."""
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

    fig.update_layout(
        title_text=title, template='plotly_dark', height=600, barmode='stack',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Harga (Rp)", secondary_y=True, row=1, col=1, showgrid=False)
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

# --- Sidebar Filter ---
st.sidebar.header("🔍 Filter Data")
if not df.empty:
    selected_sector = st.sidebar.selectbox("1. Pilih Sektor", sorted(df['Sector'].unique()))
    
    stocks_in_sector = sorted(df[df['Stock Code'].str.strip() != ''][df['Sector'] == selected_sector]['Stock Code'].unique())
    selected_stock = st.sidebar.selectbox("2. Pilih Kode Saham", stocks_in_sector)
    
    # Filter data berdasarkan saham yang dipilih
    stock_data = df[df["Stock Code"] == selected_stock]
    
    # Ambil daftar minggu yang unik dan urutkan
    available_weeks = sorted(stock_data['Week'].unique(), reverse=True)
    
    # Filter Minggu (Multi-select)
    selected_weeks = st.sidebar.multiselect(
        "3. Pilih Minggu (bisa lebih dari satu)",
        options=available_weeks,
        default=available_weeks[:4] if len(available_weeks) > 4 else available_weeks # Default 4 minggu terakhir
    )

    if st.sidebar.button("🔄 Perbarui Data"):
        st.cache_data.clear()
        st.rerun()

    # --- Tampilan Utama ---
    if selected_weeks:
        # Filter data harian berdasarkan minggu yang dipilih
        filtered_daily_data = stock_data[stock_data['Week'].isin(selected_weeks)]
        
        st.header(f"Analisis Harian untuk {selected_stock}")
        st.markdown(f"Menampilkan data untuk minggu: **{', '.join(selected_weeks)}**")
        
        create_optimal_chart(
            data=filtered_daily_data, 
            x_axis_col='Last Trading Date', 
            title=f"Analisis Detail Harian untuk {selected_stock}"
        )
    else:
        st.info("Pilih setidaknya satu minggu dari sidebar untuk menampilkan data.")

else:
    st.warning("Gagal memuat data. Aplikasi tidak dapat berjalan.")
