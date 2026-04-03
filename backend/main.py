import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import models
from database import engine, get_db, Base
from routers import auth as auth_router
from routers import funds as funds_router
from routers import accounts as accounts_router
from routers import categories as categories_router
from routers import transactions as transactions_router
from routers import counterparties as counterparties_router
from routers import cascades as cascades_router
from routers import settings as settings_router
from routers import attachments as attachments_router
from routers import admin as admin_router

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finance")

Base.metadata.create_all(bind=engine)

# Seed глобальных данных
from database import SessionLocal
_seed_db = SessionLocal()
try:
    admin_router.seed_admin_settings(_seed_db)
    admin_router.seed_page_content(_seed_db)
finally:
    _seed_db.close()

app = FastAPI(title="Personal Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.error(
            "Unhandled exception on %s %s\n%s",
            request.method,
            request.url,
            traceback.format_exc(),
        )
        return JSONResponse(status_code=500, content={"detail": traceback.format_exc()})

app.include_router(auth_router.router)
app.include_router(funds_router.router)
app.include_router(accounts_router.router)
app.include_router(categories_router.router)
app.include_router(transactions_router.router)
app.include_router(counterparties_router.router)
app.include_router(cascades_router.router)
app.include_router(settings_router.router)
app.include_router(attachments_router.router)
app.include_router(admin_router.router)


@app.get("/")
def root():
    return {"message": "Personal Finance API"}
