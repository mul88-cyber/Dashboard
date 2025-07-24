import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Saham Optimal", layout="wide")
st.title("🚀 Dashboard Analisis Saham Optimal")

# --- Load Data ---
@st.cache_data(ttl=3600)
def load_data():
    """Memuat dan membersihkan data dari URL."""
    csv_url = "https://storage.googleapis.com/stock-csvku/hasil_gabungan.csv"
    try:
        df = pd.read_csv(csv_url)
        df['Last Trading Date'] = pd.to_datetime(df['Last Trading Date'])
        
        # Kolom numerik yang dibutuhkan
        numeric_cols = ['Volume', 'Close', 'Foreign Buy', 'Foreign Sell', 'Frequency']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Menambahkan data sektor (dummy)
        sektors = ['FINANCE', 'TECHNOLOGY', 'INFRASTRUCTURE', 'ENERGY', 'HEALTHCARE', 'INDUSTRY', 'CONSUMER']
        df['Sector'] = df.groupby('Stock Code')['Stock Code'].transform(lambda x: sektors[hash(x.name) % len(sektors)])
        
        # Mengisi nilai kosong sebelum mengubah tipe data untuk menghindari error
        df.fillna(0, inplace=True)
        df['Sector'] = df['Sector'].astype('category')
        
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
    stocks_in_sector = sorted(df[df['Sector'] == selected_sector]['Stock Code'].unique())
    selected_stock = st.sidebar.selectbox("Pilih Kode Saham", stocks_in_sector)
    
    if st.sidebar.button("🔄 Perbarui Data"):
        st.cache_data.clear()
        st.rerun()

    stock_data = df[df["Stock Code"] == selected_stock]
else:
    st.warning("Gagal memuat data. Aplikasi tidak dapat berjalan.")
    stock_data = pd.DataFrame()

# --- Fungsi Grafik ---
def create_combined_chart(data, x_axis_col, title):
    """Membuat grafik gabungan untuk Harga, Volume, dan Frekuensi."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sumbu Y Kiri: Volume (Bar) & Frequency (Bar)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Volume'], name='Volume', marker_color='royalblue', opacity=0.5), secondary_y=False)
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Frequency'], name='Frequency', marker_color='orange', opacity=0.5), secondary_y=False)

    # Sumbu Y Kanan: Close Price (Line)
    fig.add_trace(go.Scatter(x=data[x_axis_col], y=data['Close'], name='Close Price', line=dict(color='white', width=2)), secondary_y=True)

    fig.update_layout(
        title_text=title,
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode='stack'
    )
    fig.update_yaxes(title_text="Volume & Frekuensi", secondary_y=False)
    fig.update_yaxes(title_text="Harga Penutupan (Rp)", secondary_y=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

def create_foreign_flow_chart(data, x_axis_col, title):
    """Membuat grafik khusus untuk Foreign Flow."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Buy'], name='Foreign Buy', marker_color='green'))
    fig.add_trace(go.Bar(x=data[x_axis_col], y=data['Foreign Sell'], name='Foreign Sell', marker_color='red'))
    fig.update_layout(
        title_text=title,
        barmode='group',
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Nilai Transaksi")
    st.plotly_chart(fig, use_container_width=True)

# --- Tampilan Utama dengan Tab ---
tab_harian, tab_mingguan = st.tabs(["📈 Analisis Harian", "📅 Analisis Mingguan"])

with tab_harian:
    if not stock_data.empty:
        st.header(f"Analisis Harian: {selected_stock}")
        # Menampilkan 90 hari terakhir untuk default view
        daily_data = stock_data[stock_data['Last Trading Date'] >= (stock_data['Last Trading Date'].max() - pd.Timedelta(days=90))]
        create_combined_chart(daily_data, 'Last Trading Date', "Harga, Volume, & Frekuensi Harian")
        create_foreign_flow_chart(daily_data, 'Last Trading Date', "Aliran Dana Asing Harian")
    else:
        st.info("Silakan pilih saham di sidebar.")

with tab_mingguan:
    if not stock_data.empty and 'Week' in stock_data.columns:
        st.header(f"Analisis Mingguan: {selected_stock}")
        
        # Agregasi data mingguan menggunakan kolom 'Week'
        weekly_data = stock_data.groupby('Week').agg(
            Close=('Close', 'last'),
            Volume=('Volume', 'sum'),
            Foreign_Buy=('Foreign Buy', 'sum'),
            Foreign_Sell=('Foreign Sell', 'sum'),
            Frequency=('Frequency', 'sum')
        ).reset_index()

        # Rename kolom agar sesuai dengan fungsi chart
        weekly_data.rename(columns={'Foreign_Buy': 'Foreign Buy', 'Foreign_Sell': 'Foreign Sell'}, inplace=True)
        
        create_combined_chart(weekly_data, 'Week', "Harga, Volume, & Frekuensi Mingguan")
        create_foreign_flow_chart(weekly_data, 'Week', "Aliran Dana Asing Mingguan")
    else:
        st.info("Silakan pilih saham di sidebar atau data tidak memiliki kolom 'Week'.")
