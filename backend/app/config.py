from functools import lru_cache

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings parses .env into this module's own Settings fields, but
# never touches os.environ itself. LLM integrations that read the
# environment directly (for API keys, model flags, etc.) would never see .env
# values without this. This module is imported by nearly everything in the
# app, so loading here means it happens exactly once, before anything needs
# it.
load_dotenv()


class Settings(BaseSettings):
    # extra="ignore": .env is shared with tools/libraries that read straight
    # from the process environment (LLM clients included). Settings only needs
    # to declare the fields it uses; it shouldn't crash the app over keys
    # meant for something else.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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
