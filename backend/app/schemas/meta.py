from pydantic import BaseModel


class NamedItem(BaseModel):
    id: int
    name: str


class MetaOut(BaseModel):
    mock_mode: bool
    domains: list[NamedItem]
    groups: list[NamedItem]
    traffic_sources: list[NamedItem]
    default_domain_id: int | None
    default_group_id: int | None
    default_traffic_source_id: int | None


class OfferOut(BaseModel):
    id: int
    name: str
    state: str
    country: list[str]


class SyncResult(BaseModel):
    synced: int
