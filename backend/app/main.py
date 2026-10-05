from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.db import get_session_factory, init_db
from app.infrastructure.seed import seed_if_empty

settings = get_settings()
configure_logging(settings.app_debug)
log = get_logger("nexus.api")

REQS = Counter("nexus_http_requests_total", "HTTP requests", ["method", "path", "status"])
LAT = Histogram("nexus_http_request_duration_seconds", "Request latency", ["method", "path"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.app_env)
    init_db()
    if settings.seed_on_startup:
        db = get_session_factory()()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield
    log.info("shutdown")


app = FastAPI(
    title="NEXUS Intelligence API",
    description="Lawful OSINT / data-intelligence platform. Original data is immutable; search is a projection.",
    version=__version__,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_mw(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    path = request.url.path
    # avoid high-cardinality
    if path.startswith("/api/"):
        LAT.labels(request.method, path.split("?")[0][:80]).observe(perf_counter() - start)
        REQS.labels(request.method, path.split("?")[0][:80], str(response.status_code)).inc()
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": "nexus-api", "version": __version__}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/dashboard")
def dashboard():
    from sqlalchemy import func

    from app.domain.models import AuditLog, Collection, Dataset, Entity, ImportJob, Investigation, Record, Relationship

    db = get_session_factory()()
    try:
        by_cat = dict(
            db.query(Dataset.category, func.count(Dataset.id)).group_by(Dataset.category).all()
        )
        by_type = dict(
            db.query(Entity.entity_type, func.count(Entity.id)).group_by(Entity.entity_type).all()
        )
        recent_audit = (
            db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(8).all()
        )
        jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(5).all()
        return {
            "kpis": {
                "collections": db.query(func.count(Collection.id)).filter(Collection.status != "deleted").scalar() or 0,
                "datasets": db.query(func.count(Dataset.id)).scalar() or 0,
                "records": db.query(func.count(Record.id)).scalar() or 0,
                "entities": db.query(func.count(Entity.id)).scalar() or 0,
                "relationships": db.query(func.count(Relationship.id)).scalar() or 0,
                "investigations": db.query(func.count(Investigation.id)).scalar() or 0,
            },
            "datasets_by_category": by_cat,
            "entities_by_type": by_type,
            "jobs": [
                {
                    "id": str(j.id),
                    "filename": j.filename,
                    "status": j.status,
                    "records_processed": j.records_processed,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in jobs
            ],
            "audit": [
                {
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in recent_audit
            ],
            "collections": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "slug": c.slug,
                    "record_count": c.record_count,
                    "dataset_count": c.dataset_count,
                    "status": c.status,
                }
                for c in db.query(Collection).filter(Collection.status != "deleted").order_by(Collection.name).all()
            ],
            "scale_note": "Phase 1 metadata+bounded records in PostgreSQL. Target architecture supports 10B+ via object store, ClickHouse, OpenSearch. Collections are the partitioning dimension.",
        }
    finally:
        db.close()
