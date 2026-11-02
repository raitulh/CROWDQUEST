import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from redis.exceptions import RedisError

from app.api.v1 import analytics, auth, community, health, overlay, sessions, settings as settings_router
from app.core.config import settings
from app.core.database import dispose_database
from app.core.redis import close_redis, connect_redis, get_redis

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("crowdquest.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_redis()
    logger.info("CrowdQuest API started in %s mode", settings.app_env)
    yield
    await close_redis()
    await dispose_database()


app = FastAPI(
    title="CrowdQuest API",
    description="Production API for Twitch-connected collaborative quest sessions.",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url="/api/redoc" if settings.app_env != "production" else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("Origin")
        allowed_origins = set(settings.cors_origins) | {settings.frontend_url}
        if origin and origin not in allowed_origins:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Request origin is not allowed", "request_id": request_id}, status_code=403)
    if request.url.path not in {"/health/live", "/health/ready"}:
        ip = request.client.host if request.client else "unknown"
        bucket = int(time.time() // 60)
        key = f"{settings.redis_prefix}:ratelimit:{ip}:{bucket}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 70)
            if count > 180:
                from fastapi.responses import JSONResponse
                response = JSONResponse({"detail": "Rate limit exceeded", "request_id": request_id}, status_code=429)
                response.headers["Retry-After"] = "60"
                return response
        except RedisError:
            logger.exception("Redis rate limiter unavailable")
            if settings.app_env == "production":
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Temporarily unavailable"}, status_code=503)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    sensitive_path = request.url.path.startswith("/api/v1/public/overlays/")
    if request.url.path.startswith("/api/v1/auth") or sensitive_path:
        response.headers["Cache-Control"] = "no-store"
    if sensitive_path:
        response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    log_path = "/api/v1/public/overlays/[TOKEN REDACTED]" if sensitive_path else request.url.path
    logger.info("%s %s %s %.2fms", request.method, log_path, response.status_code, (time.perf_counter() - start) * 1000)
    return response



app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(community.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(overlay.router, prefix="/api/v1")
