import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends
)

from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    Response
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from motor.motor_asyncio import AsyncIOMotorClient

import bcrypt

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey
)

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption
)

from bson import ObjectId

import httpx

from pydantic import BaseModel

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ============================================================
# PINVPN
# Backend
# ============================================================

app = FastAPI(
    title="PinVPN API",
    version="1.0.0"
)

client_security = HTTPBearer()

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
# WIREGUARD KEY GENERATION
# ============================================================

def generate_wireguard_keypair():

    private_key = X25519PrivateKey.generate()

    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption()
    )

    public_bytes = public_key.public_bytes(
        Encoding.Raw,
        PublicFormat.Raw
    )

    import base64

    private_key_base64 = base64.b64encode(
        private_bytes
    ).decode("ascii")

    public_key_base64 = base64.b64encode(
        public_bytes
    ).decode("ascii")

    return (
        private_key_base64,
        public_key_base64
    )

# ============================================================
# MONGODB
# ============================================================

MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "pinvpn"
)

# ============================================================
# GETIP / WIREGUARD
# ============================================================

GETIP_VPN_ADDRESS = os.getenv(
    "GETIP_VPN_ADDRESS"
)

GETIP_VPN_DNS = os.getenv(
    "GETIP_VPN_DNS"
)

GETIP_VPN_PUBLIC_KEY = os.getenv(
    "GETIP_VPN_PUBLIC_KEY"
)

GETIP_VPN_ENDPOINT = os.getenv(
    "GETIP_VPN_ENDPOINT"
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

        await db.devices.create_index(
            "user_id"
        )
        
        await db.devices.create_index(
            [
                ("user_id", 1),
                ("name", 1)
            ]
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

@app.head("/")
async def home_head():
    return Response(status_code=200)

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
async def auth_me(request: Request):

    user = await current_user(request)

    if not user:
        return {
            "authenticated": False
        }

    return {
        "authenticated": True,
        "user": {
            "username": user.get("username"),
            "active": user.get("active", True)
        }
    }

async def current_user(request: Request):

    session_token = request.cookies.get(
        "pinvpn_session"
    )

    if not session_token:
        return None

    session = await db.sessions.find_one(
        {
            "token": session_token
        }
    )

    if not session:
        return None

    expires_at = session.get("expires_at")

    if not expires_at:
        await db.sessions.delete_one(
            {
                "_id": session["_id"]
            }
        )

        return None

    # MongoDB может вернуть datetime без timezone.
    # Приводим его к UTC.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    # Проверяем срок действия сессии.
    if expires_at < datetime.now(timezone.utc):

        await db.sessions.delete_one(
            {
                "_id": session["_id"]
            }
        )

        return None

    # Находим аккаунт пользователя.
    user = await db.users.find_one(
        {
            "_id": session["user_id"]
        }
    )

    if not user:
        await db.sessions.delete_one(
            {
                "_id": session["_id"]
            }
        )

        return None

    # Если аккаунт отключён.
    if not user.get("active", True):
        return None

    return user

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

class ClientLoginRequest(BaseModel):
    username: str
    password: str

# ============================================================
# PINVPN CLIENT
# Авторизация Windows / Android клиента
# ============================================================

from pydantic import BaseModel

@app.post("/api/client/login")
async def client_login(
    data: ClientLoginRequest
):
    if db is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database is not connected."
            }
        )

    username = data.username.strip()
    password = data.password

    if not username or not password:
        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Username and password are required."
            }
        )

    user = await db.users.find_one(
        {
            "username_lower":
            username.lower()
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

    if not user.get("active", True):
        return JSONResponse(
            status_code=403,
            content={
                "detail":
                "This account is disabled."
            }
        )

    client_token = secrets.token_urlsafe(48)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=90)

    await db.client_tokens.insert_one(
        {
            "token": client_token,
            "user_id": user["_id"],
            "created_at": now,
            "expires_at": expires_at,
            "active": True
        }
    )

    return {
        "status": "ok",
        "token": client_token,
        "expires_at":
            expires_at.isoformat(),
        "user": {
            "id": str(user["_id"]),
            "username": user["username"]
        }
    }

# ============================================================
# CLIENT AUTHENTICATION
# ============================================================

async def client_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = None
):

    token = None

    # Если токен передан через Swagger / HTTPBearer
    if credentials:
        token = credentials.credentials

    # Обычный вариант через Authorization header
    if not token:
        token = request.headers.get("Authorization")

        if token and token.startswith("Bearer "):
            token = token[7:]

    if not token:
        return None

    token = token.strip()

    if not token:
        return None

    client_token = await db.client_tokens.find_one(
        {
            "token": token,
            "active": True
        }
    )

    if not client_token:
        return None

    expires_at = client_token.get("expires_at")

    if not expires_at:
        await db.client_tokens.delete_one(
            {"_id": client_token["_id"]}
        )
        return None

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at < datetime.now(timezone.utc):
        await db.client_tokens.update_one(
            {"_id": client_token["_id"]},
            {
                "$set": {
                    "active": False
                }
            }
        )
        return None

    user = await db.users.find_one(
        {
            "_id": client_token["user_id"]
        }
    )

    if not user:
        return None

    if not user.get("active", True):
        return None

    return user

