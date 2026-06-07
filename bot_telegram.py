import telebot
import pymongo
import pandas as pd
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
TELEGRAM_TOKEN = "8265162710:AAFVE2w689wfhYPgxxCElHYLqciGcHuhxlE"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

MONGO_URL = "mongodb+srv://mirza:faizy2009%23@cluster0.us2zngx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URL)
koleksi = client["keuangan_db"]["pengeluaran"]

# ==========================================
# 2. MELATIH OTAK AI (NLP)
# ==========================================
data_latihan = [
    ("makan nasi padang 20000", "Makanan"), ("beli nasi goreng 25000", "Makanan"),
    ("jajan es campur 10000", "Jajan"), ("beli bakso 15000", "Jajan"),
    ("bayar listrik 100000", "Tagihan"), ("beli token pln 50000", "Tagihan"),
    ("isi bensin 30000", "Transportasi"), ("ongkos gojek 12000", "Transportasi"),
    ("bayar utang temen 50000", "Utang"), ("ngutang di warung 20000", "Utang"),
    ("dapat gaji bulan ini 3000000", "Pemasukan"), ("hasil jualan 500000", "Pemasukan"),
]

df = pd.DataFrame(data_latihan, columns=["teks", "kategori"])
model_nlp = make_pipeline(TfidfVectorizer(), MultinomialNB())
model_nlp.fit(df['teks'], df['kategori'])

# ==========================================
# 3. LOGIKA BOT TELEGRAM
# ==========================================
@bot.message_handler(func=lambda message: True)
def proses_chat_masuk(message):
    teks_chat = message.text.lower()
    kategori_tebakan = model_nlp.predict([teks_chat])[0]
    
    data_baru = {
        "tanggal": datetime.now().strftime("%Y-%m-%d"),
        "catatan_asli": message.text,
        "kategori_ai": kategori_tebakan
    }
    koleksi.insert_one(data_baru)
    bot.reply_to(message, f"✅ Siap bosku! '{message.text}' sudah disimpan sebagai: {kategori_tebakan}.")

# ==========================================
# 4. SERVER WEB MINI (AGAR GRATIS DI RENDER)
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