"""
api.py — отдаёт вакансии из общей Postgres-базы (Supabase) как JSON,
с теми же фильтрами, что и на фронте (grade, format, city, поиск по тексту).
Также содержит защищённый эндпоинт /run-parser, который запускает сбор
и обработку новых вакансий — его дёргает внешний бесплатный планировщик
(например cron-job.org) по расписанию, раз в сутки.

Запуск:
    uvicorn api:app --host 0.0.0.0 --port $PORT

Проверить:
    /api/vacancies
"""

import json
import os
import subprocess

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db import fetch_vacancies

app = FastAPI()

# чтобы фронт на другом домене/порту мог достучаться
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/vacancies")
def get_vacancies(
    q: str = Query(default=""),
    category: str = Query(default=""),
    grade: str = Query(default=""),
    format: str = Query(default=""),
    city: str = Query(default=""),
):
    rows = fetch_vacancies(q=q, category=category, grade=grade, format=format, city=city)

    result = []
    for row in rows:
        item = dict(row)
        item["stack"] = json.loads(item["stack"] or "[]")
        result.append(item)

    return result


@app.get("/run-parser")
def run_parser(secret: str = Query(default="")):
    """
    Запускает fetch.py + parse.py в фоне и сразу отвечает — так внешний
    планировщик (cron-job.org) не упирается в свой таймаут ожидания ответа,
    пока сам парсинг может идти ещё пару минут.
    """
    expected = os.environ.get("PARSER_SECRET")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    subprocess.Popen("python fetch.py && python parse.py", shell=True)
    return {"status": "started", "note": "парсинг запущен в фоне, проверь /api/vacancies через пару минут"}
