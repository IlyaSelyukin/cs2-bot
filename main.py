"""
CS2 Tier 1 Stats Bot
Telegram bot for Counter-Strike 2 esports statistics.

Features:
- Upcoming Tier 1 matches schedule
- Recent match results
- Tier 1 tournament list
- HLTV Top-20 team ranking
- Team roster lookup (Top-20 only)

Author: Your Name
License: MIT
"""

import asyncio
import logging
import os
import sys
from signal import SIGINT, SIGTERM

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("BOT_TOKEN environment variable is not set")
    sys.exit(1)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()


class TeamSearch(StatesGroup):
    """FSM state for team search workflow."""
    waiting_for_team = State()


# DATA LAYER - Tier 1 CS2 Esports Data
TIER1_EVENTS: list[dict[str, str]] = [
    {"name": "IEM Cologne 2026", "dates": "15.07 - 27.07", "prize": "$1,000,000", "location": "Кёльн, Германия"},
    {"name": "BLAST Premier Spring Final", "dates": "12.06 - 16.06", "prize": "$425,000", "location": "Лондон, Великобритания"},
    {"name": "ESL Pro League Season 20", "dates": "28.05 - 23.06", "prize": "$850,000", "location": "Мальта"},
    {"name": "PGL Major Copenhagen 2026", "dates": "21.03 - 07.04", "prize": "$1,250,000", "location": "Копенгаген, Дания"},
    {"name": "BLAST Premier World Final", "dates": "11.12 - 15.12", "prize": "$1,000,000", "location": "Абу-Даби, ОАЭ"},
    {"name": "IEM Katowice 2027", "dates": "29.01 - 09.02", "prize": "$1,000,000", "location": "Катовице, Польша"},
    {"name": "ESL One Hamburg", "dates": "24.10 - 27.10", "prize": "$500,000", "location": "Гамбург, Германия"},
    {"name": "BLAST Premier Fall Final", "dates": "27.11 - 01.12", "prize": "$425,000", "location": "Копенгаген, Дания"},
]

UPCOMING_MATCHES: list[dict[str, str]] = [
    {"date": "22.05 18:00 MSK", "event": "IEM Cologne 2026", "team1": "NAVI", "team2": "FaZe Clan", "format": "BO3"},
    {"date": "22.05 21:00 MSK", "event": "BLAST Premier Spring", "team1": "Vitality", "team2": "Team Spirit", "format": "BO3"},
    {"date": "23.05 16:00 MSK", "event": "ESL Pro League S20", "team1": "MOUZ", "team2": "G2 Esports", "format": "BO1"},
    {"date": "23.05 19:30 MSK", "event": "IEM Cologne 2026", "team1": "Astralis", "team2": "Heroic", "format": "BO3"},
    {"date": "24.05 18:00 MSK", "event": "BLAST Premier Spring", "team1": "FURIA", "team2": "Team Liquid", "format": "BO3"},
    {"date": "24.05 21:00 MSK", "event": "ESL Pro League S20", "team1": "ENCE", "team2": "BIG", "format": "BO1"},
    {"date": "25.05 17:00 MSK", "event": "IEM Cologne 2026", "team1": "Ninjas in Pyjamas", "team2": "Complexity", "format": "BO3"},
    {"date": "25.05 20:00 MSK", "event": "BLAST Premier Spring", "team1": "Eternal Fire", "team2": "9z Team", "format": "BO3"},
    {"date": "26.05 18:30 MSK", "event": "ESL Pro League S20", "team1": "The MongolZ", "team2": "Lynn Vision", "format": "BO1"},
    {"date": "26.05 21:30 MSK", "event": "IEM Cologne 2026", "team1": "SAW", "team2": "Imperial", "format": "BO3"},
    {"date": "27.05 19:00 MSK", "event": "BLAST Premier Spring", "team1": "Vitality", "team2": "NAVI", "format": "BO3"},
    {"date": "28.05 18:00 MSK", "event": "ESL Pro League S20", "team1": "FaZe Clan", "team2": "Team Spirit", "format": "BO1"},
    {"date": "29.05 20:00 MSK", "event": "IEM Cologne 2026", "team1": "G2 Esports", "team2": "Astralis", "format": "BO3"},
    {"date": "30.05 17:30 MSK", "event": "BLAST Premier Spring", "team1": "MOUZ", "team2": "FURIA", "format": "BO3"},
    {"date": "31.05 19:00 MSK", "event": "ESL Pro League S20", "team1": "Heroic", "team2": "ENCE", "format": "BO1"},
]

