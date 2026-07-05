"""
parse.py — читает raw_posts.jsonl, отсеивает то, что явно не вакансия,
а остальное прогоняет через Google Gemini (бесплатный API) и извлекает
структуру (role, grade, format, city, salary, stack, desc), складывая
в общую Postgres-базу (Supabase) — ту же самую, которую читает api.py.

Запуск:
    python parse.py
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

from db import init_db, already_parsed, save_vacancy

load_dotenv()

# Gemini даёт бесплатный доступ (без кредитки) через OpenAI-совместимый
# эндпоинт — меняем только base_url и имя модели
client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL_NAME = "gemini-2.5-flash-lite"

RAW_FILE = "raw_posts.jsonl"

# быстрый фильтр по ключевым словам — экономит вызовы модели
JOB_HINTS = re.compile(
    r"(вакансия|ищем|требуется|нужен|нужна|нужны|hiring|junior|middle|senior|"
    r"зарплата|з/п|оклад|удалённо|удаленно|стажировк)",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """Ты извлекаешь структурированные данные о вакансии из поста \
канала в Telegram про поиск работы. Верни СТРОГО валидный JSON без markdown-обёртки \
и без пояснений, по следующей схеме:

{
  "is_vacancy": true/false,
  "role": "название должности" или null,
  "category": "development" | "marketing" | "design" | "qa" | "management" | "content" | "other",
  "grade": "intern" | "junior" | "middle" | "senior" | null,
  "format": "remote" | "office" | "hybrid" | null,
  "city": "название города" или "Удалённо" или null,
  "salary": "строка как в тексте, например 'от 150 000 ₽'" или null,
  "stack": ["массив", "технологий"],
  "desc": "краткое описание в 1-2 предложения своими словами"
}

Пояснения по category:
- "development" — программисты, разработчики любого стека (frontend, backend, mobile, devops)
- "qa" — тестировщики, QA, TestOps
- "marketing" — маркетологи, таргетологи, SMM-менеджеры, PR
- "design" — дизайнеры любого типа (UI/UX, графика, motion)
- "content" — копирайтеры, редакторы, журналисты, контент-менеджеры
- "management" — менеджеры проектов/продуктов, руководители, HR
- "other" — всё остальное, что не подходит под категории выше

Если пост не является вакансией (реклама, новость, мем и т.п.) — верни \
{"is_vacancy": false} и больше ничего."""


def extract_fields(text: str) -> dict | None:
    from openai import RateLimitError

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            break
        except RateLimitError:
            wait = 40 * (attempt + 1)
            print(f"  ⏳ упёрлись в лимит Gemini, ждём {wait} сек...")
            time.sleep(wait)
    else:
        print("  ⚠ не удалось получить ответ после нескольких попыток, пропускаю")
        return None

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  ⚠ модель вернула невалидный JSON, пропускаю")
        return None

    # иногда модель оборачивает ответ в список — берём первый элемент
    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict) or not data.get("is_vacancy"):
        return None
    return data


def main():
    if not os.path.exists(RAW_FILE):
        print(f"Файл {RAW_FILE} не найден — сначала запусти fetch.py")
        return

    conn = init_db()
    processed, saved = 0, 0

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            uid = record["uid"]

            if already_parsed(conn, uid):
                continue

            processed += 1

            # дешёвый предварительный фильтр — не тратим вызовы модели зря
            if not JOB_HINTS.search(record["text"]):
                continue

            fields = extract_fields(record["text"])
            time.sleep(4.2)  # Gemini 3.1 Flash Lite: лимит 15 запросов/мин
            if fields is None:
                continue

            save_vacancy(conn, {
                "uid": uid,
                "channel": record["channel"],
                "role": fields.get("role"),
                "category": fields.get("category"),
                "grade": fields.get("grade"),
                "format": fields.get("format"),
                "city": fields.get("city"),
                "salary": fields.get("salary"),
                "stack": json.dumps(fields.get("stack", []), ensure_ascii=False),
                "description": fields.get("desc"),
                "date": record["date"],
                "link": record["link"],
            })
            saved += 1
            print(f"  ✓ {fields.get('role')}")

    conn.close()
    print(f"\nОбработано новых постов: {processed}, сохранено вакансий: {saved}")


if __name__ == "__main__":
    main()
