# --- Fungsi Grafik Optimal ---
def create_optimal_chart(data, x_axis_col, title):
    """Membuat grafik combo dengan sumbu nol yang sejajar."""
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

    # --- PERBAIKAN: Menyejajarkan Garis Nol ---
    # Dapatkan nilai maksimum dari setiap sumbu
    max_vol = data['Volume'].max()
    max_price = data['Close'].max()
    min_price = data['Close'].min()

    # Hitung rentang bawah agar proporsional
    # Jika harga minimum jauh di atas nol, kita buat ruang di bawahnya
    # agar 'nol' nya sejajar dengan 'nol' volume
    if min_price > 0 and max_price > 0:
        price_range_bottom = - (min_price / (max_price - min_price)) * max_vol
    else:
        price_range_bottom = 0

    fig.update_layout(
        title_text=title,
        title_font_size=22,
        template='plotly_dark',
        height=600,
        barmode='stack',
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=14)
        ),
        # Atur rentang sumbu Y utama (Volume) dari 0 ke atas
        yaxis_range=[0, max_vol * 1.1]
    )

    # Atur font untuk semua sumbu
    fig.update_yaxes(title_font_size=16, tickfont_size=12)
    fig.update_xaxes(tickfont_size=12)

    # Beri nama dan atur rentang sumbu Y
    fig.update_yaxes(title_text="Volume", secondary_y=False, row=1, col=1)
    fig.update_yaxes(
        title_text="Harga (Rp)",
        secondary_y=True,
        row=1, col=1,
        showgrid=False,
        # Atur rentang sumbu Y kedua (Harga) dengan trik matematika
        range=[price_range_bottom, max_price * 1.1]
    )
    fig.update_yaxes(title_text="Frekuensi", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
