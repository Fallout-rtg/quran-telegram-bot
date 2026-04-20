import json
import os
import logging
import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def fetch_ayah_data(surah: int, ayah: int):
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/editions/quran-uthmani,ru.kuliev,ar.alafasy"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        editions = data['data']
                        arabic = next((e['text'] for e in editions if e['edition']['identifier'] == 'quran-uthmani'), None)
                        translation = next((e['text'] for e in editions if e['edition']['identifier'] == 'ru.kuliev'), None)
                        audio_url = next((e['audio'] for e in editions if e['edition']['identifier'] == 'ar.alafasy'), None)
                        return {'arabic': arabic, 'translation': translation, 'audio_url': audio_url}
        except Exception as e:
            logging.error(f"Ошибка API: {e}")
    return None

async def fetch_tafsir(surah: int, ayah: int):
    url = f"https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/ru-tafseer-al-saddi/{surah}/{ayah}.json"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('text', 'Толкование не найдено.')
        except Exception as e:
            logging.error(f"Ошибка Tafsir API: {e}")
    return "Не удалось загрузить толкование."

async def send_message(chat_id: int, text: str, parse_mode: str = "HTML"):
    url = f"{TG_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def send_audio(chat_id: int, audio_url: str, title: str):
    url = f"{TG_API}/sendAudio"
    payload = {"chat_id": chat_id, "audio": audio_url, "title": title}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def handle_update(update: dict):
    if "message" not in update:
        return
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text.startswith("/start"):
        await send_message(chat_id,
            "🕌 <b>Ассаламу алейкум!</b>\n\n"
            "Отправьте номер суры и аята в формате <code>сура:аят</code>\n"
            "Например: <code>2:255</code> или <code>1:1</code>\n\n"
            "Я пришлю текст на арабском, перевод, толкование и аудиозапись."
        )
        return

    import re
    match = re.match(r'^(\d+):(\d+)$', text)
    if not match:
        await send_message(chat_id, "❌ Неверный формат. Используйте <code>сура:аят</code>")
        return

    surah = int(match.group(1))
    ayah = int(match.group(2))
    if not (1 <= surah <= 114) or ayah < 1:
        await send_message(chat_id, "❌ Неверный номер суры или аята.")
        return

    await send_message(chat_id, "⏳ Ищу аят...")
    ayah_data = await fetch_ayah_data(surah, ayah)
    if not ayah_data:
        await send_message(chat_id, "❌ Не удалось найти аят. Проверьте номер.")
        return

    tafsir = await fetch_tafsir(surah, ayah)

    response = (
        f"📖 <b>Сура {surah}, Аят {ayah}</b>\n\n"
        f"🕋 <b>Арабский текст:</b>\n{ayah_data['arabic']}\n\n"
        f"🇷🇺 <b>Перевод (Кулиев):</b>\n{ayah_data['translation']}\n\n"
        f"📚 <b>Толкование (ас-Саади):</b>\n{tafsir}"
    )
    await send_message(chat_id, response)

    audio_url = ayah_data.get('audio_url')
    if audio_url:
        try:
            await send_audio(chat_id, audio_url, f"Сура {surah}, Аят {ayah}")
        except Exception as e:
            await send_message(chat_id, "⚠️ Не удалось отправить аудио.")
    else:
        await send_message(chat_id, "⚠️ Аудио не найдено.")

async def webhook_handler(request):
    try:
        data = await request.json()
        await handle_update(data)
    except Exception as e:
        logging.error(f"Ошибка обработки: {e}")
    return web.Response(text="OK")

app = web.Application()
app.router.add_post("/api/webhook", webhook_handler)
app.router.add_get("/api/webhook", webhook_handler)  # для проверки

if __name__ == "__main__":
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
