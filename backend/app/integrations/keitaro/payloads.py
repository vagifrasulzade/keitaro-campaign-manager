"""Builders for Keitaro request bodies — kept pure so they are trivial to unit-test."""

from app.integrations.keitaro.base import JSON


def campaign_payload(
    *,
    name: str,
    alias: str,
    domain_id: int,
    group_id: int,
    traffic_source_id: int,
) -> JSON:
    return {
        "name": name,
        "alias": alias,
        "type": "position",  # "Ротация потоков: по позиции"
        "state": "active",
        "cost_type": "CPC",
        "cost_value": 0,
        "cost_currency": "USD",
        "cost_auto": True,  # "Из параметра 'cost'"
        "domain_id": domain_id,
        "group_id": group_id,
        "traffic_source_id": traffic_source_id,
    }


def geo_redirect_stream_payload(
    *, campaign_id: int, countries: list[str], redirect_url: str, position: int = 1
) -> JSON:
    """Flow 1: visitors from `countries` → HTTP redirect to `redirect_url`."""
    return {
        "campaign_id": campaign_id,
        "name": f"Geo {','.join(countries)} → {redirect_url}",
        "type": "regular",
        "position": position,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": redirect_url,
        "collect_clicks": True,
        "filters": [{"name": "country", "mode": "accept", "payload": countries}],
    }


def offers_stream_payload(*, campaign_id: int, offers: list[JSON], position: int = 2) -> JSON:
    """Flow 2: everybody else → offers (split by share)."""
    return {
        "campaign_id": campaign_id,
        "name": "Offers",
        "type": "regular",
        "position": position,
        "state": "active",
        "schema": "landings",
        "action_type": "http",
        "collect_clicks": True,
        "offers": offers,
    }


def offer_item(offer_id: int, share: int) -> JSON:
    return {"offer_id": offer_id, "share": share, "state": "active"}
