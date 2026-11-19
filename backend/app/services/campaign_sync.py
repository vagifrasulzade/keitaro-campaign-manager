"""Import / refresh a Keitaro campaign and its streams into the local staging DB.

Reconciliation rules for offers of every stream:
* offer present in Keitaro            → local row = Keitaro values (draft is discarded)
* published locally, gone in Keitaro  → kept as "removed" (archived, can be brought back)
* local draft never pushed            → deleted
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.keitaro.base import KeitaroClientProtocol
from app.models import Campaign, OfferStatus, Stream, StreamOffer
from app.services.keitaro_meta import campaign_url
from app.services.offer_catalog import OfferCatalog


def _remote_status(state: str | None) -> str:
    return OfferStatus.ACTIVE.value if (state or "active") == "active" else OfferStatus.REMOVED.value


async def load_campaign(session: AsyncSession, keitaro_campaign_id: int, *, fresh: bool = False) -> Campaign | None:
    """Campaign with streams and offers eagerly loaded (async sessions can't lazy-load)."""
    stmt = (
        select(Campaign)
        .where(Campaign.keitaro_id == keitaro_campaign_id)
        .options(selectinload(Campaign.streams).selectinload(Stream.offers))
    )
    if fresh:
        stmt = stmt.execution_options(populate_existing=True)
    return await session.scalar(stmt)


class CampaignSync:
    def __init__(self, session: AsyncSession, keitaro: KeitaroClientProtocol, catalog: OfferCatalog):
        self.session = session
        self.keitaro = keitaro
        self.catalog = catalog

    async def get_local(self, keitaro_campaign_id: int, *, fresh: bool = False) -> Campaign | None:
        return await load_campaign(self.session, keitaro_campaign_id, fresh=fresh)

    async def get_or_import(self, keitaro_campaign_id: int) -> Campaign:
        return await self.get_local(keitaro_campaign_id) or await self.sync(keitaro_campaign_id)

    async def sync(self, keitaro_campaign_id: int) -> Campaign:
        remote = await self.keitaro.get_campaign(keitaro_campaign_id)
        remote_streams = await self.keitaro.list_campaign_streams(keitaro_campaign_id)

        campaign = await self.get_local(keitaro_campaign_id)
        if campaign is None:
            campaign = Campaign(keitaro_id=keitaro_campaign_id, origin="import", geo=[], streams=[])
            self.session.add(campaign)

        campaign.name = remote.get("name") or f"Campaign #{keitaro_campaign_id}"
        campaign.alias = remote.get("alias") or ""
        campaign.domain_id = remote.get("domain_id")
        campaign.group_id = remote.get("group_id")
        campaign.traffic_source_id = remote.get("traffic_source_id")
        if remote.get("domain"):  # Keitaro returns e.g. "https://kylovoa.com/"
            campaign.url = campaign_url(remote["domain"], campaign.alias)
        elif campaign.domain_id and not campaign.url:
            domains = await self.keitaro.list_domains()
            name = next((d["name"] for d in domains if int(d["id"]) == campaign.domain_id), None)
            campaign.url = campaign_url(name, campaign.alias)

        offer_ids = {int(o["offer_id"]) for s in remote_streams for o in (s.get("offers") or [])}
        names = await self.catalog.names(offer_ids)

        local_by_kid = {s.keitaro_id: s for s in campaign.streams}
        seen: set[int] = set()
        for item in remote_streams:
            kid = int(item["id"])
            seen.add(kid)
            stream = local_by_kid.get(kid)
            if stream is None:
                stream = Stream(keitaro_id=kid, offers=[])
                campaign.streams.append(stream)
            self._apply_stream(stream, item)
            self._reconcile_offers(stream, item.get("offers") or [], names)

        for kid, stream in local_by_kid.items():
            if kid not in seen:
                campaign.streams.remove(stream)

        await self.session.commit()
        return await self.get_local(keitaro_campaign_id, fresh=True)  # type: ignore[return-value]

    @staticmethod
    def _apply_stream(stream: Stream, item: dict[str, Any]) -> None:
        stream.name = item.get("name") or ""
        stream.position = int(item.get("position") or 0)
        stream.type = item.get("type") or "regular"
        stream.schema = item.get("schema") or ""
        stream.action_type = item.get("action_type")
        payload = item.get("action_payload")
        stream.action_payload = payload if isinstance(payload, str) or payload is None else str(payload)
        stream.state = item.get("state") or "active"
        stream.filters = [
            {"name": f.get("name"), "mode": f.get("mode"), "payload": f.get("payload")}
            for f in (item.get("filters") or [])
        ]

    @staticmethod
    def _reconcile_offers(stream: Stream, remote_offers: list[dict[str, Any]], names: dict[int, str]) -> None:
        remote = {int(o["offer_id"]): o for o in remote_offers}
        local = {o.offer_id: o for o in stream.offers}

        for offer_id, row in local.items():
            if offer_id in remote:
                continue
            if row.is_published:
                row.status = row.published_status = OfferStatus.REMOVED.value
                row.share = row.published_share = 0
                row.is_pinned = False
            else:
                stream.offers.remove(row)

        for offer_id, data in remote.items():
            row = local.get(offer_id)
            if row is None:
                row = StreamOffer(offer_id=offer_id)
                stream.offers.append(row)
            status = _remote_status(data.get("state"))
            share = int(data.get("share") or 0) if status == OfferStatus.ACTIVE.value else 0
            row.offer_name = names.get(offer_id, row.offer_name or f"Offer #{offer_id}")
            row.share = row.published_share = share
            row.status = row.published_status = status
            row.is_pinned = False
