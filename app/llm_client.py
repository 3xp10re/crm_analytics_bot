import json
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()


OLLAMA_URL = (
    os.getenv("OLLAMA_URL")
    or "http://127.0.0.1:11434"
).strip()

OLLAMA_MODEL = (
    os.getenv("OLLAMA_MODEL")
    or "qwen2.5:3b"
).strip()

OLLAMA_TIMEOUT_SECONDS = 120.0


def clean_sql_response(response: str) -> str:

    cleaned_response = response.strip()

    code_block = re.search(
        r"```(?:sql)?\s*(.*?)```",
        cleaned_response,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if code_block:
        cleaned_response = code_block.group(1).strip()

    cleaned_response = re.sub(
        r"^\s*SQL\s*:\s*",
        "",
        cleaned_response,
        flags=re.IGNORECASE,
    )

    cleaned_response = cleaned_response.strip()

    if not cleaned_response:
        raise RuntimeError(
            "Модель вернула пустой SQL-запрос."
        )

    return cleaned_response.rstrip("; \n\t") + ";"


async def chat_with_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0,
) -> str:

    if not OLLAMA_URL:
        raise RuntimeError(
            "Не задан адрес Ollama."
        )

    if not OLLAMA_MODEL:
        raise RuntimeError(
            "Не указана модель Ollama."
        )

    request_data: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    url = f"{OLLAMA_URL.rstrip('/')}/api/chat"

    try:
        async with httpx.AsyncClient(
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                url=url,
                json=request_data,
            )

        response.raise_for_status()

    except httpx.ConnectError as error:
        raise RuntimeError(
            "Не удалось подключиться к Ollama. "
            "Проверь, что приложение Ollama запущено."
        ) from error

    except httpx.TimeoutException as error:
        raise RuntimeError(
            "Ollama не успела сформировать ответ "
            f"за {OLLAMA_TIMEOUT_SECONDS:.0f} секунд."
        ) from error

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            "Ollama вернула HTTP-ошибку "
            f"{error.response.status_code}: "
            f"{error.response.text}"
        ) from error

    except httpx.RequestError as error:
        raise RuntimeError(
            f"Ошибка запроса к Ollama: {error}"
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "Ollama вернула ответ в неизвестном формате."
        ) from error

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            f"Неожиданный формат ответа Ollama: {data}"
        ) from error

    if not isinstance(content, str):
        raise RuntimeError(
            "Поле content в ответе Ollama "
            "не является строкой."
        )

    content = content.strip()

    if not content:
        raise RuntimeError(
            "Модель вернула пустой ответ."
        )

    return content


async def generate_sql(question: str,database_schema: str,) -> str:

    question = question.strip()

    if not question:
        raise ValueError(
            "Вопрос пользователя не может быть пустым."
        )

    if not database_schema.strip():
        raise ValueError(
            "Структура базы данных не может быть пустой."
        )

    system_prompt = """
Ты создаёшь SQL-запросы для PostgreSQL.

Тебе передаются структура базы данных и вопрос пользователя.

Все рабочие таблицы находятся в схеме pechi.
Всегда используй полные имена таблиц с указанием схемы.

Примеры:
pechi.amocrm_leads
pechi.amocrm_users
pechi.amocrm_statuses
pechi.amocrm_pipelines
pechi.amocrm_tasks

Правила:
1. Используй только таблицы и колонки из переданной структуры базы.
2. Создавай ровно один SQL-запрос.
3. Разрешён только запрос SELECT.
4. Запрещены INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
   CREATE, GRANT, REVOKE, COMMENT, COPY и другие операции изменения.
5. Не придумывай таблицы, поля и связи.
6. Для JOIN используй только связи, описанные в структуре базы.
7. Всегда указывай схему pechi перед именем таблицы.
8. Для обычного списка добавляй LIMIT не больше 100.
9. Для COUNT, SUM, AVG, MIN и MAX LIMIT не нужен,
   если запрос возвращает одну агрегированную строку.
10. Для подсчёта всех строк используй COUNT(*).
11. Для рейтинга возвращай название объекта и числовой показатель,
    по которому производится сортировка.
12. Для сравнения статусов или воронок возвращай также их названия.
13. Для дат используй синтаксис PostgreSQL.
14. Добавляй понятные английские псевдонимы через AS.
15. Не добавляй объяснения, комментарии и Markdown.
16. Верни только готовый SQL-запрос.
""".strip()

    user_prompt = f"""
СТРУКТУРА БАЗЫ ДАННЫХ:

{database_schema}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:

{question}

Сформируй один безопасный SELECT-запрос.
""".strip()

    llm_response = await chat_with_ollama(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0,
    )

    return clean_sql_response(llm_response)


