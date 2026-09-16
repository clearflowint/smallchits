"""
Day 1 Google OAuth 2.0 authentication layer (Blueprint section 3).

- Every operational endpoint depends on `get_current_manager`, which resolves
  the authenticated Manager_ID (user_email) from a signed session cookie.
- Manager_ID is PERMANENTLY bound to the authenticated Google email on first
  login and never changes.
- Complete Logout Protocol purges the session cookie and revokes state.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

JWT_ALGORITHM = "HS256"


def create_session_token(user_email: str, manager_name: Optional[str] = None) -> str:
    """Creates a signed session token binding this browser session to Manager_ID."""
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    payload = {
        "sub": user_email,  # Manager_ID — permanent tenant anchor
        "name": manager_name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
        ) from exc


async def get_current_manager(
    clearflow_session: Optional[str] = Cookie(default=None, alias="clearflow_session"),
) -> str:
    """
    FastAPI dependency: resolves the authenticated Manager_ID (email).

    This is the Authentication Guardrail from Blueprint section 3 — any router
    that depends on this is unreachable without a valid Google-authenticated
    session, and every NocoDB query downstream MUST filter by this Manager_ID.
    """
    if not clearflow_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Redirect to Google Sign-In.",
        )
    payload = decode_session_token(clearflow_session)
    manager_id: Optional[str] = payload.get("sub")
    if not manager_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session payload.")
    return manager_id
