from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import KeitaroError
from app.db.session import get_session
from app.integrations.keitaro.base import KeitaroClientProtocol
from app.services.campaign_creator import CampaignCreator
from app.services.campaign_sync import CampaignSync
from app.services.offer_catalog import OfferCatalog
from app.services.stream_editor import StreamEditor

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_keitaro(request: Request) -> KeitaroClientProtocol:
    client = getattr(request.app.state, "keitaro", None)
    if client is None:
        raise KeitaroError(
            getattr(request.app.state, "keitaro_error", None) or "Keitaro client is not configured"
        )
    return client


KeitaroDep = Annotated[KeitaroClientProtocol, Depends(get_keitaro)]


def get_catalog(session: SessionDep, keitaro: KeitaroDep, settings: SettingsDep) -> OfferCatalog:
    return OfferCatalog(session, keitaro, settings.offers_cache_ttl_seconds)


CatalogDep = Annotated[OfferCatalog, Depends(get_catalog)]


def get_creator(
    session: SessionDep, keitaro: KeitaroDep, catalog: CatalogDep, settings: SettingsDep
) -> CampaignCreator:
    return CampaignCreator(session, keitaro, catalog, settings)


def get_sync(session: SessionDep, keitaro: KeitaroDep, catalog: CatalogDep) -> CampaignSync:
    return CampaignSync(session, keitaro, catalog)


def get_editor(session: SessionDep, keitaro: KeitaroDep, catalog: CatalogDep) -> StreamEditor:
    return StreamEditor(session, keitaro, catalog)


CreatorDep = Annotated[CampaignCreator, Depends(get_creator)]
SyncDep = Annotated[CampaignSync, Depends(get_sync)]
EditorDep = Annotated[StreamEditor, Depends(get_editor)]
