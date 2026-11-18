from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # .../backend
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Adrobot · Keitaro campaign tool"
    debug: bool = False

    # --- Database -----------------------------------------------------------
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'adrobot.db'}"

    # --- Keitaro ------------------------------------------------------------
    keitaro_url: str = "https://example.com"  # tracker URL, without /admin_api/v1
    keitaro_api_key: str = ""
    keitaro_timeout: float = 20.0
    # true → in-memory fake tracker (demo / local development without a key)
    keitaro_mock: bool = False

    # --- Campaign creator defaults ------------------------------------------
    # Names (not ids) so the same .env works on any tracker; resolved via API.
    # If a name is not found and the tracker has exactly one item, that item is used.
    default_domain: str = "kylovoa.com"
    default_group: str = "FORTESTS"
    default_traffic_source: str = "FORTESTS"
    geo_redirect_url: str = "https://google.com"

    # --- Offer catalog cache -------------------------------------------------
    offers_cache_ttl_seconds: int = Field(default=600, ge=0)

    # --- Frontend ------------------------------------------------------------
    # React build output (`npm run build` in frontend/); served at "/" if present
    frontend_dir: Path = PROJECT_DIR / "frontend" / "dist"

    @property
    def keitaro_api_base(self) -> str:
        return self.keitaro_url.rstrip("/") + "/admin_api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
