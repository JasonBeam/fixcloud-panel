import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.settings import get_settings
from app.services.browser_session import (
    COOKIE_NAME,
    bind,
    cleanup_loop,
    new_token,
    scope_for_token,
    session_directory,
    touch,
    unbind,
    valid_token,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(cleanup_loop(settings.app_data_dir, stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(
    title="FixCloud Panel",
    docs_url="/api/docs" if settings.app_env == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    override = request.app.dependency_overrides.get(get_settings)
    request_settings = override() if override else get_settings()
    token = request.cookies.get(COOKIE_NAME)
    created = not valid_token(token)
    if created:
        token = new_token()
    assert token is not None
    directory = session_directory(request_settings.app_data_dir, token)
    await asyncio.to_thread(touch, directory)
    context_tokens = bind(scope_for_token(token), directory)
    try:
        response = await call_next(request)
    finally:
        unbind(context_tokens)
    if created:
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: https: http:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.method in {"GET", "HEAD"}:
        # Always revalidate the app shell and built assets so a NAS container
        # update cannot leave Safari running an older editor bundle.
        response.headers["Cache-Control"] = "no-cache"
    return response


frontend_dist = Path(settings.frontend_dist)
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
