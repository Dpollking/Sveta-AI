# Roadmap

## Сделано (v0.4)

- [x] Структура проекта по §35.
- [x] `LLMAdapter` (Ollama / llama.cpp / vLLM), реплика с fallback-шаблонами при недоступности модели.
- [x] SQLite-персистентность: sessions/messages/research_events/red_flag_events.
- [x] RAG (ChromaDB + multilingual embeddings) с keyword-фолбэком без heavy deps.
- [x] Биография + таймлайн Светы (`knowledge/sveta_biography.json`, `sveta_timeline.json`).
- [x] Scenario Engine — граф из 13 событий, day 1–18, backend решает accept/refuse.
- [x] Risk Engine — веса по §12 + P0–P3 классификация + поправка на длину переписки и на факт «перевода денег».
- [x] Strategy Manager — 14 категорий §13, откат при росте suspicion.
- [x] Response Validator — блокирует утечку внутренних терминов и реальные запросы credentials.
- [x] Safety net на реальные пароли/OTP/номера карт во входящих сообщениях — никогда не сохраняются.
- [x] Публичный чат (frontend/) без утечки internal state.
- [x] Админ-панель (admin/) — dashboard, список сессий, детальный просмотр состояния/чата/red flags.
- [x] Тесты: extraction, risk engine, scenario engine, strategy manager, API-контракты (23 теста, зелёные).

## Следующий этап

1. Редактируемые admin-экраны для сценария/биографии/RAG-контента (сейчас read-only).
2. Полноценная временная симуляция дня (не только по количеству сообщений).
3. LLM-анализатор (§23) как дополнительный, не основной, источник сигналов — сверх детерминированного extraction.py.
4. Dataset export (§29) из research_events/red_flag_events в обезличенном виде.
5. LoRA training pipeline и Tools Center по образцу Anti-FraudX.
6. Реальные (вымышленные, с соблюдением прав) медиа-ассеты Светы вместо метаданных-плейсхолдеров.
