"""
api.py — отдаёт вакансии из общей Postgres-базы (Supabase) как JSON,
с теми же фильтрами, что и на фронте (grade, format, city, поиск по тексту).

Запуск:
    uvicorn api:app --host 0.0.0.0 --port $PORT

Проверить:
    /api/vacancies
"""

import json

from fastapi import FastAPI, Query
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
