from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"

    database_url: str = "sqlite:///./dev.db"

    cors_origins: list[str] = ["http://localhost:5173"]

    # Neon Auth (Better Auth) settings. These stay unset until Neon Auth is
    # enabled on the Neon project. See app/auth.py for how they're used.
    # neon_auth_url matches the frontend's VITE_NEON_AUTH_URL, e.g.
    # https://your-project.neon.tech/auth
    neon_auth_url: str | None = None
    neon_auth_jwks_url: str | None = None
    neon_auth_issuer: str | None = None

    @property
    def auth_configured(self) -> bool:
        return bool(self.neon_auth_url or self.neon_auth_jwks_url)

    @field_validator(
        "neon_auth_url", "neon_auth_jwks_url", "neon_auth_issuer", mode="before"
    )
    @classmethod
    def _blank_env_as_none(cls, value: object) -> object:
        # A var present in .env but left blank (NEON_AUTH_ISSUER=) parses as
        # "", not None. That silently breaks the "unset means skip this
        # check" contract these fields rely on, so treat blank as unset.
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
