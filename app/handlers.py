from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command
import random
import asyncio

from app.metrics import get_current_month_metrics, get_top_managers, get_status_report
from app.charts import create_revenue_chart
from app.question_answering import answer_question_with_llm
from app.recommendations import get_recommendations

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


@router.message(Command("top_managers"))
async def top_managers_handler(message: Message) -> None:
    managers = get_top_managers()

    if not managers:
        await message.answer(
            "За текущий месяц данные по менеджерам отсутствуют."
        )
        return
    
    lines = [
        "🏆 Топ-5 менеджеров за текущий месяц",
        "",
    ]

    for position, manager in enumerate(managers, start=1):
        lines.extend(
             [
                f"{position}. {manager['manager']}",
                f"Заказов: {manager['orders_count']}",
                f"Выручка: {manager['revenue']:,.2f}",
                f"Маржа: {manager['margin']:,.2f}",
                f"Средний чек: {manager['average_check']:,.2f}",
                f"Успешных: {manager['success_rate']:.2f}%",
                "",
            ]
        )

    await message.answer("\n".join(lines))


@router.message(Command("status_report"))
async def status_report_handler(message: Message) -> None:
    statuses = get_status_report()

    if not statuses:
        await message.answer(
            "За текущий месяц данные по статусу заказов отсутствуют."
        )
        return
    
    lines = [
        "📋 Распределение заказов за текущий месяц",
        "",
    ]

    for status in statuses:
        lines.append(
            f"Статус: {status['status_group']}\n"
            f"Количество заказов: {status['orders_count']}\n"
        )

    await message.answer("\n".join(lines))


@router.message(Command("chart_revenue"))
async def chart_revenue_handler(message: Message,) -> None:
    await message.answer(
        "Строю график выручки..."
    )

    chart_path = await asyncio.to_thread(
        create_revenue_chart
    )

    if chart_path is None:
        await message.answer(
            "За последние 30 дней данных по заказам нет."
        )
        return

    photo = FSInputFile(chart_path)

    try:
        await message.answer_photo(
            photo=photo,
            caption=(
                "📈 Выручка по дням "
                "за последние 30 дней"
            ),
        )
    finally:
        chart_path.unlink(missing_ok=True)


@router.message(Command("recommendations"))
async def recommendations_handler(
    message: Message,
) -> None:
    await message.answer(
        "Анализирую CRM-данные..."
    )

    recommendations = await get_recommendations()

    if not recommendations:
        await message.answer(
            "В текущей базе недостаточно данных "
            "для формирования рекомендаций."
        )
        return

    lines = [
        "💡 Рекомендации по CRM-данным",
    ]

    for number, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        lines.append(
            f"{number}. {recommendation}"
        )

    await message.answer(
        "\n\n".join(lines)
    )


@router.message(F.text & ~F.text.startswith("/"))
async def natural_language_handler(message: Message,) -> None:
    await message.answer(
        "Обрабатываю вопрос..."
    )

    answer = await answer_question_with_llm(
        message.text
    )
    await message.answer(answer)