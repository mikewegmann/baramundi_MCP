import os
import httpx
from dotenv import load_dotenv

load_dotenv()


class MacmonAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"macmon API error {status_code}: {message}")


class MacmonClient:
    """Async HTTP client für die macmon NAC REST API (Basic Auth)."""

    def __init__(self):
        base_url = os.environ.get("MACMON_API_URL")
        user = os.environ.get("MACMON_USER")
        password = os.environ.get("MACMON_PASSWORD")

        if not base_url:
            raise ValueError("MACMON_API_URL ist nicht gesetzt (prüfe .env)")
        if not user or not password:
            raise ValueError("MACMON_USER oder MACMON_PASSWORD ist nicht gesetzt (prüfe .env)")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            auth=httpx.BasicAuth(user, password),
            headers={"Accept": "application/json"},
            timeout=30.0,
            verify=os.environ.get("MACMON_SSL_VERIFY", "true").lower() != "false",
        )

    async def get(self, path: str, params: dict | None = None) -> dict | list:
        response = await self._client.get(path.lstrip("/"), params=params)
        return self._handle_response(response)

    async def put(self, path: str, body: dict | None = None) -> dict | list:
        response = await self._client.put(path.lstrip("/"), json=body or {})
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict | list:
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise MacmonAPIError(response.status_code, str(detail))
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()
