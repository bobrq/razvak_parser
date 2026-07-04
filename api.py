"""
api.py — отдаёт вакансии из vacancies.db как JSON, с теми же фильтрами,
что и на фронте (grade, format, city, поиск по тексту).

Запуск:
    pip install fastapi uvicorn
    uvicorn api:app --reload --port 8000

Проверить:
    http://localhost:8000/api/vacancies
"""

import json
import sqlite3

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# чтобы фронт на другом домене/порту мог достучаться
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "vacancies.db"


@app.get("/api/vacancies")
def get_vacancies(
    q: str = Query(default=""),
    grade: str = Query(default=""),
    format: str = Query(default=""),
    city: str = Query(default=""),
):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    sql = "SELECT * FROM vacancies WHERE 1=1"
    params = []

    if grade:
        sql += " AND grade = ?"
        params.append(grade)
    if format:
        sql += " AND format = ?"
        params.append(format)
    if city:
        sql += " AND city = ?"
        params.append(city)
    if q:
        sql += " AND (role LIKE ? OR stack LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]

    sql += " ORDER BY date DESC LIMIT 200"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for row in rows:
        item = dict(row)
        item["stack"] = json.loads(item["stack"] or "[]")
        result.append(item)

    return result
