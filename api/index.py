import os
import logging
import re
import requests
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def fetch_ayah_data(surah: int, ayah: int):
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/editions/quran-uthmani,ru.kuliev,ar.alafasy"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                editions = data['data']
                arabic = next((e['text'] for e in editions if e['edition']['identifier'] == 'quran-uthmani'), None)
                translation = next((e['text'] for e in editions if e['edition']['identifier'] == 'ru.kuliev'), None)
                audio_url = next((e['audio'] for e in editions if e['edition']['identifier'] == 'ar.alafasy'), None)
                return {'arabic': arabic, 'translation': translation, 'audio_url': audio_url}
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
    return None

def fetch_tafsir(surah: int, ayah: int):
    url = f"https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/ru-tafseer-al-saddi/{surah}/{ayah}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get('text', 'Толкование не найдено.')
    except Exception:
        pass
    return "Не удалось загрузить толкование."

def send_tg_request(method, payload):
    return requests.post(f"{TG_API}/{method}", json=payload)

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "OK", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text.startswith("/start"):
        send_tg_request("sendMessage", {
            "chat_id": chat_id,
            "text": "🕌 <b>Ассаламу алейкум!</b>\n\nОтправьте <code>сура:аят</code>",
            "parse_mode": "HTML"
        })
        return "OK", 200

    match = re.match(r'^(\d+):(\d+)$', text)
    if not match:
        return "OK", 200

    surah, ayah = int(match.group(1)), int(match.group(2))
    
    if not (1 <= surah <= 114):
        send_tg_request("sendMessage", {"chat_id": chat_id, "text": "❌ Суры от 1 до 114."})
        return "OK", 200

    ayah_data = fetch_ayah_data(surah, ayah)
    if not ayah_data:
        send_tg_request("sendMessage", {"chat_id": chat_id, "text": "❌ Аят не найден."})
        return "OK", 200

    tafsir = fetch_tafsir(surah, ayah)
    response_text = (
        f"📖 <b>Сура {surah}, Аят {ayah}</b>\n\n"
        f"🕋 {ayah_data['arabic']}\n\n"
        f"🇷🇺 <b>Перевод:</b> {ayah_data['translation']}\n\n"
        f"📚 <b>Толкование:</b> {tafsir}"
    )
    
    send_tg_request("sendMessage", {"chat_id": chat_id, "text": response_text, "parse_mode": "HTML"})
    
    if ayah_data.get('audio_url'):
        send_tg_request("sendAudio", {
            "chat_id": chat_id, 
            "audio": ayah_data['audio_url'], 
            "title": f"Сура {surah}, Аят {ayah}"
        })

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200
