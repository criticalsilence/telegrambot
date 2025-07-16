import os
import requests
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# .env dosyasından ortam değişkenlerini yükle
load_dotenv()

# Ortam değişkenlerini al
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VENICE_API_KEY = os.getenv("VENICE_API_KEY")

# Venice.ai API URL'sini belirle
# Venice.ai belgelerinde bu URL'nin doğru olduğundan emin olun.
# Genellikle https://api.venice.ai/api/v1/chat/completions şeklindedir, ancak kontrol etmekte fayda var.
VENICE_API_URL = "https://api.venice.ai/api/v1/chat/completions"

# Kullanılacak Venice.ai modelinin adı
# BURAYI KESİNLİKLE GÜNCELLEMELİSİNİZ!
# Venice.ai panelinizde veya dokümantasyonunda (örneğin, 'Models' veya 'Getting Started' bölümlerinde)
# sohbet için hangi model adını kullanmanız gerektiğini bulmalısınız.
# Örnekler: "llama-3.1-405b", "gemma-2-27b-it", "qwen-2-72b-instruct" vb.
VENICE_MODEL_NAME = "qwen-2.5-vl" # <<< BURAYI KENDİ MODEL ADINIZLA DEĞİŞTİRİN

# --- Komut İşleyiciler ---

async def start(update, context):
    """Bot başlatıldığında gönderilecek mesaj."""
    await update.message.reply_text("Merhaba! Ben embriyoloji asistanınızım. Sorularınızı yanıtlayabilirim.")

async def handle_message(update, context):
    """Kullanıcı mesajlarını işler ve Venice.ai'ye gönderir."""
    user_message = update.message.text
    chat_id = update.message.chat_id

    print(f"[{chat_id}] Kullanıcı mesajı: {user_message}") # Konsola loglama

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
            "model": VENICE_MODEL_NAME,
            "messages": [
                {"role": "system", "content": """Siz tajribali embriyolog yordamchisiz. Bemorlarning savollariga aniq va tushunarli javob bering. Tibbiy maslahat bermang, faqat ma'lumot bering. Davolanish so'rovlarini klinikaga yo'naltiring.

Bizning klinikamiz haqida ma'lumot:
Nomi: Turk Buxoro EKU Markazi
Manzil: Buxoro shahar A.G'ijduvoniy 60uy, Bukhoro, 200100, O'zbekiston)
Telefon: [Telefon Numaranız, örn: +998 88 244 00 03]
Ish vaqti: Dushanba-Juma 09:00-17:00, Shanba 09:00-13:00, Yakshanba yopiq.

Agar bemor manzil, aloqa yoki ish vaqti haqida so'rasa, yuqoridagi ma'lumotlardan foydalaning.
Davolanish, narxlar yoki shaxsiy maslahat so'ralganda, ularni har doim klinikaga yo'naltiring.
""",
                },
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

    try:
        response = requests.post(VENICE_API_URL, headers=headers, json=payload)
        response.raise_for_status() # HTTP hataları (4xx, 5xx) için istisna fırlatır

        response_data = response.json()
        ai_response = response_data["choices"][0]["message"]["content"]

        print(f"[{chat_id}] AI yanıtı: {ai_response}") # Konsola loglama

        await update.message.reply_text(ai_response)

        # --- Klinik Yönlendirme Mantığı ---
        # Hem kullanıcının mesajında hem de AI'nın yanıtında anahtar kelime kontrolü
        # Türkçe ve Özbekçe anahtar kelimeler
        trigger_keywords = ["tedavi", "randevu", "klinik", "doktor", # Türkçe
                            "davolash", "uchrashuv", "klinika", "shifokor", # Özbekçe
                            "treatment", "appointment", "clinic", "doctor"] # İngilizce (olası)

        lower_user_message = user_message.lower()
        lower_ai_response = ai_response.lower()

        # Herhangi bir tetikleyici kelime bulunursa kliniğe yönlendir
        if any(keyword in lower_user_message for keyword in trigger_keywords) or \
           any(keyword in lower_ai_response for keyword in trigger_keywords):
            await update.message.reply_text(
                "Tedavi talebiniz için sizi kliniğimize yönlendirebiliriz. "
                "Randevu almak veya daha fazla bilgi edinmek için lütfen şu numarayı arayın: **+998 882440003** " # <<< Kendi telefon numaranızı buraya yazın
                "veya web sitemizi ziyaret edin: [www.klinikadi.uz](https://www.klinikadi.uz)" # <<< Kendi web sitenizi buraya yazın
            )

    except requests.exceptions.RequestException as e:
        print(f"Venice.ai API hatası: {e}")
        await update.message.reply_text("Üzgünüm, şu anda bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin.")
    except KeyError as e:
        # API yanıtının beklenen formatta olmaması durumu
        print(f"Venice.ai yanıtında beklenmeyen format: {e}, Tam yanıt: {response_data if 'response_data' in locals() else 'Yanıt alınamadı'}")
        await update.message.reply_text("Üzgünüm, AI'dan beklenmeyen bir yanıt aldım.")
    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        await update.message.reply_text("Bir hata oluştu.")

# --- Ana Fonksiyon ---

def main():
    """Botu çalıştıran ana fonksiyon."""
    # Telegram uygulamasını oluştur
    if not TELEGRAM_BOT_TOKEN:
        print("HATA: TELEGRAM_BOT_TOKEN ortam değişkeni ayarlanmadı. Lütfen .env dosyanızı kontrol edin.")
        return
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Komut işleyicileri ekle
    application.add_handler(CommandHandler("start", start))
    # Metin mesajlarını işlemek için mesaj işleyici ekle (komut olmayanlar)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot çalışıyor... Mesaj bekleniyor.")
    # Botu başlat ve gelen mesajları dinle
    application.run_polling(poll_interval=1.0) # Her 1 saniyede bir yeni mesajları kontrol et

if __name__ == "__main__":
    main()