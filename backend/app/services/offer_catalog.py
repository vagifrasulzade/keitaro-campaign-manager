"""Offer catalog: Keitaro offers cached locally for autocomplete."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import cast, delete, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.integrations.keitaro.base import KeitaroClientProtocol
from app.models import OfferCache


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class OfferCatalog:
    def __init__(self, session: AsyncSession, keitaro: KeitaroClientProtocol, ttl_seconds: int):
        self.session = session
        self.keitaro = keitaro
        self.ttl = timedelta(seconds=ttl_seconds)

    async def sync(self) -> int:
        remote = await self.keitaro.list_offers()
        now = datetime.now(UTC)
        existing = {o.id: o for o in (await self.session.scalars(select(OfferCache))).all()}
        remote_ids: set[int] = set()

        for item in remote:
            offer_id = int(item["id"])
            remote_ids.add(offer_id)
            row = existing.get(offer_id) or OfferCache(id=offer_id)
            row.name = item.get("name") or f"Offer #{offer_id}"
            row.state = item.get("state") or "active"
            country = item.get("country") or []
            row.country = country if isinstance(country, list) else [country]
            row.synced_at = now
            self.session.add(row)

        stale_ids = set(existing) - remote_ids
        if stale_ids:
            await self.session.execute(delete(OfferCache).where(OfferCache.id.in_(stale_ids)))
        await self.session.commit()
        return len(remote_ids)

    async def _ensure_fresh(self) -> None:
        last_sync = await self.session.scalar(select(func.max(OfferCache.synced_at)))
        if last_sync is None or datetime.now(UTC) - _aware(last_sync) > self.ttl:
            await self.sync()

    async def search(self, query: str, limit: int = 20) -> list[OfferCache]:
        await self._ensure_fresh()
        stmt = select(OfferCache).where(OfferCache.state != "deleted")
        query = query.strip()
        if query:
            conditions = [OfferCache.name.ilike(f"%{query}%")]
            if query.isdigit():
                conditions.append(cast(OfferCache.id, String).like(f"{query}%"))
            stmt = stmt.where(or_(*conditions))
        stmt = stmt.order_by(OfferCache.id.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def get(self, offer_id: int) -> OfferCache:
        """Cached offer; falls back to Keitaro for offers created after the last sync."""
        row = await self.session.get(OfferCache, offer_id)
        if row:
            return row
        remote = await self.keitaro.get_offer(offer_id)  # raises NotFoundError
        if not remote:
            raise NotFoundError(f"Offer {offer_id} not found")
        row = OfferCache(
            id=offer_id,
            name=remote.get("name") or f"Offer #{offer_id}",
            state=remote.get("state") or "active",
            country=remote.get("country") or [],
            synced_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def names(self, offer_ids: set[int]) -> dict[int, str]:
        if not offer_ids:
            return {}
        rows = await self.session.scalars(select(OfferCache).where(OfferCache.id.in_(offer_ids)))
        names = {r.id: r.name for r in rows}
        if len(names) < len(offer_ids):  # unknown offers → refresh cache once
            await self.sync()
            rows = await self.session.scalars(select(OfferCache).where(OfferCache.id.in_(offer_ids)))
            names = {r.id: r.name for r in rows}
        return names
