import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    headers = {}
    if settings.INTERNAL_API_KEY:
        headers["X-API-Key"] = settings.INTERNAL_API_KEY
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac

