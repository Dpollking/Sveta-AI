import httpx

from .base import LLMAdapter


class OpenAICompatibleAdapter(LLMAdapter):
    """Works against any OpenAI-compatible /v1/chat/completions server (llama.cpp server, vLLM)."""

    def __init__(self, base_url: str, model: str, timeout: float = 30.0, api_key: str = "not-needed"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = api_key

    async def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 400) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.is_error:
                # raise_for_status() alone only reports the status line — the
                # provider's actual reason (bad key, disallowed model, quota,
                # moderation, ...) is in the JSON/text body, which is worth
                # having in the traceback rather than just "403 Forbidden".
                raise RuntimeError(f"{resp.status_code} from {resp.request.url}: {resp.text[:500]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
