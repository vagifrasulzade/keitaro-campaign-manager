from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CreatorDep, KeitaroDep, SessionDep, SyncDep
from app.models import Campaign
from app.schemas.campaign import CampaignCreate, CampaignOut, KeitaroCampaignListItem

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED,
             summary="Part 1: create campaign (geo → google, rest → offer)")
async def create_campaign(data: CampaignCreate, creator: CreatorDep) -> CampaignOut:
    return CampaignOut.from_model(await creator.create(data))


@router.get("", response_model=list[KeitaroCampaignListItem], summary="Campaigns in Keitaro (editor picker)")
async def list_campaigns(
    keitaro: KeitaroDep,
    session: SessionDep,
    q: str = Query(default="", max_length=200),
) -> list[KeitaroCampaignListItem]:
    remote = await keitaro.list_campaigns()
    local_ids = set((await session.scalars(select(Campaign.keitaro_id))).all())
    needle = q.strip().lower()
    items = [
        KeitaroCampaignListItem(
            id=int(c["id"]),
            name=c.get("name") or "",
            alias=c.get("alias"),
            state=c.get("state"),
            group_id=c.get("group_id"),
            is_local=int(c["id"]) in local_ids,
        )
        for c in remote
        if not needle or needle in (c.get("name") or "").lower() or needle == str(c["id"])
    ]
    return sorted(items, key=lambda c: c.id, reverse=True)


@router.get("/{campaign_id}", response_model=CampaignOut, summary="Campaign with streams (imports on first open)")
async def get_campaign(campaign_id: int, sync: SyncDep) -> CampaignOut:
    return CampaignOut.from_model(await sync.get_or_import(campaign_id))


@router.post("/{campaign_id}/sync", response_model=CampaignOut,
             summary="Fetch streams from Keitaro (discards unpublished drafts)")
async def sync_campaign(campaign_id: int, sync: SyncDep) -> CampaignOut:
    return CampaignOut.from_model(await sync.sync(campaign_id))
