import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import (
    FastAPI,
    Request,
    Form
)

from fastapi.responses import (
    HTMLResponse,
    JSONResponse
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from motor.motor_asyncio import AsyncIOMotorClient

import bcrypt


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

templates = Jinja2Templates(
    directory="templates"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ============================================================
# PASSWORD HASHING
# ============================================================




# ============================================================
# MONGODB
# ============================================================

MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "pinvpn"
)

mongo_client = None
db = None


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():

    global mongo_client
    global db

    if not MONGODB_URI:

        print(
            "[PINVPN] MONGODB_URI is not configured."
        )

        return

    try:

        mongo_client = AsyncIOMotorClient(
            MONGODB_URI
        )

        db = mongo_client[
            MONGODB_DATABASE
        ]

        await mongo_client.admin.command(
            "ping"
        )

        # Create indexes

        await db.users.create_index(
            "username_lower",
            unique=True
        )

        await db.sessions.create_index(
            "expires_at",
            expireAfterSeconds=0
        )

        print(
            f"[PINVPN] MongoDB connected: "
            f"{MONGODB_DATABASE}"
        )

    except Exception as e:

        print(
            f"[PINVPN] MongoDB connection error: {e}"
        )


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def shutdown():

    global mongo_client

    if mongo_client:

        mongo_client.close()

        print(
            "[PINVPN] MongoDB connection closed."
        )


# ============================================================
# FRONTEND
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
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

        await mongo_client.admin.command(
            "ping"
        )

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
# API INFORMATION
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


# ============================================================
# CREATE USER
# ============================================================

@app.post("/api/auth/register")
async def register(
    username: str = Form(...),
    password: str = Form(...)
):

    if db is None:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "Database is not connected."
            }
        )


    username = username.strip()


    # Username validation

    if len(username) < 3:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Username must contain at least 3 characters."
            }
        )


    if len(username) > 30:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Username is too long."
            }
        )


    # Password validation

    if len(password) < 8:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Password must contain at least 8 characters."
            }
        )


    username_lower = username.lower()


    # Check existing username

    existing_user = await db.users.find_one(
        {
            "username_lower":
            username_lower
        }
    )


    if existing_user:

        return JSONResponse(
            status_code=409,
            content={
                "detail":
                "This username is already registered."
            }
        )


    # Hash password

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


    now = datetime.now(
        timezone.utc
    )


    user = {

        "username":
        username,

        "username_lower":
        username_lower,

        "password_hash":
        password_hash,

        "created_at":
        now,

        "active":
        True
    }


    result = await db.users.insert_one(
        user
    )


    return {
        "status": "ok",
        "message":
        "Account created successfully.",
        "user": {
            "id":
            str(result.inserted_id),

            "username":
            username,

            "created_at":
            now.isoformat()
        }
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    if db is None:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "Database is not connected."
            }
        )


    username_lower = username.strip().lower()


    user = await db.users.find_one(
        {
            "username_lower":
            username_lower
        }
    )


    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Invalid username or password."
            }
        )


    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    ):

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Invalid username or password."
            }
        )


    if not user.get(
        "active",
        True
    ):

        return JSONResponse(
            status_code=403,
            content={
                "detail":
                "This account is disabled."
            }
        )


    # Create session

    session_token = secrets.token_urlsafe(
        48
    )


    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=30)
    )


    await db.sessions.insert_one(
        {
            "token":
            session_token,

            "user_id":
            user["_id"],

            "created_at":
            datetime.now(
                timezone.utc
            ),

            "expires_at":
            expires_at
        }
    )


    response = JSONResponse(
        {
            "status": "ok",
            "message":
            "Login successful.",
            "user": {
                "id":
                str(user["_id"]),

                "username":
                user["username"]
            }
        }
    )


    response.set_cookie(
        key="pinvpn_session",
        value=session_token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=True,
        samesite="lax"
    )


    return response


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/auth/me")
async def current_user(
    request: Request
):

    if db is None:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "Database is not connected."
            }
        )


    token = request.cookies.get(
        "pinvpn_session"
    )


    if not token:

        return {
            "authenticated":
            False
        }


    session = await db.sessions.find_one(
        {
            "token":
            token
        }
    )


    if not session:

        return {
            "authenticated":
            False
        }


    if session["expires_at"] < datetime.now(
        timezone.utc
    ):

        await db.sessions.delete_one(
            {
                "_id":
                session["_id"]
            }
        )

        return {
            "authenticated":
            False
        }


    user = await db.users.find_one(
        {
            "_id":
            session["user_id"]
        }
    )


    if not user:

        return {
            "authenticated":
            False
        }


    return {
        "authenticated":
        True,

        "user": {
            "id":
            str(user["_id"]),

            "username":
            user["username"],

            "created_at":
            user["created_at"].isoformat(),

            "active":
            user.get(
                "active",
                True
            )
        }
    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/auth/logout")
async def logout(
    request: Request
):

    if db is None:

        return {
            "status":
            "ok"
        }


    token = request.cookies.get(
        "pinvpn_session"
    )


    if token:

        await db.sessions.delete_one(
            {
                "token":
                token
            }
        )


    response = JSONResponse(
        {
            "status":
            "ok",
            "message":
            "Logged out."
        }
    )


    response.delete_cookie(
        "pinvpn_session"
    )


    return response
