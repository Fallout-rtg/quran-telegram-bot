import json
import os
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
VERCEL_URL = os.getenv("VERCEL_URL")

if not BOT_TOKEN or not VERCEL_URL:
    raise ValueError("BOT_TOKEN и VERCEL_URL должны быть установлены")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

async def fetch_tafsir(surah: int, ayah: int, edition: str = 'ru-tafseer-al-saddi'):
    url = f"https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir/{edition}/{surah}/{ayah}.json"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('text', 'Толкование не найдено.')
        except Exception as e:
            logging.error(f"Ошибка Tafsir API: {e}")
    return "Не удалось загрузить толкование."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🕌 <b>Ассаламу алейкум!</b>\n\n"
        "Отправьте номер суры и аята в формате <code>сура:аят</code>\n"
        "Например: <code>2:255</code> или <code>1:1</code>\n\n"
        "Я пришлю текст на арабском, перевод, толкование и аудиозапись.",
        parse_mode="HTML"
    )

@dp.message(F.text.regexp(r'^\d+:\d+$'))
async def handle_ayah_request(message: types.Message):
    try:
        surah, ayah = map(int, message.text.split(':'))
        if not (1 <= surah <= 114) or ayah < 1:
            await message.reply("❌ Неверный номер суры или аята.")
            return
    except ValueError:
        await message.reply("❌ Некорректный формат. Используйте <code>сура:аят</code>", parse_mode="HTML")
        return

    wait_msg = await message.reply("⏳ Ищу аят...")

    ayah_data = await fetch_ayah_data(surah, ayah)
    if not ayah_data:
        await wait_msg.edit_text("❌ Не удалось найти аят. Проверьте номер.")
        return

    tafsir_text = await fetch_tafsir(surah, ayah)

    response_text = (
        f"📖 <b>Сура {surah}, Аят {ayah}</b>\n\n"
        f"🕋 <b>Арабский текст:</b>\n{ayah_data['arabic']}\n\n"
        f"🇷🇺 <b>Перевод (Кулиев):</b>\n{ayah_data['translation']}\n\n"
        f"📚 <b>Толкование (ас-Саади):</b>\n{tafsir_text}"
    )

    await wait_msg.edit_text(response_text, parse_mode="HTML")

    audio_url = ayah_data.get('audio_url')
    if audio_url:
        try:
            await message.reply_audio(audio=audio_url, title=f"Сура {surah}, Аят {ayah}")
        except Exception as e:
            if "file is too big" in str(e):
                await message.reply("⚠️ Аудиофайл слишком большой (>20 МБ).")
            else:
                await message.reply("⚠️ Не удалось отправить аудио.")
    else:
        await message.reply("⚠️ Аудио для этого аята не найдено.")

async def on_startup(bot: Bot):
    webhook_url = f"{VERCEL_URL}/api/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook удалён")

app = web.Application()

webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
webhook_requests_handler.register(app, path="/api/webhook")

app.on_startup.append(lambda _: on_startup(bot))
app.on_shutdown.append(lambda _: on_shutdown(bot))

setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
