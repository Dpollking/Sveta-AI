from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """Replaceable model adapter. Business logic never talks to a provider SDK directly."""

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 400) -> str:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...
