import httpx


class FhirClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _build_url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict | None:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = self._build_url(path)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                raise

    async def read(self, path: str) -> dict | None:
        return await self._get(path)

    async def post(self, path: str, resource: dict) -> tuple[int, dict | None]:
        """POST a FHIR resource. Returns (status_code, body json or None)."""
        headers = {"Content-Type": "application/fhir+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = self._build_url(path)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=resource)
            try:
                body = response.json() if response.content else None
            except Exception:
                body = None
            return response.status_code, body

    async def search(
        self,
        resource_type: str,
        search_parameters: dict[str, str] | None = None,
    ) -> dict | None:
        return await self._get(resource_type, params=search_parameters)
