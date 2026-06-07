import streamlit as st
import pandas as pd
import pymongo
import plotly.express as px
import re
from datetime import datetime

# ==========================================
# 1. KONFIGURASI HALAMAN UTAMA WEBSITE & TANGGAL
# ==========================================
st.set_page_config(page_title="Asisten Keuangan AI", page_icon="💰", layout="wide")

# Membuat format tanggal Indonesia secara manual agar rapi dan pasti Bahasa Indonesia
hari_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
bulan_indo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

now = datetime.now()
nama_hari = hari_indo[now.weekday()]
nama_bulan = bulan_indo[now.month - 1]
bulan_kode = now.strftime("%Y-%m")     # Kode untuk filter database (Contoh: "2026-06")

# Menggabungkan teks tanggal lengkap
tanggal_hari_ini = f"{nama_hari}, {now.day} {nama_bulan} {now.year}"
bulan_sekarang_tahun = f"{nama_bulan} {now.year}"

# Menampilkan Judul Utama dan Info Tanggal Real-time
st.title(f"💰 Dasbor Keuangan Cerdas ({bulan_sekarang_tahun})")
st.subheader(f"📅 Hari Ini: {tanggal_hari_ini}")
st.markdown("Data otomatis ter-reset setiap tanggal 1 awal bulan baru.")
st.markdown("---")

# ==========================================
# 2. KONEKSI DATABASE MONGODB
# ==========================================
MONGO_URL = "mongodb+srv://mirza:faizy2009%23@cluster0.us2zngx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(MONGO_URL)

client = init_connection()
koleksi = client["keuangan_db"]["pengeluaran"]

# ==========================================
# 3. AMBIL DATA & FILTER BULANAN (AUTO-RESET)
# ==========================================
# Mengambil data dari MongoDB yang tanggalnya diawali dengan tahun-bulan sekarang (e.g., "2026-06-%")
query_bulanan = {"tanggal": {"$regex": f"^{bulan_kode}"}}
data_mentah = list(koleksi.find(query_bulanan, {"_id": 0}))

# Jika awal bulan belum ada data, tampilkan pesan bersih
if not data_mentah:
    st.success(f"🎉 Selamat datang di bulan baru! Belum ada transaksi untuk {bulan_sekarang_tahun}. Silakan input data lewat Telegram.")
    
    # Tampilkan metrik kosong biar layout tidak rusak
    m1, m2, m3 = st.columns(3)
    m1.metric(label="Total Pemasukan", value="Rp 0", delta="Pemasukan")
    m2.metric(label="Total Pengeluaran", value="Rp 0", delta="- Pengeluaran")
    m3.metric(label="Sisa Saldo Aman", value="Rp 0", delta="Aman sentosa")
else:
    df = pd.DataFrame(data_mentah)
    
    # Fungsi mengambil angka nominal uang dari dalam kalimat chat
    def ambil_nominal(teks):
        angka = re.findall(r'\d+', str(teks))
        return int("".join(angka)) if angka else 0

    df['nominal'] = df['catatan_asli'].apply(ambil_nominal)
    
    # Memilah jenis transaksi secara presisi lewat kata kunci
    def tentukan_jenis(teks):
        t = str(teks).lower()
        kata_pemasukan = ['gaji', 'pemasukan', 'dapat', 'transfer', 'dikasih', 'jualan', 'hasil']
        if any(kata in t for kata in kata_pemasukan):
            return 'Pemasukan'
        return 'Pengeluaran'
        
    df['jenis'] = df['catatan_asli'].apply(tentukan_jenis)

    # ==========================================
    # 4. BAGIAN KEUANGAN (METRIK WARNA HIJAU/MERAH)
    # ==========================================
    total_pemasukan = df[df['jenis'] == 'Pemasukan']['nominal'].sum()
    total_pengeluaran = df[df['jenis'] == 'Pengeluaran']['nominal'].sum()
    sisa_saldo = total_pemasukan - total_pengeluaran

    m1, m2, m3 = st.columns(3)
    
    # Indikator Panah Hijau untuk Pemasukan
    m1.metric(label="Total Pemasukan", value=f"Rp {total_pemasukan:,}", delta="Pemasukan", delta_color="normal")
    
    # Indikator Panah Merah untuk Pengeluaran (pakai minus agar jadi merah)
    m2.metric(label="Total Pengeluaran", value=f"Rp {total_pengeluaran:,}", delta="- Pengeluaran", delta_color="normal")
    
    # Logika warna dan peringatan Saldo
    if sisa_saldo < 0:
        m3.metric(label="Sisa Saldo (Defisit)", value=f"Rp {sisa_saldo:,}", delta="- Dompet Kritis!", delta_color="normal")
        st.error("🚨 **ALARM KEUANGAN:** Pengeluaran kamu sudah melebihi pemasukan! Segera kurangi belanja.")
    elif sisa_saldo < 50000 and total_pemasukan > 0:
        m3.metric(label="Sisa Saldo (Menipis)", value=f"Rp {sisa_saldo:,}", delta="- Sisa sedikit!", delta_color="normal")
        st.warning("⚠️ **PERINGATAN:** Saldo kamu sisa sedikit lagi. Hati-hati sebelum belanja.")
    else:
        m3.metric(label="Sisa Saldo Aman", value=f"Rp {sisa_saldo:,}", delta="Aman sentosa", delta_color="normal")
        st.success("✅ **KONDISI AMAN:** Keuangan kamu bulan ini terpantau masih stabil dan sehat.")

    st.markdown("---")

    # ==========================================
    # 5. GRAFIK INTERAKTIF & TABEL DATA
    # ==========================================
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Catatan Transaksi Bulan Ini")
        df_tampil = df[['tanggal', 'catatan_asli', 'kategori_ai', 'jenis', 'nominal']]
        st.dataframe(df_tampil, width="stretch")

    with col2:
        st.subheader("📊 Perbandingan Pemasukan vs Pengeluaran")
        df_chart = df.groupby('jenis')['nominal'].sum().reset_index()
        
        fig = px.pie(
            df_chart, 
            values='nominal', 
            names='jenis', 
            color='jenis',
            hole=0.4,
            color_discrete_map={
                'Pemasukan': '#28a745',   # Warna Hijau Paten
                'Pengeluaran': '#dc3545'  # Warna Merah Paten
            }
        )
        st.plotly_chart(fig, width="stretch")