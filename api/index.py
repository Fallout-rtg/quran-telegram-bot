import os
import logging
import re
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def fetch_ayah_data(surah: int, ayah: int):
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/editions/quran-uthmani,ru.kuliev,ar.alafasy"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'OK':
                editions = data['data']
                return {
                    'arabic': next((e['text'] for e in editions if e['edition']['identifier'] == 'quran-uthmani'), ""),
                    'translation': next((e['text'] for e in editions if e['edition']['identifier'] == 'ru.kuliev'), ""),
                    'audio': next((e['audio'] for e in editions if e['edition']['identifier'] == 'ar.alafasy'), None)
                }
    except: pass
    return None

def fetch_tafsir(surah: int, ayah: int):
    url = f"https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/ru-tafseer-al-saddi/{surah}/{ayah}.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('text', '')
    except: pass
    return ""

def send_message(chat_id, text):
    # Функция для отправки длинных сообщений по частям
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
            "• Диапазон аятов — <code>2:1-3</code>\n\n"
            "Пусть Аллах сделает это знание полезным для вас!"
        )
        send_message(chat_id, welcome)
        return "OK", 200

    # Регулярка для одиночного аята (2:255) или диапазона (2:1-3)
    match = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', text)
    if not match:
        send_message(chat_id, "❌ Неверный формат. Используйте <code>сура:аят</code> или <code>сура:аят-аят</code>")
        return "OK", 200

    surah = int(match.group(1))
    start_ayah = int(match.group(2))
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah

    if not (1 <= surah <= 114) or start_ayah > end_ayah or (end_ayah - start_ayah) > 10:
        send_message(chat_id, "❌ Ошибка в номерах или диапазон слишком велик (макс. 10 аятов за раз).")
        return "OK", 200

    for a_num in range(start_ayah, end_ayah + 1):
        data = fetch_ayah_data(surah, a_num)
        if not data:
            send_message(chat_id, f"❌ Аят {surah}:{a_num} не найден.")
            continue

        # 1. Отправляем текст аята и перевод
        main_text = (
            f"📖 <b>Сура {surah}, Аят {a_num}</b>\n\n"
            f"🕋 <code>{data['arabic']}</code>\n\n"
            f"🇷🇺 <b>Перевод:</b> {data['translation']}"
        )
        send_message(chat_id, main_text)

        # 2. Отправляем тафсир отдельным сворачиваемым сообщением
        tafsir_text = fetch_tafsir(surah, a_num)
        if tafsir_text:
            # Сворачиваемая цитата HTML
            formatted_tafsir = (
                f"📚 <b>Толкование аята {a_num}:</b>\n"
                f"<blockquote expandable>{tafsir_text}</blockquote>"
            )
            send_message(chat_id, formatted_tafsir)

        # 3. Аудио
        if data['audio']:
            send_audio(chat_id, data['audio'], f"Сура {surah}, Аят {a_num}")

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200
