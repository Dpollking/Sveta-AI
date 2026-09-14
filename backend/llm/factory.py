from backend.core.config import settings

from .base import LLMAdapter
from .ollama_adapter import OllamaAdapter
from .llama_cpp_adapter import LlamaCppAdapter
from .vllm_adapter import VllmAdapter

_adapter: LLMAdapter | None = None


def get_llm_adapter() -> LLMAdapter:
    global _adapter
    if _adapter is not None:
        return _adapter

    provider = settings.llm_provider.lower()
    if provider == "ollama":
        _adapter = OllamaAdapter(settings.llm_base_url, settings.llm_model, settings.llm_timeout)
    elif provider == "llama_cpp":
        _adapter = LlamaCppAdapter(settings.llm_base_url, settings.llm_model, settings.llm_timeout, settings.llm_api_key or "not-needed")
    elif provider == "vllm":
        _adapter = VllmAdapter(settings.llm_base_url, settings.llm_model, settings.llm_timeout, settings.llm_api_key or "not-needed")
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
    return _adapter