async def generate_answer(question: str,sql_result: list[dict],) -> str:

    question = question.strip()

    if not question:
        raise ValueError(
            "Вопрос пользователя не может быть пустым."
        )

    if not sql_result:
        return "По вашему запросу данные не найдены."

    result_json = json.dumps(
        sql_result,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    system_prompt = """
Ты CRM-аналитик.

Тебе передаются вопрос пользователя и результат,
полученный после выполнения SQL-запроса.

Правила:
1. Отвечай только на русском языке.
2. Используй исключительно переданные данные.
3. Не придумывай числа, факты, причины или события.
4. Не упоминай SQL, JSON, базу данных, таблицы,
   модель или внутреннюю работу программы.
5. Отвечай прямо на вопрос пользователя.
6. Если передано одно агрегированное значение,
   сформулируй одно короткое предложение.
7. Один объект с одним числом не является рейтингом.
8. Рейтинг оформляй нумерованным списком только тогда,
   когда пользователь явно просит топ, рейтинг,
   лучших или худших и передано несколько элементов.
9. Для каждого элемента рейтинга указывай название
   и числовой показатель.
10. Для списка статусов, менеджеров или воронок
    используй читаемый список.
11. Не пиши, что данные не найдены,
    если результат содержит хотя бы одну строку.
12. Значение 0 является полноценным результатом,
    а не отсутствием данных.
13. Не используй фразы «по данному запросу»,
    «согласно результату» и похожие канцеляризмы.
14. Не делай выводов, которые невозможно подтвердить
    переданными показателями.
15. Пиши коротко, грамотно и естественно.
""".strip()

    user_prompt = f"""
ВОПРОС ПОЛЬЗОВАТЕЛЯ:

{question}

ПОЛУЧЕННЫЕ ДАННЫЕ:

{result_json}

Сформулируй готовый ответ пользователю.
""".strip()

    return await chat_with_ollama(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0,
    )


async def correct_sql(
    question: str,
    database_schema: str,
    incorrect_sql: str,
    error_message: str,) -> str:

    question = question.strip()
    incorrect_sql = incorrect_sql.strip()
    error_message = error_message.strip()

    if not question:
        raise ValueError(
            "Вопрос пользователя не может быть пустым."
        )

    if not database_schema.strip():
        raise ValueError(
            "Структура базы данных не может быть пустой."
        )

    if not incorrect_sql:
        raise ValueError(
            "Неправильный SQL-запрос не может быть пустым."
        )

    if not error_message:
        raise ValueError(
            "Сообщение об ошибке не может быть пустым."
        )

    system_prompt = """
Ты исправляешь SQL-запросы для PostgreSQL.

Тебе передаются структура базы, вопрос пользователя,
ошибочный SQL и сообщение об ошибке.

Все рабочие таблицы находятся в схеме pechi.
Всегда используй полные имена таблиц.

Примеры:
pechi.amocrm_leads
pechi.amocrm_users
pechi.amocrm_statuses
pechi.amocrm_pipelines
pechi.amocrm_tasks

Правила:
1. Верни ровно один исправленный SQL-запрос.
2. Разрешён только SELECT.
3. Используй только таблицы и колонки из переданной структуры.
4. Используй только описанные связи между таблицами.
5. Не придумывай таблицы, поля и связи.
6. Обязательно учти текст переданной ошибки.
7. Всегда указывай схему pechi перед именами таблиц.
8. Для обычных списков добавляй LIMIT не больше 100.
9. Запрещены INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, CREATE, GRANT, REVOKE, COMMENT и COPY.
10. Не добавляй объяснения, комментарии и Markdown.
11. Верни только исправленный SQL-запрос.
""".strip()

    user_prompt = f"""
СТРУКТУРА БАЗЫ ДАННЫХ:

{database_schema}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:

{question}

ОШИБОЧНЫЙ SQL:

{incorrect_sql}

ТЕКСТ ОШИБКИ:

{error_message}

Исправь запрос и верни только SQL.
""".strip()

    llm_response = await chat_with_ollama(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0,
    )

    return clean_sql_response(llm_response)