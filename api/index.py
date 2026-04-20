import os
import re
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# База данных сур (оставлена для работы логики)
SURAH_DATA = {
    1: ["الفاتحة", "Открывающая", 7], 2: ["البقرة", "Корова", 286], 3: ["آل عمران", "Семейство Имрана", 200],
    4: ["النساء", "Женщины", 176], 5: ["المائدة", "Трапеза", 120], 6: ["الأنعام", "Скот", 165],
    7: ["الأعراف", "Преграды", 206], 8: ["الأنفال", "Трофеи", 75], 9: ["التوبة", "Покаяние", 129],
    10: ["يونس", "Юнус", 109], 11: ["هود", "Худ", 123], 12: ["يوسف", "Юсуф", 111],
    13: ["الرعد", "Гром", 43], 14: ["إبراهيم", "Ибрахим", 52], 15: ["الحجر", "Хиджр", 99],
    16: ["النحل", "Пчелы", 128], 17: ["الإسراء", "Ночной перенос", 111], 18: ["الكهф", "Пещера", 110],
    19: ["مريم", "Марьям", 98], 20: ["طه", "Та Ха", 135], 21: ["الأنبياء", "Пророки", 112],
    22: ["الحج", "Хадж", 78], 23: ["المؤمنون", "Верующие", 118], 24: ["النور", "Свет", 64],
    25: ["الفرقان", "Различение", 77], 26: ["الشعراء", "Поэты", 227], 27: ["النمل", "Муравьи", 93],
    28: ["القصص", "Повествование", 88], 29: ["العنكبوت", "Паук", 69], 30: ["الروم", "Римляне", 60],
    31: ["لقمان", "Лукман", 34], 32: ["السجدة", "Поклон", 30], 33: ["الأحزاب", "Сонмы", 73],
    34: ["سبأ", "Сава", 54], 35: ["فاطر", "Творец", 45], 36: ["يس", "Йа Син", 83],
    37: ["الصافات", "Выстроившиеся в ряды", 182], 38: ["ص", "Сад", 88], 39: ["الزمر", "Толпы", 75],
    40: ["غافر", "Прощающий", 85], 41: ["فصلت", "Разъяснены", 54], 42: ["الشورى", "Совет", 53],
    43: ["الزخرف", "Украшения", 89], 44: ["الدخان", "Дым", 59], 45: ["الجاثية", "Коленопреклоненные", 37],
    46: ["الأحقاف", "Барханы", 35], 47: ["محمد", "Мухаммад", 38], 48: ["الفتح", "Победа", 29],
    49: ["الحجرات", "Комнаты", 18], 50: ["ق", "Каф", 45], 51: ["الذاريات", "Рассеивающие", 60],
    52: ["الطور", "Гора", 49], 53: ["النجم", "Звезда", 62], 54: ["القمر", "Луна", 55],
    55: ["الرحمن", "Милостивый", 78], 56: ["الواقعة", "Событие", 96], 57: ["الحديد", "Железо", 29],
    58: ["المجادلة", "Препирающаяся", 22], 59: ["الحشر", "Собрание", 24], 60: ["الممتحنة", "Испытуемая", 13],
    61: ["الصف", "Ряды", 14], 62: ["الجمعة", "Пятница", 11], 63: ["المنافقون", "Лицемеры", 11],
    64: ["التغابн", "Взаимное обманывание", 18], 65: ["الطلاق", "Развод", 12], 66: ["التحريم", "Запрещение", 12],
    67: ["الملк", "Власть", 30], 68: ["القلم", "Письменная трость", 52], 69: ["الحاقة", "Неминуемое", 52],
    70: ["المعارج", "Ступени", 44], 71: ["نوح", "Нух", 28], 72: ["الجن", "Джинны", 28],
    73: ["المزمل", "Закутавшийся", 20], 74: ["المدثر", "Завернувшийся", 56], 75: ["القيامة", "Воскресение", 40],
    76: ["الإنسان", "Человек", 31], 77: ["المرسلات", "Посылаемые", 50], 78: ["النبأ", "Весть", 40],
    79: ["النازعات", "Исторгающие", 46], 80: ["عبس", "Нахмурился", 42], 81: ["التكوير", "Скручивание", 29],
    82: ["الانفطار", "Раскалывание", 19], 83: ["المطففين", "Обвешивающие", 36], 84: ["الانشقاق", "Разверзание", 25],
    85: ["البروج", "Созвездия", 22], 86: ["الطارق", "Ночной путник", 17], 87: ["الأعلى", "Всевышний", 19],
    88: ["الغاشية", "Покрывающее", 26], 89: ["الفجر", "Заря", 30], 90: ["البلд", "Город", 20],
    91: ["الشمس", "Солнце", 15], 92: ["الليل", "Ночь", 21], 93: ["الضحى", "Утро", 11],
    94: ["الشرح", "Раскрытие", 8], 95: ["التين", "Смоковница", 8], 96: ["العلق", "Сгусток", 19],
    97: ["القدر", "Предопределение", 5], 98: ["البينة", "Ясное знамение", 8], 99: ["الزلزلة", "Землетрясение", 8],
    100: ["العاديات", "Скачущие", 11], 101: ["القارعة", "Бедствие", 11], 102: ["التكاثر", "Страсть к приумножению", 8],
    103: ["العصر", "Предвечернее время", 3], 104: ["الهمزة", "Хулитель", 9], 105: ["الفيل", "Слон", 5],
    106: ["قريش", "Курайшиты", 4], 107: ["الماعون", "Подаяние", 7], 108: ["الكوثر", "Обильное", 3],
    109: ["الكافرون", "Неверующие", 6], 110: ["النصر", "Помощь", 3], 111: ["المسد", "Пальмовые волокна", 5],
    112: ["الإخلاص", "Очищение веры", 4], 113: ["الفلق", "Рассвет", 5], 114: ["الناس", "Люди", 6]
}

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
    # Уменьшил лимит до 3800 для запаса на HTML теги
    limit = 3800
    if len(text) <= limit:
        requests.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "HTML", 
            "disable_web_page_preview": True, "reply_markup": reply_markup
        })
    else:
        # Разбиваем текст, стараясь не разрывать теги (грубое разбиение по длине)
        for i in range(0, len(text), limit):
            part = text[i:i+limit]
            # Добавляем кнопки только к последней части
            markup = reply_markup if i + limit >= len(text) else None
            requests.post(f"{TG_API}/sendMessage", json={
                "chat_id": chat_id, "text": part, "parse_mode": "HTML", 
                "disable_web_page_preview": True, "reply_markup": markup
            })

