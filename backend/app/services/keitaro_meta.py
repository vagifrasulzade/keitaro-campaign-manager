"""Domains / groups / traffic sources lookups + default resolution by name."""

from dataclasses import dataclass

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.integrations.keitaro.base import JSON, KeitaroClientProtocol


def _norm_domain(name: str) -> str:
    return name.lower().removeprefix("https://").removeprefix("http://").strip("/")


def _find_id(items: list[JSON], name: str, *, domain: bool = False) -> int | None:
    norm = _norm_domain if domain else (lambda v: v.strip().lower())
    target = norm(name)
    for item in items:
        if norm(str(item.get("name", ""))) == target:
            return int(item["id"])
    if len(items) == 1:  # only one choice on this tracker → use it
        return int(items[0]["id"])
    return None


def campaign_url(domain_name: str | None, alias: str) -> str | None:
    if not domain_name:
        return None
    return f"https://{_norm_domain(domain_name)}/{alias}"


@dataclass
class Lookups:
    domains: list[JSON]
    groups: list[JSON]
    traffic_sources: list[JSON]
    default_domain_id: int | None
    default_group_id: int | None
    default_traffic_source_id: int | None

    def domain_name(self, domain_id: int | None) -> str | None:
        for d in self.domains:
            if int(d["id"]) == domain_id:
                return str(d.get("name"))
        return None


class KeitaroMeta:
    def __init__(self, keitaro: KeitaroClientProtocol, settings: Settings):
        self.keitaro = keitaro
        self.settings = settings

    async def lookups(self) -> Lookups:
        domains = await self.keitaro.list_domains()
        groups = await self.keitaro.list_groups("campaigns")
        sources = await self.keitaro.list_traffic_sources()
        return Lookups(
            domains=domains,
            groups=groups,
            traffic_sources=sources,
            default_domain_id=_find_id(domains, self.settings.default_domain, domain=True),
            default_group_id=_find_id(groups, self.settings.default_group),
            default_traffic_source_id=_find_id(sources, self.settings.default_traffic_source),
        )

    @staticmethod
    def resolve(explicit: int | None, default: int | None, items: list[JSON], label: str) -> int:
        value = explicit if explicit is not None else default
        if value is None:
            raise ValidationError(f"{label} is not selected and no default {label} was found in Keitaro")
        if not any(int(i["id"]) == value for i in items):
            raise ValidationError(f"{label} #{value} does not exist in Keitaro")
        return value