RECENT_RESULTS: list[dict[str, str]] = [
    {"date": "21.05", "event": "BLAST Premier Spring", "team1": "Vitality", "team2": "G2 Esports", "score": "2:1", "winner": "Vitality"},
    {"date": "20.05", "event": "IEM Cologne 2026", "team1": "NAVI", "team2": "MOUZ", "score": "2:0", "winner": "NAVI"},
    {"date": "20.05", "event": "ESL Pro League S20", "team1": "FaZe Clan", "team2": "Team Liquid", "score": "2:1", "winner": "FaZe Clan"},
    {"date": "19.05", "event": "BLAST Premier Spring", "team1": "Team Spirit", "team2": "Astralis", "score": "2:0", "winner": "Team Spirit"},
    {"date": "19.05", "event": "IEM Cologne 2026", "team1": "Heroic", "team2": "ENCE", "score": "1:2", "winner": "ENCE"},
    {"date": "18.05", "event": "ESL Pro League S20", "team1": "FURIA", "team2": "BIG", "score": "2:0", "winner": "FURIA"},
    {"date": "18.05", "event": "BLAST Premier Spring", "team1": "Ninjas in Pyjamas", "team2": "Complexity", "score": "2:1", "winner": "Ninjas in Pyjamas"},
    {"date": "17.05", "event": "IEM Cologne 2026", "team1": "Eternal Fire", "team2": "9z Team", "score": "0:2", "winner": "9z Team"},
    {"date": "16.05", "event": "ESL Pro League S20", "team1": "The MongolZ", "team2": "SAW", "score": "2:0", "winner": "The MongolZ"},
    {"date": "15.05", "event": "BLAST Premier Spring", "team1": "Lynn Vision", "team2": "Imperial", "score": "1:2", "winner": "Imperial"},
]

TOP_20_TEAMS: list[tuple[int, str, str]] = [
    (1, "Vitality", "🇫🇷"), (2, "Team Spirit", "🇷🇺"), (3, "NAVI", "🇺🇦"),
    (4, "MOUZ", "🇩🇪"), (5, "FaZe Clan", "🇪🇺"), (6, "Astralis", "🇩🇰"),
    (7, "G2 Esports", "🇪🇺"), (8, "Heroic", "🇩🇰"), (9, "FURIA", "🇧🇷"),
    (10, "Ninjas in Pyjamas", "🇸🇪"), (11, "Team Liquid", "🇺🇸"),
    (12, "ENCE", "🇫🇮"), (13, "Complexity", "🇺🇸"), (14, "BIG", "🇩🇪"),
    (15, "Eternal Fire", "🇹🇷"), (16, "9z Team", "🇦🇷"),
    (17, "The MongolZ", "🇲🇳"), (18, "Lynn Vision", "🇨🇳"),
    (19, "SAW", "🇵🇹"), (20, "Imperial", "🇧🇷"),
]

