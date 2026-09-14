# Sveta AI — Safe Romance Fraud Simulator

Образовательный исследовательский симулятор романтического мошенничества.
Пользователь просто переписывается со Светой; backend в это время ведёт
полностью скрытую от него аналитику: доверие, привязанность, подозрение,
red flags, сценарные события — по [мастер-спецификации проекта](../"Sveta AI — Master Project Specification.md").

## Принципы

- Local-first: основная модель — локальный Qwen через llama.cpp/vLLM/Ollama, заменяемый через `LLMAdapter`.
- Backend, а не LLM, решает, что происходит: факты, red flags, сценарные события и risk-score полностью детерминированы кодом в `backend/services/`; модель только выбирает формулировку.
- Пользователь никогда не видит internal state (trust/suspicion/attraction/risk/strategy/RAG) — см. `backend/models/schemas.py: ChatResponsePublic` и `backend/api/routes_session.py`.
- Реальные пароли, OTP, документы, биометрия и интимные фото пользователя не принимаются системой ни при каких обстоятельствах (`backend/services/extraction.py: contains_real_credential_like_content`).

## Быстрый запуск

```bash
python -m venv .venv
./.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Открыть `http://127.0.0.1:8000` — чат пользователя.
Открыть `http://127.0.0.1:8000/admin` — админ-панель (нужен `ADMIN_TOKEN` из `.env`).

Без запущенной локальной модели (`ollama serve` + `ollama pull qwen2.5`, либо
`llama-server` в режиме llama.cpp) система продолжает работать в fallback-режиме
с шаблонными репликами (§33 спеки) — вся остальная логика (сценарии, risk engine,
память) при этом полностью функциональна и тестируема.

## Desktop .exe

Для запуска без терминала и Python — один файл `SvetaAI.exe` с нативным
окном чата (через `pywebview`), без браузерной вкладки:

```bash
pip install -r requirements-desktop.txt
build_exe.bat
```

Результат — `dist\SvetaAI.exe`. Его можно скопировать куда угодно: при
первом запуске рядом появится папка `data\` (SQLite + при включённом RAG —
индекс Chroma), которая переживает перезапуски. Админ-панель остаётся
доступна в браузере на `http://127.0.0.1:8765/admin`, пока exe запущен.

Собирайте из venv **без** `requirements-rag.txt` — иначе в exe попадут
`torch`/`sentence-transformers` (~1 ГБ и заметно дольше холодный старт);
без них `backend/services/rag.py` просто использует keyword-фолбэк.

### RAG (опционально)

```bash
pip install -r requirements-rag.txt
```

Без этих зависимостей `backend/services/rag.py` автоматически откатывается на
keyword-поиск по тем же документам из `knowledge/` — приложение не падает.

## Тесты

```bash
pytest
```

## Структура

См. `docs/ARCHITECTURE.md`.
