import asyncio

from app.intent_executor import execute_intent
from app.llm_questions import parse_question_with_llm

async def answer_question_with_llm(question: str,) -> str:
    try:
        intent = await parse_question_with_llm(question)

        return await asyncio.to_thread(
            execute_intent,
            intent,
        )

    except ValueError:
        return (
            "Не удалось корректно определить период. "
            "Попробуйте уточнить месяц, год "
            "или количество дней."
        )

    except Exception as error:
        print(
            "Ошибка LLM-вопроса:",
            repr(error),
        )

        return (
            "Не удалось обработать вопрос. "
            "Попробуйте сформулировать его иначе."
        )
