import asyncio
import logging
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from bs4 import BeautifulSoup

# ================= 🔐 КОНФИГУРАЦИЯ =================
TOKEN = os.getenv("BOT_TOKEN", "")

HLTV_URL = "https://www.hltv.org"

# 🔥 ПРОКСИ (из твоего VPN конфига)
# Если используешь V2Ray/Xray - порт обычно 10808 (SOCKS) или 10809 (HTTP)
USE_PROXY = True  # Поставь True если нужен прокси
PROXY_URL = "http://127.0.0.1:10809"  # HTTP прокси из твоего VPN
# PROXY_URL = "socks5://127.0.0.1:10808"  # Или SOCKS5

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()


class TeamSearch(StatesGroup):
    waiting_for_team = State()


# ================= 🕷️ ПАРСИНГ С ПРОКСИ =================

async def fetch_hltv(url):
    """Загружает страницу HLTV с прокси"""
    logger.info(f"🔗 Запрос: {url}")

    try:
        connector = None
        if USE_PROXY:
            connector = aiohttp.TCPConnector()
            logger.info(f"🔌 Использую прокси: {PROXY_URL}")

        async with aiohttp.ClientSession(
                headers=HEADERS,
                connector=connector
        ) as session:

            # Настраиваем прокси
            kwargs = {}
            if USE_PROXY:
                kwargs['proxy'] = PROXY_URL

            logger.info("📤 Отправка запроса...")
            async with session.get(url, timeout=20, **kwargs) as resp:
                logger.info(f"📥 Статус: {resp.status}")

                if resp.status == 403:
                    logger.error("🚫 403 Forbidden - HLTV блокирует!")
                    logger.error("💡 Проверь прокси или попробуй позже")
                    return None

                if resp.status != 200:
                    logger.error(f"❌ HTTP {resp.status}")
                    return None

                html = await resp.text()
                logger.info(f"✓ Получено {len(html)} байт")

                soup = BeautifulSoup(html, 'lxml')
                logger.info("✓ HTML распарсен")
                return soup

    except asyncio.TimeoutError:
        logger.error("⏱️ Timeout - сайт не ответил")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"🌐 ClientError: {e}")
        return None
    except Exception as e:
        logger.error(f"💥 Error: {type(e).__name__}: {e}")
        return None


async def get_upcoming_matches():
    logger.info("🎯 Получение матчей...")
    soup = await fetch_hltv(f"{HLTV_URL}/matches")

    if not soup:
        return "❌ Не удалось загрузить. Проверь прокси/интернет."

    try:
        blocks = soup.find_all('div', class_='match-line')
        logger.info(f"Найдено матчей: {len(blocks)}")

        if not blocks:
            blocks = soup.find_all('a', class_='match-link')

        if not blocks:
            return "⚠️ Матчи не найдены"

        m = blocks[0]

        teams = m.find_all('div', class_='team-name')
        if len(teams) < 2:
            teams = m.find_all('span', class_='team-name')

        t1 = teams[0].get_text(strip=True) if len(teams) > 0 else "?"
        t2 = teams[1].get_text(strip=True) if len(teams) > 1 else "?"

        time_el = m.find('div', class_='match-time') or m.find('time')
        when = time_el.get_text(strip=True) if time_el else "?"

        event_el = m.find('div', class_='event-name')
        event = event_el.get_text(strip=True) if event_el else "Турнир"

        return f"🔥 <b>БЛИЖАЙШИЙ МАТЧ:</b>\n\n📅 {when}\n🏆 {event}\n⚔️ <b>{t1}</b> vs <b>{t2}</b>"

    except Exception as e:
        logger.error(f"❌ Parse error: {e}")
        return f"❌ Ошибка: {e}"


async def get_ranking():
    logger.info("🏆 Получение рейтинга...")
    soup = await fetch_hltv(f"{HLTV_URL}/ranking")

    if not soup:
        return "❌ Не удалось загрузить"

    try:
        rows = soup.find_all('tr', class_='row')
        logger.info(f"Найдено строк: {len(rows)}")

        if not rows:
            return "⚠️ Рейтинг не найден"

        ranking = []
        for i, row in enumerate(rows[:10]):
            try:
                pos = row.find('td', class_='position')
                rank = pos.get_text(strip=True) if pos else f"#{i + 1}"

                team = row.find('span', class_='team-name')
                name = team.get_text(strip=True) if team else "Unknown"

                pts = row.find('td', class_='points')
                points = pts.get_text(strip=True) if pts else ""

                ranking.append(f"#{rank} <b>{name}</b> ({points})")

            except Exception as e:
                logger.warning(f"⚠️ Пропущена строка {i}: {e}")
                continue

        if not ranking:
            return "⚠️ Не удалось распарсить"

        return "🏆 <b>HLTV Ranking:</b>\n\n" + "\n".join(ranking)

    except Exception as e:
        logger.error(f"❌ Ranking error: {e}")
        return f"❌ Ошибка: {e}"


