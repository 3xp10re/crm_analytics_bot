import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()


OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")


def clean_sql_response(response: str) -> str:
    response = response.strip()

    code_block = re.search(
        r"```(?:sql)?\s*(.*?)```",
        response,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if code_block:
        response = code_block.group(1).strip()

    return response.rstrip(";").strip() + ";"


async def generate_sql(question: str, database_schema: str,) -> str:
    system_prompt = """
Ты создаёшь SQL-запросы для PostgreSQL.

Тебе будет передана структура базы данных и вопрос пользователя.

Все таблицы находятся в схеме "pechi".
При обращении к таблицам всегда используй полное имя, например:
pechi.amocrm_leads
pechi.amocrm_users
...

Правила:
1. Используй только таблицы и колонки из переданной структуры базы.
2. Создавай только один запрос SELECT.
3. Запрещено использовать INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, CREATE, GRANT, REVOKE и другие команды изменения данных.
4. Для соединения таблиц используй только описанные связи.
5. Не придумывай таблицы, колонки и связи.
6. Если пользователь просит список строк, добавляй LIMIT 100.
7. Для подсчёта строк используй COUNT(*).
8. Учитывай, что используется PostgreSQL.
9. Верни только SQL-запрос.
10. Не добавляй объяснения, Markdown и блоки ```sql.
11. Если пользователь просит рейтинг, топ или сравнение,
    возвращай не только название объекта, но и числовой показатель,
    по которому выполнена сортировка.
""".strip()


    user_prompt = f"""
СТРУКТУРА БАЗЫ ДАННЫХ:

{database_schema}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:

{question}
""".strip()

    request_data = {
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
            "temperature": 0,
        },
    }

    url = f"{OLLAMA_URL.rstrip('/')}/api/chat"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                json=request_data,
            )

            response.raise_for_status()

    except httpx.ConnectError as error:
        raise RuntimeError(
            "Не удалось подключиться к Ollama. "
            "Проверь, что Ollama запущена."
        ) from error

    except httpx.TimeoutException as error:
        raise RuntimeError(
            "Ollama не успела ответить за 120 секунд."
        ) from error

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"Ollama вернула HTTP-ошибку: "
            f"{error.response.status_code}. "
            f"Ответ: {error.response.text}"
        ) from error

    data = response.json()

    try:
        llm_response = data["message"]["content"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            f"Неожиданный формат ответа Ollama: {data}"
        ) from error

    sql = clean_sql_response(llm_response)

    if not sql:
        raise RuntimeError(
            "Модель вернула пустой SQL-запрос."
        )

    return sql


async def generate_answer(question: str, sql_result: list[dict]) -> str:
    result_json = json.dumps(
        sql_result,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    system_prompt = """
Ты CRM-аналитик.

Тебе передаются вопрос пользователя и результат SQL-запроса.

Правила:
1. Отвечай на русском языке.
2. Используй только переданные данные.
3. Не придумывай числа, факты, причины и выводы.
4. Не упоминай SQL, JSON, базу данных или внутреннюю работу программы.
5. Не используй фразы «по данному запросу» и «согласно результату».
6. Если пользователь просит рейтинг, оформляй ответ нумерованным списком.
7. Для каждого элемента рейтинга указывай название и показатель.
8. Не добавляй лишний итог после списка.
9. Если результат пустой, скажи: «По вашему запросу данные не найдены».
10. Пиши грамотно, коротко и естественно.
""".strip()

    user_prompt = f"""
ВОПРОС ПОЛЬЗОВАТЕЛЯ:

{question}

РЕЗУЛЬТАТ SQL-ЗАПРОСА:

{result_json}

Сформулируй готовый ответ пользователю.
""".strip()

    request_data = {
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
            "temperature": 0,
        },
    }

    url = f"{OLLAMA_URL.rstrip('/')}/api/chat"

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
        ) as client:
            response = await client.post(
                url,
                json=request_data,
            )

        response.raise_for_status()

    except httpx.ConnectError as error:
        raise RuntimeError(
            "Не удалось подключиться к Ollama."
        ) from error

    except httpx.TimeoutException as error:
        raise RuntimeError(
            "Ollama не успела сформировать ответ."
        ) from error

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            "Ollama вернула HTTP-ошибку "
            f"{error.response.status_code}: "
            f"{error.response.text}"
        ) from error

    data = response.json()

    try:
        answer = data["message"]["content"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            f"Неожиданный ответ Ollama: {data}"
        ) from error

    answer = answer.strip()

    if not answer:
        raise RuntimeError(
            "Модель вернула пустой ответ."
        )

    return answer