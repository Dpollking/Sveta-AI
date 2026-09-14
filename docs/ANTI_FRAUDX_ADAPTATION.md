# Anti-FraudX adaptation map

Anti-FraudX используется как архитектурный референс, не как форк кода.

| Anti-FraudX | Sveta AI |
|---|---|
| `backend/llms/llm_factory.py` (`LlmFactory`) | `backend/llm/factory.py` (`get_llm_adapter`) |
| `backend/llms/ollama_llm.py` / `gemini_llm.py` | `backend/llm/ollama_adapter.py` / `llama_cpp_adapter.py` / `vllm_adapter.py` |
| `backend/services/rag_service.py` (ChromaDB + `sentence-transformers`) | `backend/services/rag.py` — тот же embedding model (`paraphrase-multilingual-MiniLM-L12-v2`), тот же паттерн persistent client + keyword fallback |
| `backend/services/agent_service.py` | `backend/services/sveta_engine.py` |
| `backend/agents/scammer.py` / `system_instructions.py` | `backend/services/prompts.py` |
| Trust meter (`VictimTrustState`) | `SessionState.relationship` (trust/attraction/emotional_attachment/suspicion/intimacy) |
| Tools Center | `admin/` (пока read-only dashboard, без training pipeline) |

## Дополнительно взято из `emotional-fraud-detector` (Claude skill)

P0–P3 весовая модель red flags (`references/red-flags-checklist.md`) и
детализированная таксономия манипуляций (`references/manipulation-tactics.md`)
переведены на русский и адаптированы в `knowledge/red_flags.json` и
`knowledge/manipulations.json` — заметно глубже, чем исходный список из
раннего прототипа `sveta-ai-v0.3`.

## Сознательно не перенесено

- HK-specific ADCC корпус кейсов как domain truth.
- RPG battle/game-механика как основной опыт.
- Реальный сбор credentials, malware, доступ к аккаунтам, биометрия или
  другие операционные шаги атаки.
- Обязательная зависимость от облачного Gemini/иного cloud LLM.
