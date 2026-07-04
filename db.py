"""
db.py — общая логика работы с базой Postgres (Supabase).
Используется и в parse.py (запись), и в api.py (чтение) — так оба
сервиса на Render всегда видят одни и те же данные, независимо от того,
на каком именно инстансе они запущены.
"""

import os

import psycopg2
import psycopg2.extras


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                uid TEXT PRIMARY KEY,
                channel TEXT,
                role TEXT,
                grade TEXT,
                format TEXT,
                city TEXT,
                salary TEXT,
                stack TEXT,
                description TEXT,
                date TEXT,
                link TEXT
            )
        """)
    conn.commit()
    return conn


def already_parsed(conn, uid: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM vacancies WHERE uid = %s", (uid,))
        return cur.fetchone() is not None


def save_vacancy(conn, record: dict):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO vacancies
               (uid, channel, role, grade, format, city, salary, stack, description, date, link)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (uid) DO UPDATE SET
                   role = EXCLUDED.role,
                   grade = EXCLUDED.grade,
                   format = EXCLUDED.format,
                   city = EXCLUDED.city,
                   salary = EXCLUDED.salary,
                   stack = EXCLUDED.stack,
                   description = EXCLUDED.description""",
            (
                record["uid"],
                record["channel"],
                record.get("role"),
                record.get("grade"),
                record.get("format"),
                record.get("city"),
                record.get("salary"),
                record.get("stack"),
                record.get("description"),
                record["date"],
                record["link"],
            ),
        )
    conn.commit()


def fetch_vacancies(q="", grade="", format="", city="", limit=200):
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        sql = "SELECT * FROM vacancies WHERE 1=1"
        params = []

        if grade:
            sql += " AND grade = %s"
            params.append(grade)
        if format:
            sql += " AND format = %s"
            params.append(format)
        if city:
            sql += " AND city = %s"
            params.append(city)
        if q:
            sql += " AND (role ILIKE %s OR stack ILIKE %s)"
            params += [f"%{q}%", f"%{q}%"]

        sql += " ORDER BY date DESC LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.close()
    return rows
