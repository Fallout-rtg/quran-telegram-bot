import os
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

def send_message(chat_id, text, reply_markup=None):
    limit = 4000
    for i in range(0, len(text), limit):
        part = text[i:i+limit]
        payload = {
            "chat_id": chat_id,
            "text": part,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_markup and i + limit >= len(text):
            payload["reply_markup"] = reply_markup
        requests.post(f"{TG_API}/sendMessage", json=payload)

def send_audio(chat_id, audio_url, title):
    requests.post(f"{TG_API}/sendAudio", json={"chat_id": chat_id, "audio": audio_url, "title": title})

def get_nav_buttons(surah, start, end):
    buttons = []
    step = (end - start) + 1
    
    row = []
    if start > 1:
        prev_s = max(1, start - step)
        prev_e = start - 1
        label = f"⬅️ {surah}:{prev_s}-{prev_e}" if step > 1 else f"⬅️ {surah}:{prev_s}"
        row.append({"text": label, "callback_data": f"{surah}:{prev_s}-{prev_e}" if step > 1 else f"{surah}:{prev_s}"})
    
    if end < 286: 
        next_s = end + 1
        next_e = end + step
        label = f"{surah}:{next_s}-{next_e} ➡️" if step > 1 else f"{surah}:{next_s} ➡️"
        row.append({"text": label, "callback_data": f"{surah}:{next_s}-{next_e}" if step > 1 else f"{surah}:{next_s}"})
    
    if row: buttons.append(row)
    return {"inline_keyboard": buttons}

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "OK", 200

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
    elif "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        text = update["callback_query"]["data"]
    else:
        return "OK", 200

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
        if "message" in update:
            send_message(chat_id, "❌ Неверный формат. Используйте <code>сура:аят</code> или <code>сура:аят-аят</code>")
        return "OK", 200

    surah, start_ayah = int(match.group(1)), int(match.group(2))
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah

    if not (1 <= surah <= 114) or (end_ayah - start_ayah) >= 10:
        send_message(chat_id, "❌ Ошибка: неверные номера или лимит 10 аятов.")
        return "OK", 200

    ayahs_data = fetch_range_data(surah, start_ayah, end_ayah)
    if not ayahs_data:
        send_message(chat_id, "❌ Аяты не найдены.")
        return "OK", 200

    is_single = (start_ayah == end_ayah)
    
    if is_single:
        a = ayahs_data[0]
        full_text = f"📖 <b>Сура {surah}, Аят {start_ayah}</b>\n\n{a['arabic']}\n\n{a['translation']}"
    else:
        full_text = f"📖 <b>Сура {surah}, Аяты {start_ayah}-{end_ayah}</b>\n\n"
        for a in ayahs_data:
            full_text += f"<b>Аят {a['num']}</b>\n{a['arabic']}\n<i>{a['translation']}</i>\n\n"

    send_message(chat_id, full_text)

    combined_tafsir = ""
    for a in ayahs_data:
        t_content = fetch_tafsir(surah, a['num'])
        if t_content:
            combined_tafsir += (f"📌 <b>Аят {a['num']}:</b>\n" if not is_single else "") + f"{t_content}\n\n"

    if combined_tafsir:
        header = f"📚 <b>Толкование {surah}:{start_ayah}</b>" if is_single else f"📚 <b>Толкование {surah}:{start_ayah}-{end_ayah}</b>"
        final_tafsir = f"{header}\n<blockquote expandable>{combined_tafsir.strip()}</blockquote>"
        
        nav = get_nav_buttons(surah, start_ayah, end_ayah)
        send_message(chat_id, final_tafsir, reply_markup=nav)

    for a in ayahs_data:
        if a['audio']:
            send_audio(chat_id, a['audio'], f"Сура {surah}, Аят {a['num']}")

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200
