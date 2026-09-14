from .openai_compatible import OpenAICompatibleAdapter


class LlamaCppAdapter(OpenAICompatibleAdapter):
    """Local Qwen served by llama.cpp's OpenAI-compatible server (`llama-server`)."""