TEAM_ROSTERS: dict[str, dict] = {
    "vitality": {"name": "Team Vitality", "flag": "🇫🇷", "players": ["ZywOo", "apEX", "flameZ", "mezii", "Spinx"], "coach": "Djokovic"},
    "spirit": {"name": "Team Spirit", "flag": "🇷🇺", "players": ["donk", "zont1x", "magixx", "chopper", "sh1ro"], "coach": "hally"},
    "navi": {"name": "Natus Vincere", "flag": "🇺🇦", "players": ["iM", "jL", "b1t", "w0nderful", "Aleksib"], "coach": "B1ad3"},
    "mouz": {"name": "MOUZ", "flag": "🇩🇪", "players": ["torzsi", "xertioN", "siuhy", "Jimpphat", "Brollan"], "coach": "glow"},
    "faze": {"name": "FaZe Clan", "flag": "🇪🇺", "players": ["karrigan", "rain", "frozen", "ropz", "broky"], "coach": "RobbaN"},
    "astralis": {"name": "Astralis", "flag": "🇩🇰", "players": ["device", "blameF", "Staehr", "jabbi", "br0"], "coach": "ave"},
    "g2": {"name": "G2 Esports", "flag": "🇪🇺", "players": ["NiKo", "m0NESY", "huNter-", "malbsMd", "Snax"], "coach": "TaZ"},
    "heroic": {"name": "Heroic", "flag": "🇩🇰", "players": ["cadiaN", "stavn", "TeSeS", "sjuush", "nicoodoz"], "coach": "HUNDEN"},
    "furia": {"name": "FURIA", "flag": "🇧🇷", "players": ["arT", "KSCERATO", "yuurih", "chelo", "drop"], "coach": "guerri"},
    "nip": {"name": "Ninjas in Pyjamas", "flag": "🇸🇪", "players": ["REZ", "hampus", "isak", "LnZ", "arteme"], "coach": "GG"},
    "liquid": {"name": "Team Liquid", "flag": "🇺🇸", "players": ["NAF", "EliGE", "nitr0", "oSee", "YEKINDAR"], "coach": "adreN"},
    "ence": {"name": "ENCE", "flag": "🇫🇮", "players": ["Snappi", "doto", "Spinx", "xertioN", "Aleksib"], "coach": "zonic"},
    "complexity": {"name": "Complexity Gaming", "flag": "🇺🇸", "players": ["floppy", "Ricky", "moose", "hades", "insani"], "coach": "Sonic"},
    "big": {"name": "BIG", "flag": "🇩🇪", "players": ["syrsoN", "tiziaN", "k1to", "smooya", "tabseN"], "coach": "sycrone"},
    "eternal fire": {"name": "Eternal Fire", "flag": "🇹🇷", "players": ["woxic", "XANTARES", "calix", "mojo", "qRaxs"], "coach": "enghh"},
    "9z": {"name": "9z Team", "flag": "🇦🇷", "players": ["heat", "mazino", "nzr", "adverso", "foxz"], "coach": "onur"},
    "mongolz": {"name": "The MongolZ", "flag": "🇲🇳", "players": ["bLaze", "910", "Techno4K", "Mzinho", "Interz"], "coach": "Enkhtaivan"},
    "lynn": {"name": "Lynn Vision", "flag": "🇨🇳", "players": ["Attacker", "Summer", "Patience", "Westmelon", "aumaN"], "coach": "Autumn"},
    "saw": {"name": "SAW", "flag": "🇵🇹", "players": ["roman", "picky", "morta", "fox", "RAiLWAY"], "coach": "zakk"},
    "imperial": {"name": "Imperial Esports", "flag": "🇧🇷", "players": ["LUCAS1", "nzr", "artzin", "rich", "dyo"], "coach": "onur"},
}

TEAM_ALIASES: dict[str, str] = {
    "vitality": "vitality", "team vitality": "vitality",
    "spirit": "spirit", "team spirit": "spirit",
    "navi": "navi", "natus vincere": "navi", "na`vi": "navi",
    "mouz": "mouz", "mousesports": "mouz",
    "faze": "faze", "faze clan": "faze",
    "astralis": "astralis",
    "g2": "g2", "g2 esports": "g2",
    "heroic": "heroic",
    "furia": "furia",
    "nip": "nip", "ninjas in pyjamas": "nip",
    "liquid": "liquid", "team liquid": "liquid",
    "ence": "ence",
    "complexity": "complexity", "comp": "complexity",
    "big": "big",
    "eternal fire": "eternal fire", "ef": "eternal fire",
    "9z": "9z", "9z team": "9z",
    "mongolz": "mongolz", "the mongolz": "mongolz",
    "lynn": "lynn", "lynn vision": "lynn",
    "saw": "saw",
    "imperial": "imperial",
}


