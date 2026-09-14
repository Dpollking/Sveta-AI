# Архитектура (реализация v0.4)

## Слои и их файлы

```
USER ──> POST /api/chat (routes_chat.py)
           │
           ▼
      sveta_engine.handle_message()   ── единая точка входа на реплику
           │
           ├─ extraction.py            факты, user-initiated red flags,
           │                            real-credential safety net,
           │                            boundary/suspicion классификация
           │
           ├─ scenario_engine.py       resolve_pending() → pick_next()
           │                            (единственный источник правды
           │                            о том, что сейчас происходит)
           │
           ├─ risk_engine.py           P0-P3 веса из knowledge/red_flags.json,
           │                            score = f(red_flags, message_count, money_sent)
           │
           ├─ strategy_manager.py      категория тона (§13), event wins,
           │                            иначе rotation с оглядкой на suspicion
           │
           ├─ rag.py                   ChromaDB+multilingual-MiniLM, либо
           │                            keyword fallback без heavy deps
           │
           ├─ prompts.py               system prompt (§22) + event hint,
           │                            никогда не передаёт числовые trust/suspicion
           │
           ├─ llm/factory.py           OllamaAdapter | LlamaCppAdapter | VllmAdapter
           │
           ├─ response_validator.py    ловит утечку слов «trust/стратегия/RAG» и
           │                            реальные запросы пароля/OTP/карты → fallback
           │
           └─ memory.py                SQLite: sessions/messages/research_events/
                                        red_flag_events (§34)

ADMIN ──> /api/admin/*  (routes_admin.py, требует X-Admin-Token)
USER  ──> /api/session/{id}, /api/session/{id}/report — ничего внутреннего
```

## Ключевой инвариант

`ChatResponsePublic` (`backend/models/schemas.py`) — единственное, что видит
пользователь: `session_id, reply, day, media`. Ни один публичный роут не
возвращает `SessionState` целиком. Полный `SessionState` уходит только через
`/api/admin/sessions/{id}`, за токеном.

## Сознательные отклонения от буквы спеки

- **§4 `/api/biography`, `/api/memory/{id}`** сделаны админскими
  (`/api/admin/biography`, состояние сессии — частью `/api/admin/sessions/{id}`),
  а не публичными флэт-роутами: публичный доступ к ним противоречил бы §2.
- **§27 Debrief** сделан публичным (`/api/session/{id}/report`) и доступным
  в любой момент, не только «после завершения» — соответствует тексту UX-раздела
  («при необходимости — финальный образовательный разбор»), возвращает только
  человекочитаемые находки и уровень риска, никогда сырые числа.
- **День симуляции** продвигается эвристикой `day = 1 + user_messages // 3`
  вместо привязки к реальному времени — детерминированно и тестируемо;
  реальную временную симуляцию (задержки, «Света не отвечает ночью») можно
  добавить позже без изменения контракта API.
- **`rag_documents` таблица из §34** не создана отдельно от файлов
  `knowledge/*.json` — избежано дублирование источника истины между SQL и
  файлами/Chroma; Chroma персистентно хранит embeddings в `data/chroma/`.
- **Media** — только метаданные (`media/assets.json`), без реальных
  изображений: генерация/подбор безопасных вымышленных фото Светы — отдельная
  задача, не входящая в текущий этап (нет прав на реальные фото людей, а
  генерация изображений — вне рамок этой сессии).

## Что дальше (см. `ROADMAP.md`)

Admin-редакторы (Scenario/Biography editors с записью, не только чтением),
LoRA training pipeline, dataset export, полноценная система смены дня по
времени, реальные media-ассеты.
