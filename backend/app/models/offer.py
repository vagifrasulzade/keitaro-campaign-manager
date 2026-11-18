from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OfferCache(Base):
    """Local copy of Keitaro offers → fast autocomplete without hitting the tracker."""

    __tablename__ = "offers_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # Keitaro id
    name: Mapped[str] = mapped_column(String(512), index=True)
    state: Mapped[str] = mapped_column(String(16), default="active")
    country: Mapped[list[str]] = mapped_column(JSON, default=list)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
