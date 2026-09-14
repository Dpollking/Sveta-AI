from .openai_compatible import OpenAICompatibleAdapter


class VllmAdapter(OpenAICompatibleAdapter):
    """Qwen served by vLLM's OpenAI-compatible server, for higher-throughput deployments."""
