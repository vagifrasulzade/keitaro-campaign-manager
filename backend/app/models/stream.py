from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.stream_offer import StreamOffer


class Stream(TimestampMixin, Base):
    """Keitaro stream ("поток" / flow) of a campaign."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32), default="regular")  # regular|forced|default
    schema: Mapped[str] = mapped_column(String(32), default="")  # redirect|landings|action
    action_type: Mapped[str | None] = mapped_column(String(64))
    action_payload: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="active")
    filters: Mapped[list[dict]] = mapped_column(JSON, default=list)

    campaign: Mapped[Campaign] = relationship(back_populates="streams")
    offers: Mapped[list[StreamOffer]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="StreamOffer.id",
        lazy="selectin",
    )

    @property
    def supports_offers(self) -> bool:
        return self.schema == "landings"

    @property
    def is_dirty(self) -> bool:
        return any(o.is_dirty for o in self.offers)
