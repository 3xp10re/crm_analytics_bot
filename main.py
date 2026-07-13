import sqlite3
import os
import aiogram
import matplotlib
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv

from app.handlers import router


async def main() -> None:
    load_dotenv()
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)
    await set_bot_commands(bot)
    await dp.start_polling(bot)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(
            command="start",
            description="Запуск бота",
        ),
        BotCommand(
            command="metrics",
            description="Метрики за текущий месяц",
        ),
        BotCommand(
            command="top_managers",
            description="Топ менеджеров",
        ),
        BotCommand(
            command="status_report",
            description="Отчёт по статусам",
        ),
        BotCommand(
            command="chart_revenue",
            description="График выручки",
        ),
        BotCommand(
            command="recommendations",
            description="Рекомендации по CRM",
        ),
    ]

    await bot.set_my_commands(commands)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('bot is off')