# ============================================================
# CLIENT DEVICES
# ============================================================

@app.get("/api/client/devices")
async def client_get_devices(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(client_security)
):

    if db is None:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "Database is not connected."
            }
        )

    user = await client_user(
        request,
        credentials
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Client authentication required."
            }
        )

    devices = []

    cursor = db.devices.find(
        {
            "user_id":
            user["_id"]
        }
    ).sort(
        "created_at",
        -1
    )

    async for device in cursor:

        devices.append(
            {
                "id":
                str(device["_id"]),

                "name":
                device.get(
                    "name",
                    "Unnamed device"
                ),

                "status":
                device.get(
                    "status",
                    "offline"
                ),

                "ipv6":
                device.get(
                    "getip",
                    {}
                ).get(
                    "ipv6"
                ),

                "created_at":
                device["created_at"].isoformat()
                if device.get("created_at")
                else None
            }
        )

    return {
        "status":
        "ok",

        "devices":
        devices
    }

# ============================================================
# CLIENT WIREGUARD CONFIG
# ============================================================

@app.get(
    "/api/client/devices/{device_id}/wireguard"
)
async def client_get_wireguard_config(
    device_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(client_security)
):

    if db is None:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "Database is not connected."
            }
        )

    user = await client_user(
        request,
        credentials
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Client authentication required."
            }
        )

    try:

        device_object_id = ObjectId(
            device_id
        )

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Invalid device ID."
            }
        )

    device = await db.devices.find_one(
        {
            "_id":
            device_object_id,

            "user_id":
            user["_id"]
        }
    )

    if not device:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "Device not found."
            }
        )

    wireguard = device.get(
        "wireguard"
    )

    if not wireguard:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "WireGuard configuration is not available."
            }
        )

    config = wireguard.get(
        "config"
    )

    if not config:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "WireGuard configuration is not available."
            }
        )

    return {

        "status":
        "ok",

        "device": {

            "id":
            str(device["_id"]),

            "name":
            device.get(
                "name",
                "Device"
            ),

            "ipv6":
            device.get(
                "getip",
                {}
            ).get(
                "ipv6"
            )
        },

        "wireguard_config":
        config
    }

# ============================================================
# DEVICES
# ============================================================

@app.get("/api/devices")
async def get_devices(
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

    user = await current_user(request)

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Authentication required."
            }
        )

    devices = []

    cursor = db.devices.find(
        {
            "user_id": user["_id"]
        }
    ).sort(
        "created_at",
        -1
    )

    async for device in cursor:

        devices.append(
            {
                "id":
                str(device["_id"]),

                "name":
                device.get(
                    "name",
                    "Unnamed device"
                ),

                "status":
                device.get(
                    "status",
                    "offline"
                ),

                "created_at":
                device["created_at"].isoformat()
                if device.get("created_at")
                else None
            }
        )

    return {
        "devices": devices
    }

# ============================================================
# GETIP
# Создание туннеля и получение WireGuard конфигурации
# ============================================================

