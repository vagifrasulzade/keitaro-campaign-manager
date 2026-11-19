"""Part 1 — "создаватор": one call → Keitaro campaign with two streams.

Flow 1 (position 1): country ∈ geo  → redirect to google.com
Flow 2 (position 2): everyone else  → selected offer (100 %)

If anything fails after the campaign exists in Keitaro, the campaign is
deleted (archived) so no half-configured campaign is left behind.
"""

import logging
import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.integrations.keitaro import payloads
from app.integrations.keitaro.base import KeitaroClientProtocol
from app.models import Campaign, OfferStatus, Stream, StreamOffer
from app.schemas.campaign import CampaignCreate
from app.services.campaign_sync import load_campaign
from app.services.keitaro_meta import KeitaroMeta, campaign_url
from app.services.offer_catalog import OfferCatalog

logger = logging.getLogger(__name__)

ALIAS_ALPHABET = string.ascii_letters + string.digits


def generate_alias(length: int = 7) -> str:
    return "".join(secrets.choice(ALIAS_ALPHABET) for _ in range(length))


class CampaignCreator:
    def __init__(
        self,
        session: AsyncSession,
        keitaro: KeitaroClientProtocol,
        catalog: OfferCatalog,
        settings: Settings,
    ):
        self.session = session
        self.keitaro = keitaro
        self.catalog = catalog
        self.settings = settings

    async def create(self, data: CampaignCreate) -> Campaign:
        offer = await self.catalog.get(data.offer_id)  # 404 if the offer doesn't exist

        meta = KeitaroMeta(self.keitaro, self.settings)
        lookups = await meta.lookups()
        s = self.settings
        domain_id = meta.resolve(
            data.domain_id, lookups.default_domain_id, lookups.domains, "domain", s.default_domain
        )
        group_id = meta.resolve(data.group_id, lookups.default_group_id, lookups.groups, "group", s.default_group)
        source_id = meta.resolve(
            data.traffic_source_id,
            lookups.default_traffic_source_id,
            lookups.traffic_sources,
            "traffic source",
            s.default_traffic_source,
        )

        alias = generate_alias()
        remote_campaign = await self.keitaro.create_campaign(
            payloads.campaign_payload(
                name=data.name,
                alias=alias,
                domain_id=domain_id,
                group_id=group_id,
                traffic_source_id=source_id,
            )
        )
        keitaro_campaign_id = int(remote_campaign["id"])
        alias = remote_campaign.get("alias") or alias

        try:
            geo_stream = await self.keitaro.create_stream(
                payloads.geo_redirect_stream_payload(
                    campaign_id=keitaro_campaign_id,
                    countries=data.geo,
                    redirect_url=self.settings.geo_redirect_url,
                )
            )
            offer_stream = await self.keitaro.create_stream(
                payloads.offers_stream_payload(
                    campaign_id=keitaro_campaign_id,
                    offers=[payloads.offer_item(offer.id, 100)],
                )
            )
        except AppError:
            logger.warning("Stream creation failed, rolling back Keitaro campaign %s", keitaro_campaign_id)
            await self._rollback_remote(keitaro_campaign_id)
            raise

        campaign = Campaign(
            keitaro_id=keitaro_campaign_id,
            name=data.name,
            alias=alias,
            url=campaign_url(remote_campaign.get("domain") or lookups.domain_name(domain_id), alias),
            geo=data.geo,
            domain_id=domain_id,
            group_id=group_id,
            traffic_source_id=source_id,
            origin="creator",
        )
        campaign.streams = [
            Stream(
                keitaro_id=int(geo_stream["id"]),
                name=geo_stream.get("name") or "Geo → Google",
                position=1,
                type="regular",
                schema="redirect",
                action_type="http",
                action_payload=self.settings.geo_redirect_url,
                state="active",
                filters=[{"name": "country", "mode": "accept", "payload": data.geo}],
                offers=[],
            ),
            Stream(
                keitaro_id=int(offer_stream["id"]),
                name=offer_stream.get("name") or "Offers",
                position=2,
                type="regular",
                schema="landings",
                action_type="http",
                state="active",
                filters=[],
                offers=[
                    StreamOffer(
                        offer_id=offer.id,
                        offer_name=offer.name,
                        share=100,
                        status=OfferStatus.ACTIVE.value,
                        is_pinned=False,
                        published_share=100,
                        published_status=OfferStatus.ACTIVE.value,
                    )
                ],
            ),
        ]
        self.session.add(campaign)
        await self.session.commit()
        logger.info("Created campaign %s (%s) in Keitaro", keitaro_campaign_id, data.name)
        return await load_campaign(self.session, keitaro_campaign_id, fresh=True)  # type: ignore[return-value]

    async def _rollback_remote(self, keitaro_campaign_id: int) -> None:
        try:
            await self.keitaro.delete_campaign(keitaro_campaign_id)
        except AppError:
            logger.exception("Rollback failed: campaign %s stays in Keitaro", keitaro_campaign_id)
