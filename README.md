# razvak — парсер вакансий из Telegram

## Что это

Три скрипта:

1. **fetch.py** — забирает свежие посты из публичных Telegram-каналов через
   их веб-превью (`t.me/s/имя_канала`) — без логина, без API-ключей Telegram.
   Сохраняет сырые посты в `raw_posts.jsonl`.
2. **parse.py** — отсеивает мусор regex-фильтром, а оставшееся отправляет
   в DeepSeek, чтобы вытащить role/grade/city/salary/stack и т.д.
   Складывает результат в `vacancies.db` (SQLite).
3. **api.py** — маленький FastAPI-сервер, отдаёт вакансии как JSON, чтобы
   сайт мог их подгружать вместо захардкоженного массива.

## Важно про fetch.py

Веб-превью канала показывает только последние ~20 постов — это не полная
история, а "витрина". Поэтому скрипт рассчитан на регулярный запуск (раз в
15-20 минут через cron), а не на разовый сбор архива. Каждый запуск
дозаписывает только новые посты, которых ещё нет в `raw_posts.jsonl`.

## Установка

```bash
pip install -r requirements.txt
pip install fastapi uvicorn   # для api.py
cp .env.example .env
```

Заполни `.env`:

- `DEEPSEEK_API_KEY` — https://platform.deepseek.com/api_keys
- `CHANNELS` — список каналов через запятую, без @ и без https://t.me/

## Запуск

```bash
python fetch.py
python parse.py
uvicorn api:app --reload --port 8000
```

Дальше в браузере: http://localhost:8000/api/vacancies

## Автоматизация

Чтобы данные обновлялись сами, повесь `fetch.py` и `parse.py` на cron:

```
*/20 * * * * cd /path/to/razvak_parser && python fetch.py && python parse.py
```

`api.py` держи запущенным постоянно (например через `pm2` или systemd на VPS).

## Подключение фронта

В файле сайта замени константу `VACANCIES` на:

```js
let VACANCIES = [];
fetch('http://localhost:8000/api/vacancies')
  .then(r => r.json())
  .then(data => { VACANCIES = data; render(); });
```

## Про деньги

DeepSeek на порядок дешевле OpenAI/Anthropic за токен, и часто выдаёт
небольшой стартовый бесплатный баланс новым аккаунтам. Regex-фильтр в
`parse.py` дополнительно режет число вызовов модели — она вызывается
только для постов, которые уже похожи на вакансию.
