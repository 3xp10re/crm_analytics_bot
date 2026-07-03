from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import random

from metrics import get_current_month_metrics

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


@router.message(Command("metrics"))
async def metrics_handler(message: Message) -> None:
    metrics = get_current_month_metrics()
    text = (
        "📊 Метрики за текущий месяц\n\n"
        f"Количество заказов: {metrics['orders_count']}\n"
        f"Выручка: {metrics['revenue']:,.2f}\n"
        f"Маржа: {metrics['margin']:,.2f}\n"
        f"Средний чек: {metrics['average_check']:,.2f}\n"
        f"Успешных заказов: {metrics['successful_orders']}\n"
        f"Отменённых заказов: {metrics['cancelled_orders']}\n"
        f"Доля отмен: {metrics['cancellation_rate']:.2f}%\n"
        f"Новых клиентов: {metrics['new_clients']}"
    )

    await message.answer(text)