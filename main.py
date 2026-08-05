import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv

from app.handlers import router


Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
    handlers=[
        RotatingFileHandler(
            filename="logs/app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


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


async def main() -> None:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Переменная BOT_TOKEN не найдена в .env"
        )

    bot = Bot(token=token)
    dp = Dispatcher()

    dp.include_router(router)

    await set_bot_commands(bot)

    logger.info("Бот запущен")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")

    except Exception:
        logger.exception("Критическая ошибка при работе бота")