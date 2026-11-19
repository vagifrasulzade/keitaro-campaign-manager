import os
from collections.abc import AsyncIterator

os.environ.setdefault("KEITARO_MOCK", "true")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.integrations.keitaro import FakeKeitaroClient
from app.main import app


@pytest.fixture
async def session_factory(tmp_path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await engine.dispose()


@pytest.fixture
def keitaro() -> FakeKeitaroClient:
    return FakeKeitaroClient()


@pytest.fixture
async def client(session_factory, keitaro) -> AsyncIterator[AsyncClient]:
    async def _session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.state.keitaro = keitaro
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    app.state.keitaro = None


@pytest.fixture
async def campaign(client) -> dict:
    """Campaign created via Part 1 → returns API response."""
    r = await client.post("/api/v1/campaigns", json={"name": "campaign 2", "geo": "AU", "offer_id": 3749})
    assert r.status_code == 201, r.text
    return r.json()


def offers_stream(campaign: dict) -> dict:
    return next(s for s in campaign["streams"] if s["schema"] == "landings")


def shares(stream: dict) -> dict[int, int]:
    return {o["offer_id"]: o["share"] for o in stream["offers"] if o["status"] == "active"}
