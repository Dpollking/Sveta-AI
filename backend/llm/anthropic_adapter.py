from anthropic import AsyncAnthropic

from .base import LLMAdapter


class AnthropicAdapter(LLMAdapter):
    """Claude via the official Anthropic API — a real hosted model with no
    self-hosted server to run, unlike the ollama/llama_cpp/vllm providers.

    Reads ANTHROPIC_API_KEY from the environment (the SDK's own default
    credential resolution) — set it directly, there's no separate app
    setting for it.
    """

    def __init__(self, model: str, timeout: float = 30.0):
        self.model = model
        self.client = AsyncAnthropic(timeout=timeout)

    async def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 400) -> str:
        system, turns = None, messages
        if messages and messages[0]["role"] == "system":
            system, turns = messages[0]["content"], messages[1:]

        kwargs = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "messages": turns}
        if system is not None:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return next((block.text for block in response.content if block.type == "text"), "").strip()

    async def health(self) -> bool:
        try:
            await self.client.models.retrieve(self.model)
            return True
        except Exception:
            return False
