from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import random

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот для анализа CRM-данных.\n\n"
        "Я умею:\n"
        "• показывать основные показатели;\n"
        "• находить лучших менеджеров;\n"
        "• показывать распределение заказов по статусам;\n"
        "• строить график выручки;\n"
        "• отвечать на вопросы по данным;\n"
        "• формировать рекомендации.\n\n"
        "Доступные команды:\n"
        "/metrics\n"
        "/top_managers\n"
        "/status_report\n"
        "/chart_revenue\n"
        "/recommendations"
    )
    await message.answer(text)