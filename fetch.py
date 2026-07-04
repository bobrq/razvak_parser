"""
fetch.py — забирает свежие посты из публичных Telegram-каналов через
их веб-превью (https://t.me/s/имя_канала), без логина и без API-ключей
Telegram. Складывает сырой текст в raw_posts.jsonl (по одному JSON на строку).

Ограничение: веб-превью показывает только последние ~20 постов канала,
поэтому скрипт рассчитан на регулярный запуск (например раз в 20 минут),
а не на разовый сбор истории.

Запуск:
    python fetch.py
"""

import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

CHANNELS = [c.strip() for c in os.environ["CHANNELS"].split(",") if c.strip()]
OUTPUT_FILE = "raw_posts.jsonl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def load_seen_ids() -> set[str]:
    """Чтобы не сохранять один и тот же пост дважды при повторных запусках."""
    seen = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["uid"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return seen


def fetch_channel(channel: str) -> list[dict]:
    url = f"https://t.me/s/{channel}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []

    for wrap in soup.select(".tgme_widget_message_wrap"):
        msg_div = wrap.select_one(".tgme_widget_message")
        if not msg_div:
            continue

        post_id_attr = msg_div.get("data-post", "")  # формат: channel/123
        if "/" not in post_id_attr:
            continue
        msg_id = post_id_attr.split("/")[-1]

        text_div = msg_div.select_one(".tgme_widget_message_text")
        text = text_div.get_text("\n", strip=True) if text_div else ""
        if not text:
            continue  # пропускаем посты без текста (только фото/видео)

        time_tag = msg_div.select_one("time")
        date_iso = time_tag.get("datetime") if time_tag else None

        posts.append({
            "uid": f"{channel}:{msg_id}",
            "channel": channel,
            "text": text,
            "date": date_iso,
            "link": f"https://t.me/{channel}/{msg_id}",
        })

    return posts


def main():
    seen_ids = load_seen_ids()
    new_count = 0

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        for channel in CHANNELS:
            print(f"→ читаю канал @{channel}")
            try:
                posts = fetch_channel(channel)
            except Exception as e:
                print(f"  ⚠ ошибка на канале @{channel}: {e}")
                continue

            for post in posts:
                if post["uid"] in seen_ids:
                    continue
                out.write(json.dumps(post, ensure_ascii=False) + "\n")
                seen_ids.add(post["uid"])
                new_count += 1

            time.sleep(1)  # вежливая пауза между каналами

    print(f"Готово. Новых постов сохранено: {new_count}")


if __name__ == "__main__":
    main()
