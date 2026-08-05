from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command
import asyncio

from app.metrics import get_current_month_metrics, get_top_managers, get_status_report
from app.charts import create_revenue_chart
from app.sql_service import process_query
from app.recommendations import generate_recommendations

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
        f"Количество сделок: {metrics['leads_count']}\n"
        f"Общая сумма сделок: {metrics['total_price']:,.2f}\n"
        f"Средняя сумма сделки: {metrics['average_price']:,.2f}\n"
        f"Активных менеджеров: {metrics['managers_count']}\n"
        f"Сделок без менеджера: "
        f"{metrics['leads_without_manager']}\n"
        f"Сделок без источника: "
        f"{metrics['leads_without_source']}\n"
        f"Сделок без категории: "
        f"{metrics['leads_without_category']}"
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
                f"Сделок: {manager['leads_count']}",
                (
                    "Общая сумма сделок: "
                    f"{manager['total_price']:,.2f}"
                ),
                (
                    "Средняя сумма сделки: "
                    f"{manager['average_price']:,.2f}"
                ),
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
        lines.extend(
            [
                f"Воронка: {status['pipeline_name']}",
                f"Статус: {status['status_name']}",
                f"Количество сделок: {status['leads_count']}",
                (
                    "Общая сумма сделок: "
                    f"{status['total_price']:,.2f}"
                ),
                "",
            ]
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
async def recommendations_handler(message: Message,) -> None:
    try:
        await message.answer(
            "Анализирую показатели CRM..."
        )

        recommendations = await generate_recommendations()

        await message.answer(recommendations)

    except Exception:
        await message.answer(
            "Не удалось сформировать рекомендации. "
            "Попробуйте позже."
        )


@router.message(F.text & ~F.text.startswith("/"))
async def natural_language_handler(message: Message,) -> None:
    await message.answer(
        "Обрабатываю вопрос..."
    )

    answer = await process_query(
        message.text
    )
    await message.answer(answer)