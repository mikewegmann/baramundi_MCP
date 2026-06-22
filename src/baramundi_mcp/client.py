import os
import httpx
from dotenv import load_dotenv

load_dotenv()


class BaramundiAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"baramundi API error {status_code}: {message}")


class BaramundiClient:
    """Async HTTP client für die baramundi bConnect REST API."""

    def __init__(self):
        base_url = os.environ.get("BARAMUNDI_API_URL")
        api_key = os.environ.get("BARAMUNDI_API_TOKEN")

        if not base_url:
            raise ValueError("BARAMUNDI_API_URL ist nicht gesetzt (prüfe .env)")
        if not api_key:
            raise ValueError("BARAMUNDI_API_TOKEN ist nicht gesetzt (prüfe .env)")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={
                "X-API-Key": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
            verify=os.environ.get("BARAMUNDI_SSL_VERIFY", "true").lower() != "false",
        )

    async def get(self, path: str, params: dict | None = None) -> dict | list:
        response = await self._client.get(path.lstrip("/"), params=params)
        return self._handle_response(response)

    async def get_paged(self, path: str, params: dict | None = None) -> list[dict]:
        """Gibt nur die 'data'-Liste einer paginierten Antwort zurück."""
        result = await self.get(path, params)
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        if isinstance(result, list):
            return result
        return [result]

    async def post(self, path: str, body: dict | None = None) -> dict | list:
        response = await self._client.post(path.lstrip("/"), json=body or {})
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict | list:
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise BaramundiAPIError(response.status_code, str(detail))
        return response.json()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()
