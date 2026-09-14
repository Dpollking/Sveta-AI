# Чему на самом деле "обучаются" модели

## Важная терминологическая оговорка

Qwen **не дообучается** (fine-tuning) — веса модели не меняются. Персонажи
(Света, Сергей) формируются на каждый ход двумя механизмами:

1. **System prompt** ([backend/services/prompts.py](../backend/services/prompts.py)) — биография, стиль речи, текущая тональность, выбранная backend'ом.
2. **RAG** ([backend/services/rag.py](../backend/services/rag.py)) — 1-3 релевантные заметки из базы знаний, подмешиваемые в промпт под текущую тональность/запрос.

Если в будущем понадобится настоящий fine-tuning (LoRA) — см. `docs/ROADMAP.md`, это отдельный, более тяжёлый процесс (датасет диалогов + GPU), сейчас не делается.

## База знаний (`knowledge/`) — то, что реально видит модель

| Файл | Содержимое | Источник |
|---|---|---|
| `manipulations.json` | 11 тактик манипуляции: love bombing, future faking, isolation, guilt tripping, intermittent reinforcement, gaslighting, urgency, trauma bonding, social proof, authority, small commitment. Каждая — определение, сигналы, **ограниченные** `phrasing_hints` (только тон, не сценарий), контрпример нормального поведения. | Переведено/адаптировано из `emotional-fraud-detector` (референс на Cialdini 2001, Forward & Frazier 1997, Stines 2021) |
| `red_flags.json` | 12 red-flag кодов (MESSENGER_MOVE, WORK_ACCESS_DISCLOSED, SUSPICIOUS_LINK, MONEY_REQUEST, BLACKMAIL_SIMULATION и т.д.) с весами по модели P0-P3 и текстом для итогового отчёта | Веса — из мастер-спецификации §12; сама P0-P3 модель — из `emotional-fraud-detector` |
| `scenario.json` | 13 сценарных событий (day 1-18) — что именно происходит на каждом этапе, с условиями срабатывания. **Это решает backend, не LLM.** | Мастер-спецификация §9-10 |
| `educational_material.json` | 4 текста для образовательного отчёта (`/report`) | Собственный текст |
| `personas/sveta/*.json`, `personas/sergey/*.json` | Легенда, характер, стиль речи, таймлайн жизни персонажа | Составлено под каждого персонажа; Сергей — пока плейсхолдер до вашей легенды |
| `sources.json` | Библиография (Cialdini, Forward & Frazier, Stines, Anti-FraudX, emotional-fraud-detector) | — |

## Что сознательно НЕ используется

- **`yogsec/Social-Engineering-Tactics`** и аналогичные наступательные плейбуки — не подключены. Причина: они превращают LLM в свободного манипулятора вместо backend-контролируемого сценария, что ломает главный принцип архитектуры («LLM формулирует, backend решает»).
- **Реальные фото/видео/голос пользователей** — никогда не принимаются и не сохраняются (см. `bot/telegram_bot.py: handle_real_media`, `bot/telegram_userbot.py: handle_real_media`, `backend/services/extraction.py: contains_real_credential_like_content`).

## Как это применяется за один ход диалога

```
сообщение пользователя
  → извлечение фактов + user-initiated red flags (extraction.py, регулярки, детерминировано)
  → разрешение/выбор сценарного события (scenario_engine.py — backend решает ЧТО происходит)
  → пересчёт risk score (risk_engine.py, P0-P3 модель)
  → выбор тональности ответа (strategy_manager.py)
  → RAG: 1-3 заметки под эту тональность (rag.py)
  → сборка system prompt: биография персонажа + тональность + RAG-заметки (prompts.py)
  → генерация ответа (Qwen через LLMAdapter)
  → response_validator.py — проверка, что LLM не проговорился о trust/стратегии/сценарии
  → ответ пользователю
```

## Границы безопасности, действующие независимо от контента

- Доступ к обоим ботам — только по инвайт-коду (`INVITE_CODES`), без него бот не отвечает по существу.
- Реальные пароли/OTP/номера карт — перехватываются и никогда не сохраняются как факты.
- Дебриф (`/report`) — доступен в любой момент, показывает находки человеческим языком, не сырые метрики.
- Все данные — в SQLite за админ-токеном, обычному пользователю не видны trust/suspicion/risk/сценарий.
