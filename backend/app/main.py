import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import SessionLocal
from app.errors import AppError
from app.limits import limiter
from app.routers.api import router
from app.services.common import ensure_admin
from app.storage import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vcontent")
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_admin(db)
    finally:
        db.close()
    try:
        get_storage().ensure_bucket()
    except Exception:
        logger.warning("Storage ainda não está acessível. Uploads falham até o MinIO subir.")
    yield


app = FastAPI(title="VContent API", version=settings.app_version, lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method in UNSAFE and request.url.path.startswith("/api"):
        if request.headers.get("x-requested-with") != "vcontent":
            return JSONResponse({"detail": "Requisição recusada."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN" if request.url.path.endswith("/contract/file") else "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    errors = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", []) if part not in {"body", "query"})
        message = item.get("msg", "valor inválido")
        errors.append(f"{loc}: {message}" if loc else message)
    return JSONResponse(status_code=422, content={"detail": "Verifique os campos informados.", "errors": errors})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_request: Request, _exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Muitas tentativas. Aguarde um momento e tente de novo."})
