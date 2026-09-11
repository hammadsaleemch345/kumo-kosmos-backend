from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import (
    admin_import,
    admin_stories,
    admin_subscribers,
    auth,
    ccbill_webhooks,
    me,
    pages,
    stories,
    uploads,
)

app = FastAPI(title="Silk & Sin Backend")

# Wide open for local dev against the prototype file (opened directly from disk, so its origin
# is "null") and localhost dev servers. Tighten this to the real production domain before launch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(admin_stories.router)
app.include_router(admin_subscribers.router)
app.include_router(ccbill_webhooks.router)
app.include_router(stories.router)
app.include_router(me.router)
app.include_router(pages.public_router)
app.include_router(pages.admin_router)
app.include_router(admin_import.router)

Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