def send_audio_group(chat_id, ayahs_data):
    media = []
    for a in ayahs_data:
        if a['audio']:
            media.append({"type": "audio", "media": a['audio']})
    if media:
        requests.post(f"{TG_API}/sendMediaGroup", json={"chat_id": chat_id, "media": media})

def get_nav_buttons(surah, start, end):
    max_ayahs = SURAH_DATA[surah][2]
    step = (end - start) + 1
    row = []
    if start > 1:
        ps, pe = max(1, start - step), start - 1
        label = f"⬅️ {ps}-{pe}" if step > 1 else f"⬅️ {ps}"
        row.append({"text": label, "callback_data": f"{surah}:{ps}-{pe}" if step > 1 else f"{surah}:{ps}"})
    if end < max_ayahs:
        ns, ne = end + 1, min(max_ayahs, end + step)
        label = f"{ns}-{ne} ➡️" if step > 1 else f"{ns} ➡️"
        row.append({"text": label, "callback_data": f"{surah}:{ns}-{ne}" if step > 1 else f"{surah}:{ns}"})
    return {"inline_keyboard": [row]} if row else None

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
            "Добро пожаловать в бот для изучения Священного Корана.\n\n"
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
        # Разбиваем список сур на 3 части, чтобы не превышать лимит
        parts = [list(SURAH_DATA.items())[i:i + 40] for i in range(0, len(SURAH_DATA), 40)]
        
        for idx, part in enumerate(parts):
            msg = f"📜 <b>Список сур Корана (Часть {idx+1}):</b>\n<blockquote expandable>"
            for n, info in part:
                # Сначала номер и русское название, арабское — в конце через тире
                msg += f"{n}. <b>{info[1]}</b> — {info[2]} аят.  |  {info[0]}\n"
            msg += "</blockquote>"
            send_message(chat_id, msg)
        return "OK", 200

    match = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', text)
    if not match:
        if "message" in update: send_message(chat_id, "❌ Формат: <code>сура:аят</code> или <code>сура:аят-аят</code>")
        return "OK", 200

    surah, start_ayah = int(match.group(1)), int(match.group(2))
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah

    if surah not in SURAH_DATA:
        send_message(chat_id, "❌ Суры с таким номером нет (1-114).")
        return "OK", 200
    
    max_a = SURAH_DATA[surah][2]
    if start_ayah < 1 or end_ayah > max_a or start_ayah > end_ayah:
        send_message(chat_id, f"❌ В суре {surah} всего {max_a} аятов.")
        return "OK", 200

    if (end_ayah - start_ayah) >= 10:
        send_message(chat_id, "❌ Лимит: не более 10 аятов за раз.")
        return "OK", 200

    ayahs_data = fetch_range_data(surah, start_ayah, end_ayah)
    if not ayahs_data:
        send_message(chat_id, "❌ Не удалось загрузить данные.")
        return "OK", 200

    is_single = (start_ayah == end_ayah)
    s_name_ar, s_name_ru = SURAH_DATA[surah][0], SURAH_DATA[surah][1]
    
    full_text = f"📖 <b>Сура {surah}: {s_name_ar} ({s_name_ru})</b>\n"
    full_text += f"<b>Аят{'т' if not is_single else ''} {start_ayah}{'' if is_single else '-'+str(end_ayah)}</b>\n\n"
    for a in ayahs_data:
        full_text += (f"<b>Аят {a['num']}</b>\n" if not is_single else "") + f"{a['arabic']}\n<i>{a['translation']}</i>\n\n"
    send_message(chat_id, full_text)

    combined_tafsir = ""
    for a in ayahs_data:
        t_content = fetch_tafsir(surah, a['num'])
        if t_content:
            combined_tafsir += (f"📌 <b>Аят {a['num']}:</b>\n" if not is_single else "") + f"{t_content}\n\n"

    if combined_tafsir:
        t_header = f"📚 <b>Толкование {surah}:{start_ayah}</b>" if is_single else f"📚 <b>Толкование {surah}:{start_ayah}-{end_ayah}</b>"
        nav = get_nav_buttons(surah, start_ayah, end_ayah)
        send_message(chat_id, f"{t_header}\n<blockquote expandable>{combined_tafsir.strip()}</blockquote>", reply_markup=nav)

    send_audio_group(chat_id, ayahs_data)
    return "OK", 200

@app.route('/', methods=['GET'])
def index(): return "Bot is running", 200
