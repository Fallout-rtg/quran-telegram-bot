import os
import re
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Кэш для названий сур, чтобы не дергать API каждый раз
SURAH_NAMES = {}

def get_surah_info(surah_id):
    url = f"https://api.alquran.cloud/v1/surah/{surah_id}"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp['status'] == 'OK':
            data = resp['data']
            return {
                "name": data['name'], # На арабском
                "english": data['englishName'], # На англ (для базы)
                "count": data['numberOfAyahs']
            }
    except: pass
    return None

def fetch_range_data(surah: int, start: int, end: int):
    ayahs_info = []
    for a_num in range(start, end + 1):
        url = f"https://api.alquran.cloud/v1/ayah/{surah}:{a_num}/editions/quran-uthmani,ru.kuliev,ar.alafasy"
        try:
            resp = requests.get(url, timeout=10).json()
            if resp['status'] == 'OK':
                data = resp['data']
                ayahs_info.append({
                    'num': a_num,
                    'arabic': next(e['text'] for e in data if e['edition']['identifier'] == 'quran-uthmani'),
                    'translation': next(e['text'] for e in data if e['edition']['identifier'] == 'ru.kuliev'),
                    'audio': next(e['audio'] for e in data if e['edition']['identifier'] == 'ar.alafasy'),
                    'surah_name': data[0]['surah']['name'],
                    'surah_ru': data[0]['surah']['englishNameTranslation']
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
        payload = {"chat_id": chat_id, "text": part, "parse_mode": "HTML", "disable_web_page_preview": True}
        if reply_markup and i + limit >= len(text):
            payload["reply_markup"] = reply_markup
        requests.post(f"{TG_API}/sendMessage", json=payload)

def send_audio_group(chat_id, ayahs_data):
    media = []
    for a in ayahs_data:
        if a['audio']:
            media.append({"type": "audio", "media": a['audio'], "title": f"Сура {a['num']}"})
    if media:
        requests.post(f"{TG_API}/sendMediaGroup", json={"chat_id": chat_id, "media": media})

def get_nav_buttons(surah, start, end):
    step = (end - start) + 1
    row = []
    if start > 1:
        ps, pe = max(1, start - step), start - 1
        label = f"⬅️ {ps}-{pe}" if step > 1 else f"⬅️ {ps}"
        row.append({"text": label, "callback_data": f"{surah}:{ps}-{pe}" if step > 1 else f"{surah}:{ps}"})
    
    # Кнопка вперед (упрощенно)
    ns, ne = end + 1, end + step
    row.append({"text": f"{ns}-{ne} ➡️" if step > 1 else f"{ns} ➡️", "callback_data": f"{surah}:{ns}-{ne}" if step > 1 else f"{surah}:{ns}"})
    return {"inline_keyboard": [row]}

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
    else: return "OK", 200

    if text.startswith("/start"):
        welcome = (
            "🕌 <b>Ассаламу алейкум ва рахматуллахи ва баракатух!</b>\n\n"
            "Добро пожаловать в бот для изучения Священного Корана. "
            "Я помогу вам получить текст аятов, перевод Э. Кулиева, "
            "толкование (тафсир) шейха ас-Саади и прекрасное аудио-чтение.\n\n"
            "📖 <b>Как пользоваться:</b>\n"
            "• Один аят — <code>2:255</code>\n"
            "• Диапазон аятов — <code>2:1-3</code>\n"
            "• Список сур — /surahs\n"
            "• Максимальный диапазон аятов — 10\n\n"
            "Пусть Аллах сделает это знание полезным для вас!"
        )
        send_message(chat_id, welcome)
        return "OK", 200

    if text == "/surahs":
        try:
            resp = requests.get("https://api.alquran.cloud/v1/surah", timeout=10).json()
            list_text = "📜 <b>Список всех сур Корана:</b>\n<blockquote expandable>"
            for s in resp['data']:
                list_text += f"{s['number']}. {s['name']} ({s['englishNameTranslation']}) — аятов: {s['numberOfAyahs']}\n"
            list_text += "</blockquote>"
            send_message(chat_id, list_text)
        except: send_message(chat_id, "❌ Не удалось загрузить список сур.")
        return "OK", 200

    match = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', text)
    if not match:
        if "message" in update: send_message(chat_id, "❌ Формат: <code>сура:аят</code> или <code>сура:аят-аят</code>")
        return "OK", 200

    surah, start_ayah = int(match.group(1)), int(match.group(2))
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah

    if not (1 <= surah <= 114) or (end_ayah - start_ayah) >= 10:
        send_message(chat_id, "❌ Ошибка: неверная сура или диапазон > 10.")
        return "OK", 200

    ayahs_data = fetch_range_data(surah, start_ayah, end_ayah)
    if not ayahs_data:
        send_message(chat_id, "❌ Аяты не найдены.")
        return "OK", 200

    is_single = (start_ayah == end_ayah)
    s_info = f"{ayahs_data[0]['surah_name']} ({ayahs_data[0]['surah_ru']})"
    
    # 1. Текст
    full_text = f"📖 <b>Сура {surah}: {s_info}, Аят{'т' if not is_single else ''} {start_ayah}{'' if is_single else '-'+str(end_ayah)}</b>\n\n"
    for a in ayahs_data:
        full_text += (f"<b>Аят {a['num']}</b>\n" if not is_single else "") + f"{a['arabic']}\n<i>{a['translation']}</i>\n\n"
    send_message(chat_id, full_text)

    # 2. Тафсир
    combined_tafsir = ""
    for a in ayahs_data:
        t_content = fetch_tafsir(surah, a['num'])
        if t_content:
            combined_tafsir += (f"📌 <b>Аят {a['num']}:</b>\n" if not is_single else "") + f"{t_content}\n\n"

    if combined_tafsir:
        header = f"📚 <b>Толкование {surah}:{start_ayah}</b>" if is_single else f"📚 <b>Толкование {surah}:{start_ayah}-{end_ayah}</b>"
        nav = get_nav_buttons(surah, start_ayah, end_ayah)
        send_message(chat_id, f"{header}\n<blockquote expandable>{combined_tafsir.strip()}</blockquote>", reply_markup=nav)

    # 3. Аудио группой
    send_audio_group(chat_id, ayahs_data)

    return "OK", 200

@app.route('/', methods=['GET'])
def index(): return "Bot is running", 200
