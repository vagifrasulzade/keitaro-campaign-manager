"""Part 2 — offer editor for a stream (staging → push to Keitaro).

All edits change only the local draft. Nothing goes to Keitaro until `push`.
`cancel` returns the draft to what was last published.
"""

import asyncio
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.integrations.keitaro import payloads
from app.integrations.keitaro.base import KeitaroClientProtocol
from app.models import OfferStatus, Stream, StreamOffer
from app.services.offer_catalog import OfferCatalog
from app.services.share_allocator import AllocationError, Slot, allocate

ACTIVE = OfferStatus.ACTIVE.value
REMOVED = OfferStatus.REMOVED.value

# one push at a time per stream (single-process deployment)
_push_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def rebalance(stream: Stream) -> None:
    """Recalculate shares of active offers. Raises AllocationError."""
    active = [o for o in stream.offers if o.is_active]
    shares = allocate([Slot(key=id(o), pinned_share=o.share if o.is_pinned else None) for o in active])
    for offer in active:
        offer.share = shares[id(offer)]
    for offer in stream.offers:
        if not offer.is_active:
            offer.share = 0
            offer.is_pinned = False


class StreamEditor:
    def __init__(self, session: AsyncSession, keitaro: KeitaroClientProtocol, catalog: OfferCatalog):
        self.session = session
        self.keitaro = keitaro
        self.catalog = catalog

    # --- helpers -------------------------------------------------------------
    async def get_stream(self, keitaro_stream_id: int) -> Stream:
        stream = await self.session.scalar(select(Stream).where(Stream.keitaro_id == keitaro_stream_id))
        if stream is None:
            raise NotFoundError(f"Stream {keitaro_stream_id} is not loaded — open its campaign first")
        return stream

    async def _editable_stream(self, keitaro_stream_id: int) -> Stream:
        stream = await self.get_stream(keitaro_stream_id)
        if not stream.supports_offers:
            raise ValidationError(f"Stream '{stream.name}' has schema '{stream.schema}' — it has no offers")
        return stream

    @staticmethod
    def _find(stream: Stream, offer_id: int) -> StreamOffer:
        for offer in stream.offers:
            if offer.offer_id == offer_id:
                return offer
        raise NotFoundError(f"Offer {offer_id} is not in stream {stream.keitaro_id}")

    async def _commit_or_rollback(self, stream: Stream) -> Stream:
        try:
            rebalance(stream)
        except AllocationError as exc:
            await self.session.rollback()
            raise ValidationError(str(exc)) from exc
        await self.session.commit()
        return stream

    # --- operations ----------------------------------------------------------
    async def add_offer(self, keitaro_stream_id: int, offer_id: int) -> Stream:
        stream = await self._editable_stream(keitaro_stream_id)
        existing = next((o for o in stream.offers if o.offer_id == offer_id), None)
        if existing is not None:
            if existing.is_active:
                raise ConflictError(f"Offer {offer_id} is already in this stream")
            return await self.restore_offer(keitaro_stream_id, offer_id)

        offer = await self.catalog.get(offer_id)
        stream.offers.append(
            StreamOffer(offer_id=offer.id, offer_name=offer.name, share=0, status=ACTIVE, is_pinned=False)
        )
        return await self._commit_or_rollback(stream)

    async def remove_offer(self, keitaro_stream_id: int, offer_id: int) -> Stream:
        stream = await self._editable_stream(keitaro_stream_id)
        offer = self._find(stream, offer_id)
        if not offer.is_active:
            raise ConflictError(f"Offer {offer_id} is already removed")

        if offer.is_published:
            offer.status, offer.share, offer.is_pinned = REMOVED, 0, False
        else:  # local draft that never reached Keitaro → just drop it
            stream.offers.remove(offer)

        try:
            rebalance(stream)
        except AllocationError:
            # the rest were all pinned and no longer add up to 100 → release pins
            for o in stream.offers:
                o.is_pinned = False
        return await self._commit_or_rollback(stream)

    async def restore_offer(self, keitaro_stream_id: int, offer_id: int) -> Stream:
        stream = await self._editable_stream(keitaro_stream_id)
        offer = self._find(stream, offer_id)
        if offer.is_active:
            raise ConflictError(f"Offer {offer_id} is already active")
        offer.status, offer.is_pinned = ACTIVE, False
        return await self._commit_or_rollback(stream)

    async def set_share(self, keitaro_stream_id: int, offer_id: int, share: int | None) -> Stream:
        """share=int → pin the offer with this share; share=None → unpin."""
        stream = await self._editable_stream(keitaro_stream_id)
        offer = self._find(stream, offer_id)
        if not offer.is_active:
            raise ValidationError("Bring the offer back before changing its share")
        if share is None:
            offer.is_pinned = False
        else:
            offer.is_pinned, offer.share = True, share
        return await self._commit_or_rollback(stream)

    async def cancel(self, keitaro_stream_id: int) -> Stream:
        stream = await self._editable_stream(keitaro_stream_id)
        for offer in list(stream.offers):
            if not offer.is_published:
                stream.offers.remove(offer)
                continue
            offer.share = offer.published_share or 0
            offer.status = offer.published_status or ACTIVE
            offer.is_pinned = False
        await self.session.commit()
        return stream

    async def push(self, keitaro_stream_id: int) -> Stream:
        async with _push_locks[keitaro_stream_id]:
            stream = await self._editable_stream(keitaro_stream_id)
            active = [o for o in stream.offers if o.is_active]
            if not active:
                raise ValidationError("A stream must have at least one active offer")
            total = sum(o.share for o in active)
            if total != 100 or any(o.share < 1 for o in active):
                raise ValidationError(f"Active shares must be ≥1% and sum to 100% (now {total}%)")
            if not stream.is_dirty:
                return stream

            await self.keitaro.update_stream(
                stream.keitaro_id,
                {"offers": [payloads.offer_item(o.offer_id, o.share) for o in active]},
            )
            for offer in stream.offers:
                offer.published_share = offer.share
                offer.published_status = offer.status
            await self.session.commit()
            return stream