# BUSINESS LOGIC - Data Formatters
def format_upcoming_matches(matches: list[dict], limit: int = 5) -> str:
    """Format upcoming matches for display."""
    if not matches:
        return "⚠️ Ближайших матчей пока нет."
    
    lines = ["🔥 <b>БЛИЖАЙШИЕ МАТЧИ TIER 1:</b>\n"]
    for idx, match in enumerate(matches[:limit], 1):
        indicator = "🔴" if idx == 1 else "⚪"
        lines.append(
            f"{indicator} {idx}. 📅 <b>{match['date']}</b>\n"
            f"   🏆 {match['event']}\n"
            f"   ⚔️ <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"
        )
    return "\n".join(lines)


def format_recent_results(results: list[dict], limit: int = 7) -> str:
    """Format recent match results for display."""
    if not results:
        return "⚠️ Результатов пока нет."
    
    lines = ["✅ <b>РЕЗУЛЬТАТЫ (Tier 1):</b>\n"]
    for res in results[:limit]:
        t1 = f"🏆 {res['team1']}" if res['winner'] == res['team1'] else res['team1']
        t2 = f"🏆 {res['team2']}" if res['winner'] == res['team2'] else res['team2']
        lines.append(
            f"📅 {res['date']} | {res['event']}\n"
            f"⚔️ {t1} vs {t2}\n"
            f"📊 Счёт: <b>{res['score']}</b>\n"
        )
    return "\n".join(lines)


def format_tier1_events(events: list[dict]) -> str:
    """Format Tier 1 tournament list for display."""
    lines = ["🎪 <b>TIER 1 ТУРНИРЫ 2026:</b>\n"]
    for idx, event in enumerate(events, 1):
        lines.append(
            f"{idx}. <b>{event['name']}</b>\n"
            f"   📅 {event['dates']}\n"
            f"   💰 Призовой фонд: {event['prize']}\n"
            f"   📍 {event['location']}\n"
        )
    return "\n".join(lines)


def format_ranking(teams: list[tuple[int, str, str]]) -> str:
    """Format HLTV-style ranking for display."""
    lines = [f"#{rank} {flag} <b>{name}</b>" for rank, name, flag in teams]
    return "🏆 <b>Рейтинг мира по HLTV (Топ-20):</b>\n\n" + "\n".join(lines) + "\n\n<i>Обновлено: май 2026</i>"


def find_team_roster(query: str) -> tuple[str | None, str | None]:
    """
    Search for team roster in Top-20 database.
    
    Returns:
        tuple: (roster_text, error_message) - one will be None
    """
    key = query.lower().strip()
    key = TEAM_ALIASES.get(key, key)
    
    roster = TEAM_ROSTERS.get(key)
    if not roster:
        for k, v in TEAM_ROSTERS.items():
            if key in k or key in v["name"].lower():
                roster = v
                break
    
    if not roster:
        available = ", ".join(f"{r}. {n}" for r, n, _ in TOP_20_TEAMS[:10])
        return None, f"❌ <b>'{query}'</b> не найдена в Топ-20.\n\n📋 <b>Доступные команды:</b>\n<code>{available}</code>"
    
    name = roster["name"]
    flag = roster.get("flag", "")
    players = roster["players"]
    coach = roster.get("coach")
    position = next((r for r, n, _ in TOP_20_TEAMS if n.lower() in name.lower()), "?")
    
    lines = [f"👥 {flag} <b>{name}</b> (#{position} в мире)\n"]
    for idx, player in enumerate(players, 1):
        lines.append(f"{idx}. <b>{player}</b>")
    if coach:
        lines.append(f"\n🧢 <b>Тренер:</b> {coach}")
    
    return "\n".join(lines), None


