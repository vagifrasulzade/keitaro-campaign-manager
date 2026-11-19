"""HTTP client for Keitaro Admin API v1 (https://admin-api.docs.keitaro.io)."""

import logging
from typing import Any

import httpx

from app.core.exceptions import ForbiddenError, KeitaroError, NotFoundError
from app.integrations.keitaro.base import JSON

logger = logging.getLogger(__name__)


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 20.0):
        if not api_key:
            raise KeitaroError("KEITARO_API_KEY is not set (or set KEITARO_MOCK=true for demo mode)")
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Api-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.exception("Keitaro %s %s failed", method, path)
            raise KeitaroError(f"Keitaro is unreachable: {exc}") from exc

        if response.status_code == 404:
            raise NotFoundError(f"Keitaro: {path} not found")
        if response.status_code == 403:
            raise ForbiddenError(f"Keitaro: this API key has no access to {path}")
        if response.is_error:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            logger.warning("Keitaro %s %s → %s %s", method, path, response.status_code, body)
            raise KeitaroError(
                f"Keitaro {method} {path} returned {response.status_code}: {body}",
                upstream_status=response.status_code,
                payload=body,
            )
        if not response.content:
            return None
        return response.json()

    # --- lookups -----------------------------------------------------------
    async def list_domains(self) -> list[JSON]:
        return await self._request("GET", "/domains")

    async def list_groups(self, group_type: str = "campaigns") -> list[JSON]:
        return await self._request("GET", "/groups", params={"type": group_type})

    async def list_traffic_sources(self) -> list[JSON]:
        return await self._request("GET", "/traffic_sources")

    async def list_offers(self) -> list[JSON]:
        return await self._request("GET", "/offers")

    async def get_offer(self, offer_id: int) -> JSON:
        return await self._request("GET", f"/offers/{offer_id}")

    # --- campaigns ---------------------------------------------------------
    async def list_campaigns(self) -> list[JSON]:
        return await self._request("GET", "/campaigns")

    async def get_campaign(self, campaign_id: int) -> JSON:
        return await self._request("GET", f"/campaigns/{campaign_id}")

    async def create_campaign(self, payload: JSON) -> JSON:
        return await self._request("POST", "/campaigns", json=payload)

    async def delete_campaign(self, campaign_id: int) -> None:
        # Keitaro moves the campaign to archive
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    # --- streams -----------------------------------------------------------
    async def list_campaign_streams(self, campaign_id: int) -> list[JSON]:
        return await self._request("GET", f"/campaigns/{campaign_id}/streams")

    async def create_stream(self, payload: JSON) -> JSON:
        return await self._request("POST", "/streams", json=payload)

    async def update_stream(self, stream_id: int, payload: JSON) -> JSON:
        return await self._request("PUT", f"/streams/{stream_id}", json=payload)
