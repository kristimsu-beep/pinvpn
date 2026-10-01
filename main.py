import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient


# ============================================================
# PINVPN
# Backend
# ============================================================

app = FastAPI(
    title="PinVPN API",
    version="1.0.0"
)


# ============================================================
# DIRECTORIES
# ============================================================

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ============================================================
# MONGODB
# ============================================================

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "pinvpn")

mongo_client = None
db = None


@app.on_event("startup")
async def startup():

    global mongo_client
    global db

    if not MONGODB_URI:
        print("[PINVPN] MONGODB_URI is not configured.")
        return

    try:

        mongo_client = AsyncIOMotorClient(
            MONGODB_URI
        )

        db = mongo_client[MONGODB_DATABASE]

        await mongo_client.admin.command(
            "ping"
        )

        print(
            f"[PINVPN] MongoDB connected: "
            f"{MONGODB_DATABASE}"
        )

    except Exception as e:

        print(
            f"[PINVPN] MongoDB connection error: {e}"
        )


@app.on_event("shutdown")
async def shutdown():

    global mongo_client

    if mongo_client:

        mongo_client.close()

        print("[PINVPN] MongoDB connection closed.")


# ============================================================
# FRONTEND
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    if db is None:

        return {
            "status": "ok",
            "service": "PinVPN",
            "database": "not_connected"
        }

    try:

        await mongo_client.admin.command("ping")

        return {
            "status": "ok",
            "service": "PinVPN",
            "database": "connected",
            "database_name": MONGODB_DATABASE
        }

    except Exception as e:

        return {
            "status": "error",
            "service": "PinVPN",
            "database": "error",
            "error": str(e)
        }


# ============================================================
# BASIC API INFORMATION
# ============================================================

@app.get("/api")
async def api_info():

    return {
        "name": "PinVPN API",
        "version": "1.0.0",
        "status": "online",
        "time": datetime.now(
            timezone.utc
        ).isoformat()
    }