# UI LAYER - Keyboards & Handlers
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Generate main menu keyboard."""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔥 Ближайшие матчи"), KeyboardButton(text="✅ Результаты")],
        [KeyboardButton(text="🎪 Tier 1 турниры"), KeyboardButton(text="🏆 Топ-20")],
        [KeyboardButton(text="👥 Составы команд")]
    ], resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Handle /start command."""
    await message.answer(
        "👋 <b>CS2 Tier 1 Stats Bot</b>\n\n"
        "• 🔥 Ближайшие матчи Tier 1\n"
        "• ✅ Результаты за последнюю неделю\n"
        "• 🎪 Расписание турниров Tier 1\n"
        "• 🏆 Рейтинг мира по HLTV (Топ-20)\n"
        "• 👥 Составы команд (только Топ-20)\n\n"
        "Выберите действие 👇",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🔥 Ближайшие матчи")
async def handle_upcoming_matches(message: types.Message) -> None:
    """Handle upcoming matches request."""
    result = format_upcoming_matches(UPCOMING_MATCHES)
    await message.answer(result, parse_mode="HTML")


@dp.message(F.text == "✅ Результаты")
async def handle_results(message: types.Message) -> None:
    """Handle recent results request."""
    result = format_recent_results(RECENT_RESULTS)
    await message.answer(result, parse_mode="HTML")


@dp.message(F.text == "🎪 Tier 1 турниры")
async def handle_events(message: types.Message) -> None:
    """Handle Tier 1 events request."""
    result = format_tier1_events(TIER1_EVENTS)
    await message.answer(result, parse_mode="HTML")


@dp.message(F.text == "🏆 Топ-20")
async def handle_ranking(message: types.Message) -> None:
    """Handle ranking request."""
    result = format_ranking(TOP_20_TEAMS)
    await message.answer(result, parse_mode="HTML")


@dp.message(F.text == "👥 Составы команд")
async def handle_ask_team(message: types.Message, state: FSMContext) -> None:
    """Prompt user for team name."""
    preview = "\n".join(f"{r}. {f} {n}" for r, n, f in TOP_20_TEAMS)
    await message.answer(
        f"✍️ <b>Введите название команды из Топ-20:</b>\n\n"
        f"📋 <b>Список команд:</b>\n<code>{preview}</code>\n\n"
        f"Или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TeamSearch.waiting_for_team)


@dp.message(TeamSearch.waiting_for_team, F.text.lower() == "/cancel")
async def handle_cancel_search(message: types.Message, state: FSMContext) -> None:
    """Cancel team search."""
    await state.clear()
    await message.answer("✅ Отменено", reply_markup=get_main_keyboard())


@dp.message(TeamSearch.waiting_for_team)
async def handle_team_search(message: types.Message, state: FSMContext) -> None:
    """Process team name and return roster."""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("❌ Слишком короткое название")
        return
    
    roster, error = find_team_roster(query)
    response = error if error else roster
    await message.answer(response, parse_mode="HTML")
    
    await state.clear()
    await message.answer("Что дальше?", reply_markup=get_main_keyboard())


@dp.message(Command("cancel"))
async def handle_global_cancel(message: types.Message, state: FSMContext) -> None:
    """Global cancel handler."""
    await state.clear()
    await message.answer("✅ Отменено", reply_markup=get_main_keyboard())


@dp.message()
async def handle_fallback(message: types.Message) -> None:
    """Handle unrecognized commands."""
    await message.answer(
        "❓ Команда не распознана. Используйте кнопки меню или /start",
        reply_markup=get_main_keyboard()
    )


# APPLICATION LIFECYCLE
async def on_startup() -> None:
    """Execute on bot startup."""
    logger.info("Bot starting up...")
    me = await bot.get_me()
    logger.info(f"Bot @{me.username} initialized successfully")


async def on_shutdown() -> None:
    """Execute on bot shutdown."""
    logger.info("Bot shutting down...")
    await bot.session.close()


async def main() -> None:
    """Main entry point."""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        await dp.start_polling(bot)
    except (SIGINT, SIGTERM):
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