async def create_getip_tunnel():

    getip_session = os.getenv(
        "GETIP_PHPSESSID"
    )

    if not getip_session:

        raise RuntimeError(
            "GETIP_PHPSESSID is not configured."
        )

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        # ----------------------------------------------------
        # 1. СОЗДАЁМ TUNNEL
        # ----------------------------------------------------

        create_response = await client.post(

            "https://getip.online/api/tunnels/create.php",

            files={
                "comment": (
                    None,
                    "PinVPN-Device"
                ),

                "server_id": (
                    None,
                    "3"
                )
            },

            headers={
                "Cookie":
                f"PHPSESSID={getip_session}"
            }
        )

        try:

            create_data = (
                create_response.json()
            )

        except Exception:

            raise RuntimeError(
                "GetIP returned invalid JSON while creating tunnel."
            )

        if (
            create_response.status_code != 200
            or
            not create_data.get("success")
        ):

            raise RuntimeError(
                "GetIP tunnel creation failed: "
                + str(create_data)
            )

        tunnel_id = create_data.get(
            "tunnel_id"
        )

        tunnel_uuid = create_data.get(
            "tunnel_uuid"
        )

        ipv6 = create_data.get(
            "ipv6"
        )

        if not tunnel_id:

            raise RuntimeError(
                "GetIP did not return tunnel_id."
            )

        # ----------------------------------------------------
        # 2. ПОЛУЧАЕМ WIREGUARD CONFIG
        # ----------------------------------------------------

        download_response = await client.get(

            "https://getip.online/api/tunnels/download.php",

            params={
                "tunnel_id":
                tunnel_id
            },

            headers={
                "Cookie":
                f"PHPSESSID={getip_session}"
            }
        )

        if download_response.status_code != 200:

            raise RuntimeError(
                "GetIP tunnel was created, "
                "but WireGuard configuration "
                "could not be downloaded. "
                f"HTTP {download_response.status_code}"
            )

        wireguard_config = (
            download_response.text
        )

        # ----------------------------------------------------
        # 3. ПРОВЕРЯЕМ CONFIG
        # ----------------------------------------------------

        if (
            "[Interface]" not in wireguard_config
            or
            "[Peer]" not in wireguard_config
        ):

            raise RuntimeError(
                "GetIP returned an invalid WireGuard configuration."
            )

        return {
            "tunnel_id":
            tunnel_id,

            "tunnel_uuid":
            tunnel_uuid,

            "ipv6":
            ipv6,

            "config":
            wireguard_config
        }

# ============================================================
# GETIP
# Удаление туннеля
# ============================================================

async def delete_getip_tunnel(
    tunnel_id
):

    getip_session = os.getenv(
        "GETIP_PHPSESSID"
    )

    if not getip_session:

        raise RuntimeError(
            "GETIP_PHPSESSID is not configured."
        )

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        response = await client.post(

            "https://getip.online/api/tunnels/delete.php",

            json={
                "tunnel_id":
                tunnel_id
            },

            headers={
                "Cookie":
                f"PHPSESSID={getip_session}"
            }
        )

        try:

            data = response.json()

        except Exception:

            raise RuntimeError(
                "GetIP returned invalid JSON while deleting tunnel."
            )

        if response.status_code != 200:

            raise RuntimeError(
                "GetIP tunnel deletion failed: "
                + str(data)
            )

        if not data.get("success"):

            raise RuntimeError(
                "GetIP refused to delete tunnel: "
                + str(data)
            )

        return data

