import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"] is not None
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "ai-service"
    assert payload["data"]["version"] == "1.0.0"
