"""
Google OAuth 2.0 authentication routes (Blueprint section 3, Day 1 mandate).
"""
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.security import create_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/google/login")
async def google_login():
    """Redirects unauthenticated users to the ClearFlow Google Sign-In screen."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": f"openid email profile {settings.GOOGLE_DRIVE_SCOPE}",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str, response: Response):
    """
    Exchanges the OAuth code, resolves the user's email, and PERMANENTLY binds
    Manager_ID to that email (Blueprint: 'Permanent Tenant Binding').
    """
    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google token exchange failed")
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code >= 400:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Failed to fetch Google user info")
        userinfo = userinfo_resp.json()

    user_email = userinfo["email"]  # Manager_ID — permanent tenant anchor
    manager_name = userinfo.get("name", user_email)

    session_token = create_session_token(user_email, manager_name)

    redirect = RedirectResponse(url=settings.FRONTEND_URL)
    redirect.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.ENV == "production",
        samesite="lax",
    )
    # NOTE: tokens["refresh_token"] should be persisted (e.g. in Managers table,
    # encrypted) if you need offline Google Drive access beyond this session.
    return redirect


@router.post("/logout")
async def logout(response: Response):
    """
    Complete Logout Protocol (Blueprint section 3):
    purges session state and returns the app to the Google Sign-In landing page.
    """
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"status": "logged_out", "redirect": settings.FRONTEND_URL}
