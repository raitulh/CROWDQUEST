import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.redis import get_redis
from app.core.security import decrypt_secret, encrypt_secret, issue_access_token, new_opaque_token
from app.integrations.twitch.client import TwitchAPIError, TwitchClient
from app.models.entities import TwitchConnection, User
from app.services.events import publish_connection_update

router = APIRouter(prefix="/auth", tags=["authentication"])


class LocalLoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    display_name: str | None = None


@router.post("/local/login")
async def local_login(
    payload: LocalLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    clean_login = payload.username.strip().lower()
    clean_display = (payload.display_name or payload.username).strip()
    if not clean_login:
        raise HTTPException(status_code=400, detail="Username is required")

    user = await db.scalar(select(User).where(User.login == clean_login))
    if user is None:
        user = User(
            twitch_user_id=f"local_{clean_login[:25]}",
            login=clean_login,
            display_name=clean_display,
        )
        db.add(user)
        await db.flush()
    else:
        user.display_name = clean_display

    connection = await db.scalar(select(TwitchConnection).where(TwitchConnection.user_id == user.id))
    if connection is None:
        connection = TwitchConnection(
            user_id=user.id,
            access_token_ciphertext=encrypt_secret("local-dev-token"),
            refresh_token_ciphertext=encrypt_secret("local-dev-refresh"),
            scopes=["user:read:chat", "user:write:chat"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            status="connected",
        )
        db.add(connection)
    else:
        connection.status = "connected"
    await db.commit()

    redis = get_redis()
    session_token, session_id = issue_access_token(user.id)
    await redis.set(
        f"{settings.redis_prefix}:app-session:{session_id}",
        user.id,
        ex=settings.access_token_ttl_minutes * 60,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_ttl_minutes * 60,
        domain=settings.cookie_domain,
        path="/",
    )
    await publish_connection_update(user.id)
    return {
        "success": True,
        "user": {
            "id": user.id,
            "login": user.login,
            "display_name": user.display_name,
        },
    }


@router.get("/twitch/login")
async def twitch_login() -> RedirectResponse:
    if not settings.twitch_client_id or not settings.twitch_client_secret:
        raise HTTPException(status_code=503, detail="Twitch OAuth is not configured on this deployment")
    state = new_opaque_token()
    await get_redis().set(
        f"{settings.redis_prefix}:oauth:state:{state}", "valid",
        ex=settings.oauth_state_ttl_seconds,
    )
    params = {
        "client_id": settings.twitch_client_id,
        "redirect_uri": settings.twitch_redirect_uri,
        "response_type": "code",
        "scope": " ".join(settings.twitch_scopes),
        "state": state,
        "force_verify": "true",
    }
    response = RedirectResponse(f"{settings.twitch_oauth_base_url}/authorize?{urlencode(params)}")
    response.set_cookie(
        key="cq_oauth_state", value=state, httponly=True, secure=settings.cookie_secure,
        samesite="lax", max_age=settings.oauth_state_ttl_seconds, path="/api/v1/auth/twitch/callback",
    )
    return response


@router.get("/twitch/callback")
async def twitch_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state_cookie: str | None = Cookie(default=None, alias="cq_oauth_state"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if error:
        response = RedirectResponse(f"{settings.frontend_url}/login?error=twitch_authorization_denied")
        response.delete_cookie("cq_oauth_state", path="/api/v1/auth/twitch/callback")
        return response
    if not code or not state:
        raise HTTPException(status_code=400, detail="OAuth code and state are required")
    if not oauth_state_cookie or not secrets.compare_digest(oauth_state_cookie, state):
        raise HTTPException(status_code=400, detail="OAuth browser state validation failed")
    redis = get_redis()
    state_key = f"{settings.redis_prefix}:oauth:state:{state}"
    stored_state = await redis.getdel(state_key)
    if stored_state != "valid":
        raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")

    twitch = TwitchClient()
    try:
        token_data = await twitch.oauth_exchange(code)
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        scopes = token_data.get("scope", [])
        if "user:read:chat" not in scopes:
            raise HTTPException(status_code=403, detail="Twitch authorization did not include user:read:chat")
        twitch.access_token = access_token
        twitch_user = await twitch.get_current_user()
    except TwitchAPIError as exc:
        raise HTTPException(status_code=502, detail="Twitch authorization could not be completed") from exc
    finally:
        await twitch.close()

    user = await db.scalar(select(User).where(User.twitch_user_id == str(twitch_user["id"])))
    if user is None:
        user = User(
            twitch_user_id=str(twitch_user["id"]),
            login=twitch_user["login"],
            display_name=twitch_user["display_name"],
            profile_image_url=twitch_user.get("profile_image_url"),
        )
        db.add(user)
        await db.flush()
    else:
        user.login = twitch_user["login"]
        user.display_name = twitch_user["display_name"]
        user.profile_image_url = twitch_user.get("profile_image_url")

    connection = await db.scalar(select(TwitchConnection).where(TwitchConnection.user_id == user.id))
    encrypted_access = encrypt_secret(access_token)
    encrypted_refresh = encrypt_secret(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(token_data["expires_in"]))
    if connection is None:
        connection = TwitchConnection(
            user_id=user.id,
            access_token_ciphertext=encrypted_access,
            refresh_token_ciphertext=encrypted_refresh,
            scopes=scopes,
            expires_at=expires_at,
            status="connected",
        )
        db.add(connection)
    else:
        connection.access_token_ciphertext = encrypted_access
        connection.refresh_token_ciphertext = encrypted_refresh
        connection.scopes = scopes
        connection.expires_at = expires_at
        connection.status = "connected"
    await db.commit()

    session_token, session_id = issue_access_token(user.id)
    await redis.set(f"{settings.redis_prefix}:app-session:{session_id}", user.id, ex=settings.access_token_ttl_minutes * 60)
    response = RedirectResponse(f"{settings.frontend_url}/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("cq_oauth_state", path="/api/v1/auth/twitch/callback")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_ttl_minutes * 60,
        domain=settings.cookie_domain,
        path="/",
    )
    await publish_connection_update(user.id)
    return response


@router.post("/twitch/disconnect", status_code=204)
async def disconnect_twitch(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> Response:
    connection = await db.scalar(select(TwitchConnection).where(TwitchConnection.user_id == user.id))
    if connection:
        try:
            twitch = TwitchClient(decrypt_secret(connection.access_token_ciphertext))
            try:
                await twitch.revoke_token()
            finally:
                await twitch.close()
        except (TwitchAPIError, ValueError):
            # Disconnect locally even when the external revoke endpoint is unavailable.
            pass
        connection.status = "disconnected"
        await db.commit()
        await publish_connection_update(user.id)
    return Response(status_code=204)


@router.get("/status")
async def auth_status(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    connection = await db.scalar(select(TwitchConnection).where(TwitchConnection.user_id == user.id))
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "twitch_user_id": user.twitch_user_id,
            "login": user.login,
            "display_name": user.display_name,
            "profile_image_url": user.profile_image_url,
        },
        "twitch": {
            "connected": bool(connection and connection.status == "connected"),
            "status": connection.status if connection else "disconnected",
            "scopes": connection.scopes if connection else [],
        },
    }


@router.post("/logout", status_code=204)
async def logout(response: Response, user: CurrentUser, token: str | None = Cookie(default=None, alias=settings.session_cookie_name)) -> Response:
    from app.core.security import decode_access_token
    payload = decode_access_token(token) if token else None
    if payload and payload.get("jti"):
        await get_redis().delete(f"{settings.redis_prefix}:app-session:{payload['jti']}")
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.cookie_domain,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response
