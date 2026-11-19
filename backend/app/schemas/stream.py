from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import Stream


class StreamOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: int
    offer_name: str
    share: int
    status: str
    is_pinned: bool
    published_share: int | None
    published_status: str | None
    is_published: bool
    is_dirty: bool


class StreamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(validation_alias="keitaro_id")
    name: str
    position: int
    type: str
    schema_: str = Field(validation_alias="schema", serialization_alias="schema")
    action_type: str | None
    action_payload: str | None
    state: str
    filters: list[dict[str, Any]]
    supports_offers: bool
    is_dirty: bool
    offers: list[StreamOfferOut]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_share(self) -> int:
        return sum(o.share for o in self.offers if o.status == "active")

    @classmethod
    def from_model(cls, stream: Stream) -> "StreamOut":
        out = cls.model_validate(stream)
        # active first, then removed (archived) offers
        out.offers.sort(key=lambda o: (o.status != "active",))
        return out


class AddOfferIn(BaseModel):
    offer_id: int = Field(gt=0)


class SetShareIn(BaseModel):
    # integer → pin offer with this share; null → unpin (share is auto-calculated)
    share: int | None = Field(default=None, ge=1, le=100)
