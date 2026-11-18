from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.stream import Stream


class Campaign(TimestampMixin, Base):
    """Local mirror of a Keitaro campaign (created by us or imported for editing)."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(512))
    # ISO-3166 alpha-2 codes used in the geo → google stream (only for campaigns we created)
    geo: Mapped[list[str]] = mapped_column(JSON, default=list)
    domain_id: Mapped[int | None] = mapped_column(Integer)
    group_id: Mapped[int | None] = mapped_column(Integer)
    traffic_source_id: Mapped[int | None] = mapped_column(Integer)
    # "creator" — made by this tool, "import" — pulled from Keitaro for editing
    origin: Mapped[str] = mapped_column(String(16), default="creator")

    streams: Mapped[list[Stream]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Stream.position",
        lazy="selectin",
    )
