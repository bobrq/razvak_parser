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
    grade: str = Query(default=""),
    format: str = Query(default=""),
    city: str = Query(default=""),
):
    rows = fetch_vacancies(q=q, grade=grade, format=format, city=city)

    result = []
    for row in rows:
        item = dict(row)
        item["stack"] = json.loads(item["stack"] or "[]")
        result.append(item)

    return result


@app.get("/run-parser")
def run_parser(secret: str = Query(default="")):
    """
    Запускает fetch.py + parse.py по HTTP-запросу.
    Защищено секретным токеном, чтобы никто посторонний не мог
    дёргать это и жечь твою квоту Gemini.
    """
    expected = os.environ.get("PARSER_SECRET")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = subprocess.run(
        "python fetch.py && python parse.py",
        shell=True,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-3000:],
        "stderr": result.stderr[-2000:],
    }