async def find_team(team_name):
    logger.info(f"🔍 Поиск: {team_name}")

    soup = await fetch_hltv(f"{HLTV_URL}/search?term={team_name}")
    if not soup:
        return None, "❌ Ошибка поиска"

    try:
        link = None
        for a in soup.find_all('a', class_='result-item'):
            href = a.get('href', '')
            if '/team/' in href:
                link = href
                logger.info(f"✓ Найдено: {link}")
                break

        if not link:
            return None, f"❌ '{team_name}' не найдена"

        team_soup = await fetch_hltv(f"{HLTV_URL}{link}")
        if not team_soup:
            return None, "❌ Не удалось загрузить"

        header = team_soup.find('h1', class_='team-header-name')
        full_name = header.get_text(strip=True) if header else team_name

        players = []
        container = team_soup.find('div', class_='team-profile-team-members')
        if container:
            for p in container.find_all('a', class_='name'):
                name = p.get_text(strip=True)
                if name:
                    players.append(name)

        if not players:
            for p in team_soup.find_all('a', class_='name')[:5]:
                name = p.get_text(strip=True)
                if name and len(name) < 30:
                    players.append(name)

        if not players:
            return None, f"⚠️ Состав не найден"

        roster = f"👥 <b>{full_name}:</b>\n\n"
        for i, p in enumerate(players[:5], 1):
            roster += f"{i}. {p}\n"

        coach = team_soup.find('div', class_='coach')
        if coach:
            c_link = coach.find('a')
            if c_link:
                roster += f"\n🧢 <b>Тренер:</b> {c_link.get_text(strip=True)}"

        return roster, None

    except Exception as e:
        logger.error(f"❌ Team error: {e}")
        return None, f"❌ Ошибка: {e}"


# ================= ⌨️ КЛАВИАТУРА =================

def get_keyboard():
    kb = [
        [KeyboardButton(text="🔥 Ближайший матч")],
        [KeyboardButton(text="🏆 Рейтинг HLTV")],
        [KeyboardButton(text="👥 Составы команд")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ================= 🎯 ОБРАБОТЧИКИ =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>CS2 Stats Bot</b>\n\nВыбери 👇",
        reply_markup=get_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🔥 Ближайший матч")
async def show_match(message: types.Message):
    msg = await message.answer("⏳ Загружаю...")
    result = await get_upcoming_matches()
    await msg.edit_text(result, parse_mode="HTML")


@dp.message(F.text == "🏆 Рейтинг HLTV")
async def show_rank(message: types.Message):
    msg = await message.answer("⏳ Загружаю...")
    result = await get_ranking()
    await msg.edit_text(result, parse_mode="HTML")


@dp.message(F.text == "👥 Составы команд")
async def ask_team(message: types.Message, state: FSMContext):
    await message.answer(
        "✍️ <b>Напиши команду:</b>\n\n"
        "Примеры: NAVI, FaZe, Vitality\n\n"
        "Или /cancel",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TeamSearch.waiting_for_team)


@dp.message(TeamSearch.waiting_for_team)
async def handle_team_search(message: types.Message, state: FSMContext):
    team = message.text.strip()
    msg = await message.answer(f"🔍 Ищу {team}...")
    result, error = await find_team(team)

    if error:
        await msg.edit_text(error, parse_mode="HTML")
    else:
        await msg.edit_text(result, parse_mode="HTML")

    await state.clear()
    await message.answer("Что дальше?", reply_markup=get_keyboard())


@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Отменено", reply_markup=get_keyboard())


@dp.message()
async def fallback(message: types.Message):
    await message.answer("❓ Не понял. Используй кнопки или /start", reply_markup=get_keyboard())


# ================= 🚀 ЗАПУСК =================

async def main():
    logger.info("🤖 Запуск...")
    try:
        me = await bot.me()
        logger.info(f"✓ Бот: @{me.username}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"💥 {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
