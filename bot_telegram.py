import telebot
import pymongo
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from datetime import datetime
import threading
from flask import Flask
import os

# ==========================================
# 1. PENGATURAN DATABASE & TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8800914708:AAGRUlS6nFe34qkjk5wL2mBsFHJWJWhweYY"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

MONGO_URL = "mongodb+srv://mirza:faizy2009%23@cluster0.us2zngx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URL)
koleksi = client["keuangan_db"]["pengeluaran"]

# ==========================================
# 2. MELATIH OTAK AI (NLP)
# ==========================================
# Hapus angka dari data latihan agar AI fokus ke 'kata'-nya saja
data_latihan = [
    # Makanan & Jajan
    ("makan nasi padang", "Makanan"), ("beli nasi goreng", "Makanan"),
    ("jajan es campur", "Jajan"), ("beli bakso", "Jajan"),
    ("beli kopi", "Jajan"), ("ngopi", "Jajan"), ("makan malam", "Makanan"),
    
    # Tagihan
    ("bayar listrik", "Tagihan"), ("beli token pln", "Tagihan"),
    ("bayar wifi", "Tagihan"), ("bayar kos", "Tagihan"), ("tagihan air", "Tagihan"),
    
    # Transportasi
    ("isi bensin", "Transportasi"), ("ongkos gojek", "Transportasi"),
    ("naik grab", "Transportasi"), ("parkir", "Transportasi"), ("tambal ban", "Transportasi"),
    
    # Utang & Cicilan
    ("bayar utang temen", "Utang"), ("ngutang di warung", "Utang"),
    ("cicilan motor", "Utang"), ("bayar pinjol", "Utang"),
    
    # Pemasukan
    ("dapat gaji bulan ini", "Pemasukan"), ("hasil jualan", "Pemasukan"),
    ("pemasukan uang mingguan", "Pemasukan"), ("dikasih uang", "Pemasukan"),
    ("transferan masuk", "Pemasukan"), ("uang jajan", "Pemasukan")
]

df = pd.DataFrame(data_latihan, columns=["teks", "kategori"])
model_nlp = make_pipeline(TfidfVectorizer(), MultinomialNB())
model_nlp.fit(df['teks'], df['kategori'])

# ==========================================
# 3. LOGIKA BOT TELEGRAM
# ==========================================

# Tangkap perintah /start agar tidak masuk database
@bot.message_handler(commands=['start', 'help'])
def sambutan(message):
    bot.reply_to(message, "Halo bosku! Ketik pengeluaran atau pemasukanmu (contoh: 'beli bakso 10000' atau 'pemasukan uang mingguan 300000').")

# Tangkap chat biasa untuk dicatat
@bot.message_handler(func=lambda message: True)
def proses_chat_masuk(message):
    teks_asli = message.text.lower()
    
    # Trik: Hilangkan angka dari teks sebelum ditebak AI agar lebih akurat
    teks_tanpa_angka = re.sub(r'\d+', '', teks_asli).strip()
    if teks_tanpa_angka == "":
        teks_tanpa_angka = teks_asli
        
    kategori_tebakan = model_nlp.predict([teks_tanpa_angka])[0]
    
    # Trik: Ambil nominal angkanya saja untuk disimpan di database
    angka_ditemukan = re.findall(r'\d+', teks_asli)
    nominal = int(angka_ditemukan[0]) if angka_ditemukan else 0
    
    data_baru = {
        "tanggal": datetime.now().strftime("%Y-%m-%d"),
        "catatan_asli": message.text,
        "nominal": nominal,
        "kategori_ai": kategori_tebakan
    }
    
    koleksi.insert_one(data_baru)
    bot.reply_to(message, f"✅ Sukses! Disimpan sebagai kategori: {kategori_tebakan}.")

# ==========================================
# 4. SERVER WEB MINI (AGAR GRATIS DI RENDER/RAILWAY)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Mesin Bot Telegram Sedang Berjalan Online 24 Jam!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