@app.post("/api/devices")
async def create_device(
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

    # --------------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------------

    user = await current_user(
        request
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Authentication required."
            }
        )

    # --------------------------------------------------------
    # READ JSON
    # --------------------------------------------------------

    try:

        data = await request.json()

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Invalid JSON."
            }
        )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    # --------------------------------------------------------
    # VALIDATE DEVICE NAME
    # --------------------------------------------------------

    if not name:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Device name is required."
            }
        )

    if len(name) > 50:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Device name is too long."
            }
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE NAME
    # --------------------------------------------------------

    existing_device = await db.devices.find_one(
        {
            "user_id":
            user["_id"],

            "name":
            name
        }
    )

    if existing_device:

        return JSONResponse(
            status_code=409,
            content={
                "detail":
                "A device with this name already exists."
            }
        )

    # --------------------------------------------------------
    # CREATE GETIP TUNNEL
    # --------------------------------------------------------

    try:

        getip_tunnel = (
            await create_getip_tunnel()
        )

    except Exception as error:

        print(
            "[GETIP] Device tunnel creation failed:",
            error
        )

        return JSONResponse(
            status_code=502,
            content={
                "detail":
                "Unable to create VPN tunnel.",

                "error":
                str(error)
            }
        )

    # --------------------------------------------------------
    # SAVE DEVICE
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    device = {

        "user_id":
        user["_id"],

        "name":
        name,

        "status":
        "offline",

        "getip": {

            "tunnel_id":
            getip_tunnel["tunnel_id"],

            "tunnel_uuid":
            getip_tunnel["tunnel_uuid"],

            "ipv6":
            getip_tunnel["ipv6"]
        },

        "wireguard": {

            "config":
            getip_tunnel["config"]
        },

        "created_at":
        now
    }

    try:

        result = await db.devices.insert_one(
            device
        )

    except Exception as error:

        print(
            "[MONGO] Failed to save device:",
            error
        )

        # ====================================================
        # ROLLBACK
        # Если MongoDB не смогла сохранить устройство,
        # удаляем уже созданный туннель GetIP.
        # ====================================================

        try:

            await delete_getip_tunnel(
                getip_tunnel["tunnel_id"]
            )

            print(
                "[GETIP] Rollback successful. "
                "Orphan tunnel deleted:",
                getip_tunnel["tunnel_id"]
            )

        except Exception as rollback_error:

            print(
                "[GETIP] CRITICAL: "
                "Could not rollback tunnel:",
                rollback_error
            )

        return JSONResponse(
            status_code=500,
            content={
                "detail":
                "VPN tunnel was created, "
                "but the device could not be saved."
            }
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {

        "status":
        "ok",

        "device": {

            "id":
            str(result.inserted_id),

            "name":
            name,

            "status":
            "offline",

            "ipv6":
            getip_tunnel["ipv6"],

            "created_at":
            now.isoformat()
        }
    }

@app.delete("/api/devices/{device_id}")
async def delete_device(
    device_id: str,
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

    # --------------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------------

    user = await current_user(
        request
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Authentication required."
            }
        )

    # --------------------------------------------------------
    # OBJECT ID
    # --------------------------------------------------------

    try:

        device_object_id = ObjectId(
            device_id
        )

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Invalid device ID."
            }
        )

    # --------------------------------------------------------
    # FIND DEVICE
    # --------------------------------------------------------

    device = await db.devices.find_one(
        {
            "_id":
            device_object_id,

            "user_id":
            user["_id"]
        }
    )

    if not device:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "Device not found."
            }
        )

    # --------------------------------------------------------
    # GET GETIP TUNNEL ID
    # --------------------------------------------------------

    getip = device.get(
        "getip"
    )

    tunnel_id = None

    if getip:

        tunnel_id = getip.get(
            "tunnel_id"
        )

    # --------------------------------------------------------
    # DELETE GETIP TUNNEL
    # --------------------------------------------------------

    if tunnel_id:

        try:

            await delete_getip_tunnel(
                tunnel_id
            )

        except Exception as error:

            print(
                "[GETIP] Failed to delete tunnel:",
                error
            )

            return JSONResponse(
                status_code=502,
                content={
                    "detail":
                    "The GetIP tunnel could not be deleted. "
                    "The device was not removed from PinVPN.",

                    "error":
                    str(error)
                }
            )

    # --------------------------------------------------------
    # DELETE MONGODB DEVICE
    # --------------------------------------------------------

    result = await db.devices.delete_one(
        {
            "_id":
            device_object_id,

            "user_id":
            user["_id"]
        }
    )

    if result.deleted_count != 1:

        return JSONResponse(
            status_code=500,
            content={
                "detail":
                "Device could not be removed from database."
            }
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {

        "status":
        "ok",

        "message":
        "Device and GetIP tunnel deleted successfully.",

        "device_id":
        device_id,

        "tunnel_id":
        tunnel_id
    }

# ============================================================
# WIREGUARD CONFIGURATION
# ============================================================

@app.get("/api/devices/{device_id}/wireguard")
async def download_wireguard_config(
    device_id: str,
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

    # --------------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------------

    user = await current_user(
        request
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "detail":
                "Authentication required."
            }
        )

    # --------------------------------------------------------
    # CHECK OBJECT ID
    # --------------------------------------------------------

    try:

        device_object_id = ObjectId(
            device_id
        )

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "detail":
                "Invalid device ID."
            }
        )

    # --------------------------------------------------------
    # FIND DEVICE
    # --------------------------------------------------------

    device = await db.devices.find_one(
        {
            "_id":
            device_object_id,

            "user_id":
            user["_id"]
        }
    )

    if not device:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "Device not found."
            }
        )

    # --------------------------------------------------------
    # GET STORED WIREGUARD CONFIG
    # --------------------------------------------------------

    wireguard = device.get(
        "wireguard"
    )

    if not wireguard:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "WireGuard configuration is not available for this device."
            }
        )

    config = wireguard.get(
        "config"
    )

    if not config:

        return JSONResponse(
            status_code=404,
            content={
                "detail":
                "WireGuard configuration is not available for this device."
            }
        )

    # --------------------------------------------------------
    # DOWNLOAD .CONF
    # --------------------------------------------------------

    filename = (
        "PinVPN-"
        + device.get(
            "name",
            "Device"
        )
        .replace(
            " ",
            "-"
        )
        + ".conf"
    )

    return Response(

        content=config,

        media_type=
        "application/octet-stream",

        headers={
            "Content-Disposition":
            f'attachment; filename="{filename}"'
        }
    )

