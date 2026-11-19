from fastapi import APIRouter, Query

from app.api.deps import CatalogDep, KeitaroDep, SettingsDep
from app.schemas.meta import MetaOut, NamedItem, OfferOut, SyncResult
from app.services.keitaro_meta import KeitaroMeta

router = APIRouter(tags=["lookups"])


def _named(items: list[dict]) -> list[NamedItem]:
    return [NamedItem(id=int(i["id"]), name=str(i.get("name", ""))) for i in items]


@router.get("/meta", response_model=MetaOut, summary="Domains, groups, sources + defaults for the create form")
async def get_meta(keitaro: KeitaroDep, settings: SettingsDep) -> MetaOut:
    lookups = await KeitaroMeta(keitaro, settings).lookups()
    return MetaOut(
        mock_mode=settings.keitaro_mock,
        domains=_named(lookups.domains),
        groups=_named(lookups.groups),
        traffic_sources=_named(lookups.traffic_sources),
        default_domain_id=lookups.default_domain_id,
        default_group_id=lookups.default_group_id,
        default_traffic_source_id=lookups.default_traffic_source_id,
    )


@router.get("/offers", response_model=list[OfferOut], summary="Offer autocomplete (by name or id)")
async def search_offers(
    catalog: CatalogDep,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OfferOut]:
    rows = await catalog.search(q, limit)
    return [OfferOut(id=r.id, name=r.name, state=r.state, country=r.country or []) for r in rows]


@router.post("/offers/sync", response_model=SyncResult, summary="Refresh offer cache from Keitaro")
async def sync_offers(catalog: CatalogDep) -> SyncResult:
    return SyncResult(synced=await catalog.sync())
