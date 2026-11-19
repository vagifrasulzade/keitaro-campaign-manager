"""In-memory Keitaro. Used by tests and by KEITARO_MOCK=true demo mode."""

import copy
import itertools
from typing import Any

from app.core.exceptions import KeitaroError, NotFoundError
from app.integrations.keitaro.base import JSON

SAMPLE_OFFERS: list[JSON] = [
    {"id": 3749, "name": "Miaflow [BEAUTY-RO-BE_0009] [pl - - spin ro -] 2. Основной, Румыния JS", "state": "active", "country": ["RO"]},
    {"id": 3717, "name": "Miaflow [BEAUTY-RO-BE_0008] [pl - - prize ro -] 1. Основной, Румыния JS", "state": "active", "country": ["RO"]},
    {"id": 3801, "name": "Cardiol [HEALTH-MX-0012] [pl - - prelend mx -] Основной, Мексика", "state": "active", "country": ["MX"]},
    {"id": 3802, "name": "Cardiol [HEALTH-MX-0013] [pl - - quiz mx -] Основной, Мексика", "state": "active", "country": ["MX"]},
    {"id": 3910, "name": "Keto Slim [DIET-AU-0004] [pl - - news au -] Основной, Австралия", "state": "active", "country": ["AU"]},
    {"id": 3911, "name": "Keto Slim [DIET-AU-0005] [pl - - review au -] Основной, Австралия", "state": "active", "country": ["AU"]},
    {"id": 4002, "name": "Hondrexil [JOINTS-RO-0021] [pl - - doctor ro -] Основной, Румыния", "state": "active", "country": ["RO"]},
]


class FakeKeitaroClient:
    def __init__(self) -> None:
        self.domains: list[JSON] = [{"id": 1813, "name": "kylovoa.com"}]
        self.groups: list[JSON] = [
            {"id": 10332, "name": "FORTESTS", "type": "campaigns"},
            {"id": 9799, "name": "Other group", "type": "campaigns"},
        ]
        self.sources: list[JSON] = [{"id": 836, "name": "FORTESTS"}]
        self.offers: list[JSON] = copy.deepcopy(SAMPLE_OFFERS)
        self.campaigns: dict[int, JSON] = {}
        self.streams: dict[int, JSON] = {}
        self._ids = itertools.count(100)
        self.calls: list[tuple[str, Any]] = []
        # name of a method that should raise KeitaroError (failure simulation in tests)
        self.fail_on: str | None = None

    def _check_fail(self, method: str) -> None:
        self.calls.append((method, None))
        if self.fail_on == method:
            raise KeitaroError(f"simulated failure in {method}", upstream_status=500)

    # --- lookups -----------------------------------------------------------
    async def list_domains(self) -> list[JSON]:
        return copy.deepcopy(self.domains)

    async def list_groups(self, group_type: str = "campaigns") -> list[JSON]:
        return copy.deepcopy(self.groups)

    async def list_traffic_sources(self) -> list[JSON]:
        return copy.deepcopy(self.sources)

    async def list_offers(self) -> list[JSON]:
        return copy.deepcopy(self.offers)

    async def get_offer(self, offer_id: int) -> JSON:
        for offer in self.offers:
            if offer["id"] == offer_id:
                return copy.deepcopy(offer)
        raise NotFoundError(f"Keitaro: offer {offer_id} not found")

    # --- campaigns ---------------------------------------------------------
    async def list_campaigns(self) -> list[JSON]:
        return [copy.deepcopy(c) for c in self.campaigns.values() if c["state"] != "deleted"]

    async def get_campaign(self, campaign_id: int) -> JSON:
        campaign = self.campaigns.get(campaign_id)
        if not campaign or campaign["state"] == "deleted":
            raise NotFoundError(f"Keitaro: campaign {campaign_id} not found")
        return copy.deepcopy(campaign)

    async def create_campaign(self, payload: JSON) -> JSON:
        self._check_fail("create_campaign")
        campaign: JSON = {"id": next(self._ids), **copy.deepcopy(payload)}
        domain = next((d for d in self.domains if d["id"] == payload.get("domain_id")), None)
        campaign["domain"] = f"https://{domain['name']}/" if domain else None
        self.campaigns[campaign["id"]] = campaign
        self.calls[-1] = ("create_campaign", payload)
        return copy.deepcopy(campaign)

    async def delete_campaign(self, campaign_id: int) -> None:
        self._check_fail("delete_campaign")
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]["state"] = "deleted"

    # --- streams -----------------------------------------------------------
    async def list_campaign_streams(self, campaign_id: int) -> list[JSON]:
        await self.get_campaign(campaign_id)
        streams = [s for s in self.streams.values() if s["campaign_id"] == campaign_id]
        return copy.deepcopy(sorted(streams, key=lambda s: s.get("position", 0)))

    async def create_stream(self, payload: JSON) -> JSON:
        self._check_fail("create_stream")
        self.calls[-1] = ("create_stream", payload)
        stream: JSON = {"id": next(self._ids), "offers": [], "filters": [], **copy.deepcopy(payload)}
        stream["offers"] = [{"id": next(self._ids), "stream_id": stream["id"], **o} for o in stream["offers"]]
        self.streams[stream["id"]] = stream
        return copy.deepcopy(stream)

    async def update_stream(self, stream_id: int, payload: JSON) -> JSON:
        self._check_fail("update_stream")
        self.calls[-1] = ("update_stream", payload)
        stream = self.streams.get(stream_id)
        if not stream:
            raise NotFoundError(f"Keitaro: stream {stream_id} not found")
        data = copy.deepcopy(payload)
        if "offers" in data:  # Keitaro replaces the offers array completely
            data["offers"] = [{"id": next(self._ids), "stream_id": stream_id, **o} for o in data["offers"]]
        stream.update(data)
        return copy.deepcopy(stream)