# ============================================================
# GETIP TEST
# Создание туннеля + получение WireGuard конфигурации
# ============================================================

@app.post("/api/getip/test")
async def test_getip_tunnel():

    getip_session = os.getenv(
        "GETIP_PHPSESSID"
    )

    if not getip_session:

        return JSONResponse(
            status_code=503,
            content={
                "detail":
                "GETIP_PHPSESSID is not configured."
            }
        )

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            # ------------------------------------------------
            # 1. СОЗДАЁМ GETIP TUNNEL
            # ------------------------------------------------

            create_response = await client.post(

                "https://getip.online/api/tunnels/create.php",

                files={
                    "comment": (
                        None,
                        "PinVPN-Auto-Test"
                    ),

                    "server_id": (
                        None,
                        "3"
                    )
                },

                headers={
                    "Cookie":
                    f"PHPSESSID={getip_session}"
                }
            )

            # ------------------------------------------------
            # Проверяем JSON ответа
            # ------------------------------------------------

            try:

                create_data = (
                    create_response.json()
                )

            except Exception:

                return JSONResponse(
                    status_code=502,
                    content={
                        "detail":
                        "GetIP returned invalid JSON while creating tunnel.",

                        "getip_status":
                        create_response.status_code,

                        "response":
                        create_response.text[:1000]
                    }
                )

            # ------------------------------------------------
            # Проверяем создание туннеля
            # ------------------------------------------------

            if (
                create_response.status_code != 200
                or
                not create_data.get("success")
            ):

                return JSONResponse(
                    status_code=502,
                    content={
                        "detail":
                        "GetIP tunnel creation failed.",

                        "getip_status":
                        create_response.status_code,

                        "getip_response":
                        create_data
                    }
                )

            tunnel_id = create_data.get(
                "tunnel_id"
            )

            tunnel_uuid = create_data.get(
                "tunnel_uuid"
            )

            ipv6 = create_data.get(
                "ipv6"
            )

            if not tunnel_id:

                return JSONResponse(
                    status_code=502,
                    content={
                        "detail":
                        "GetIP created the tunnel but did not return tunnel_id.",

                        "getip_response":
                        create_data
                    }
                )

            # ------------------------------------------------
            # 2. ПОЛУЧАЕМ WIREGUARD CONFIG
            # ------------------------------------------------

            download_response = await client.get(

                "https://getip.online/api/tunnels/download.php",

                params={
                    "tunnel_id":
                    tunnel_id
                },

                headers={
                    "Cookie":
                    f"PHPSESSID={getip_session}"
                }
            )

            # ------------------------------------------------
            # Проверяем получение конфигурации
            # ------------------------------------------------

            if download_response.status_code != 200:

                return JSONResponse(
                    status_code=502,
                    content={
                        "detail":
                        "Tunnel was created, but WireGuard configuration could not be downloaded.",

                        "tunnel_id":
                        tunnel_id,

                        "tunnel_uuid":
                        tunnel_uuid,

                        "ipv6":
                        ipv6,

                        "getip_status":
                        download_response.status_code,

                        "getip_response":
                        download_response.text[:1000]
                    }
                )

            wireguard_config = (
                download_response.text
            )

            # ------------------------------------------------
            # Проверяем, что это действительно WireGuard config
            # ------------------------------------------------

            if (
                "[Interface]" not in wireguard_config
                or
                "[Peer]" not in wireguard_config
            ):

                return JSONResponse(
                    status_code=502,
                    content={
                        "detail":
                        "GetIP returned an unexpected WireGuard configuration.",

                        "tunnel_id":
                        tunnel_id,

                        "response":
                        wireguard_config[:2000]
                    }
                )

            # ------------------------------------------------
            # 3. УСПЕШНЫЙ РЕЗУЛЬТАТ
            # ------------------------------------------------

            return {

                "status":
                "ok",

                "message":
                "GetIP tunnel created and WireGuard configuration downloaded successfully.",

                "tunnel": {

                    "id":
                    tunnel_id,

                    "uuid":
                    tunnel_uuid,

                    "ipv6":
                    ipv6
                },

                "wireguard_config":
                wireguard_config
            }

    except Exception as error:

        return JSONResponse(
            status_code=500,
            content={
                "detail":
                "GetIP request failed.",

                "error":
                str(error)
            }
        )
