from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.stream import Stream


class OfferStatus(str, enum.Enum):
    ACTIVE = "active"
    REMOVED = "removed"


class StreamOffer(TimestampMixin, Base):
    """An offer inside a stream — the editor's staging row.

    `share` / `status` / `is_pinned` is the local *draft*.
    `published_share` / `published_status` is what Keitaro currently has
    (None → the offer was added locally and was never pushed).
    """

    __tablename__ = "stream_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id", name="uq_stream_offers_stream_offer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), index=True)
    offer_id: Mapped[int] = mapped_column(Integer)  # Keitaro offer id
    offer_name: Mapped[str] = mapped_column(String(512), default="")

    share: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default=OfferStatus.ACTIVE.value)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    published_share: Mapped[int | None] = mapped_column(Integer)
    published_status: Mapped[str | None] = mapped_column(String(16))

    stream: Mapped[Stream] = relationship(back_populates="offers")

    @property
    def is_active(self) -> bool:
        return self.status == OfferStatus.ACTIVE.value

    @property
    def is_published(self) -> bool:
        return self.published_status is not None

    @property
    def is_dirty(self) -> bool:
        if not self.is_published:
            return True
        return self.share != self.published_share or self.status != self.published_status
