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
# 2. MELATIH OTAK AI (NLP) - TAMBAHKAN KATA DI SINI
# ==========================================
data_latihan = [
    # Makanan & Jajan
    ("makan nasi padang", "Makanan"), ("beli nasi goreng", "Makanan"), ("jajan es campur", "Jajan"), 
    ("beli bakso", "Jajan"), ("beli kopi", "Jajan"), ("ngopi", "Jajan"), ("makan", "Makanan"),
    
    # Tagihan
    ("bayar listrik", "Tagihan"), ("beli token pln", "Tagihan"), ("bayar wifi", "Tagihan"), 
    ("bayar kos", "Tagihan"), ("tagihan air", "Tagihan"), ("bayar tagihan", "Tagihan"),
    
    # Transportasi
    ("isi bensin", "Transportasi"), ("ongkos gojek", "Transportasi"), ("naik grab", "Transportasi"), 
    ("parkir motor", "Transportasi"), ("tambal ban", "Transportasi"), ("naik angkot", "Transportasi"),
    
    # Utang
    ("bayar utang teman", "Utang"), ("bayar utang temen", "Utang"), ("ngutang di warung", "Utang"), 
    ("bayar cicilan", "Utang"), ("bayar pinjol", "Utang"), ("utang", "Utang"),
    
    # Pemasukan
    ("dapat gaji", "Pemasukan"), ("hasil jualan", "Pemasukan"), ("dikasih uang", "Pemasukan"), 
    ("transferan masuk", "Pemasukan"), ("gajian", "Pemasukan"), ("dapat uang", "Pemasukan")
]

df = pd.DataFrame(data_latihan, columns=["teks", "kategori"])
model_nlp = make_pipeline(TfidfVectorizer(), MultinomialNB())
model_nlp.fit(df['teks'], df['kategori'])

# ==========================================
# 3. LOGIKA BOT TELEGRAM
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def sambutan(message):
    bot.reply_to(message, "Halo bosku! Ketik saja pengeluaranmu, misal: 'bayar utang teman 50000'")

@bot.message_handler(func=lambda message: True)
def proses_chat_masuk(message):
    teks_asli = message.text.lower()
    
    # Pembersihan angka agar AI fokus ke kata kunci
    teks_tanpa_angka = re.sub(r'\d+', '', teks_asli).strip()
    kategori_tebakan = model_nlp.predict([teks_tanpa_angka])[0]
    
    # Ekstraksi angka untuk nominal
    angka_ditemukan = re.findall(r'\d+', teks_asli)
    nominal = int(angka_ditemukan[0]) if angka_ditemukan else 0
    
    # Simpan ke Database
    koleksi.insert_one({
        "tanggal": datetime.now().strftime("%Y-%m-%d"),
        "catatan_asli": message.text,
        "nominal": nominal,
        "kategori_ai": kategori_tebakan
    })
    
    bot.reply_to(message, f"✅ Sukses! Disimpan sebagai: {kategori_tebakan} (Rp {nominal:,})")

# ==========================================
# 4. SERVER WEB (AGAR TETAP HIDUP)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Telegram Aktif!"

def run_bot(): bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
