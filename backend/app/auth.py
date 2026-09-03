from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    id: str
    email: str | None = None


def _jwks_url(settings: Settings) -> str:
    if settings.neon_auth_jwks_url:
        return settings.neon_auth_jwks_url
    if settings.neon_auth_url:
        # Confirmed against a real Neon Auth project: the JWKS document is
        # at /.well-known/jwks.json under the same base URL the frontend
        # uses (VITE_NEON_AUTH_URL), not Better Auth's own default /jwks
        # path. Set NEON_AUTH_JWKS_URL directly instead if this ever
        # changes.
        return f"{settings.neon_auth_url.rstrip('/')}/.well-known/jwks.json"
    raise RuntimeError("Neon Auth is not configured.")


_jwk_clients: dict[str, jwt.PyJWKClient] = {}


def _get_jwk_client(settings: Settings) -> jwt.PyJWKClient:
    url = _jwks_url(settings)
    client = _jwk_clients.get(url)
    if client is None:
        client = jwt.PyJWKClient(url)
        _jwk_clients[url] = client
    return client


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if not settings.auth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not set up on the server yet.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        signing_key = _get_jwk_client(settings).get_signing_key_from_jwt(
            credentials.credentials
        )
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            # Neon Auth (Better Auth) signs tokens with EdDSA (Ed25519).
            algorithms=["EdDSA"],
            issuer=settings.neon_auth_issuer,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no subject claim.",
        )

    return AuthenticatedUser(id=user_id, email=payload.get("email"))
