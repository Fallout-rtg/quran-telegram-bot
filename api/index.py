import os
import logging
import re
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def fetch_range_data(surah: int, start: int, end: int):  
    ayahs_info = []
    for a_num in range(start, end + 1):
        url = f"https://api.alquran.cloud/v1/ayah/{surah}:{a_num}/editions/quran-uthmani,ru.kuliev,ar.alafasy"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()['data']
                ayahs_info.append({
                    'num': a_num,
                    'arabic': next(e['text'] for e in data if e['edition']['identifier'] == 'quran-uthmani'),
                    'translation': next(e['text'] for e in data if e['edition']['identifier'] == 'ru.kuliev'),
                    'audio': next(e['audio'] for e in data if e['edition']['identifier'] == 'ar.alafasy')
                })
        except: continue
    return ayahs_info

def fetch_tafsir(surah: int, ayah: int):
    url = f"https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/ru-tafseer-al-saddi/{surah}/{ayah}.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('text', '')
    except: pass
    return ""

def send_message(chat_id, text):
    limit = 4000
    for i in range(0, len(text), limit):
        part = text[i:i+limit]
        requests.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": part,
            "parse_mode": "HTML"
        })

def send_audio(chat_id, audio_url, title):
    requests.post(f"{TG_API}/sendAudio", json={
        "chat_id": chat_id,
        "audio": audio_url,
        "title": title
    })

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "OK", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if text.startswith("/start"):
        welcome = (
            "🕌 <b>Ассаламу алейкум ва рахматуллахи ва баракатух!</b>\n\n"
            "Добро пожаловать в бот для изучения Священного Корана. "
            "Я помогу вам получить текст аятов, перевод Э. Кулиева, "
            "толкование (тафсир) шейха ас-Саади и прекрасное аудио-чтение.\n\n"
            "📖 <b>Как пользоваться:</b>\n"
            "• Один аят — <code>2:255</code>\n"
            "• Диапазон аятов — <code>2:1-3</code>\n"
            "• Максимальный диапазон аятов — 10\n\n"
            "Пусть Аллах сделает это знание полезным для вас!"
        )
        send_message(chat_id, welcome)
        return "OK", 200

    match = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', text)
    if not match:
        send_message(chat_id, "❌ Неверный формат. Используйте <code>сура:аят</code> или <code>сура:аят-аят</code>")
        return "OK", 200

    surah = int(match.group(1))
    start_ayah = int(match.group(2))
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah

    if not (1 <= surah <= 114) or start_ayah > end_ayah or (end_ayah - start_ayah) >= 10:
        send_message(chat_id, "❌ Ошибка: неверные номера или превышен лимит (макс. 10 аятов).")
        return "OK", 200

    ayahs_data = fetch_range_data(surah, start_ayah, end_ayah)
    if not ayahs_data:
        send_message(chat_id, "❌ Не удалось найти указанные аяты.")
        return "OK", 200

    full_text = f"📖 <b>Сура {surah}, Аяты {start_ayah}-{end_ayah}</b>\n\n"
    full_tafsir = f"📚 <b>Толкование (ас-Саади) к аятам {start_ayah}-{end_ayah}:</b>\n"
    
    combined_tafsir_content = ""
    
    for a in ayahs_data:
        full_text += f"<b>Аят {a['num']}</b>\n<code>{a['arabic']}</code>\n<i>{a['translation']}</i>\n\n"
        
        t_content = fetch_tafsir(surah, a['num'])
        if t_content:
            combined_tafsir_content += f"📌 <b>Аят {a['num']}:</b>\n{t_content}\n\n"

    send_message(chat_id, full_text)

    if combined_tafsir_content:
        final_tafsir = full_tafsir + f"<blockquote expandable>{combined_tafsir_content}</blockquote>"
        send_message(chat_id, final_tafsir)

    for a in ayahs_data:
        if a['audio']:
            send_audio(chat_id, a['audio'], f"Сура {surah}, Аят {a['num']}")

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200
