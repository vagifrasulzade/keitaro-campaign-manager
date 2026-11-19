import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.stream import StreamOut

COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    # accepts ["MX","AU"] or "MX, AU RO"
    geo: list[str] = Field(min_length=1)
    offer_id: int = Field(gt=0)
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("geo", mode="before")
    @classmethod
    def split_geo(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [p for p in re.split(r"[\s,;]+", v) if p]
        return v

    @field_validator("geo")
    @classmethod
    def validate_geo(cls, v: list[str]) -> list[str]:
        codes: list[str] = []
        for raw in v:
            code = raw.strip().upper()
            if not COUNTRY_RE.match(code):
                raise ValueError(f"'{raw}' is not an ISO-3166 alpha-2 country code (e.g. AU, MX, RO)")
            if code not in codes:
                codes.append(code)
        if not codes:
            raise ValueError("at least one country is required")
        return codes


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(validation_alias="keitaro_id")
    name: str
    alias: str
    url: str | None
    geo: list[str]
    origin: str
    domain_id: int | None
    group_id: int | None
    traffic_source_id: int | None
    streams: list[StreamOut]

    @classmethod
    def from_model(cls, campaign: Any) -> "CampaignOut":
        out = cls.model_validate(campaign)
        out.streams = [StreamOut.from_model(s) for s in campaign.streams]
        return out


class KeitaroCampaignListItem(BaseModel):
    id: int
    name: str
    alias: str | None = None
    state: str | None = None
    group_id: int | None = None
    is_local: bool = False
