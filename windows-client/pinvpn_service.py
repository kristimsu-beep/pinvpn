import json
import os
import re
import secrets
import socketserver
import subprocess
import threading
import time

import win32event
import win32service
import win32serviceutil
import servicemanager


# ============================================================
# PINVPN SERVICE
# ============================================================

SERVICE_NAME = "PinVPNService"
SERVICE_DISPLAY_NAME = "PinVPN Service"
SERVICE_DESCRIPTION = (
    "Privileged VPN controller for PinVPN."
)

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 47811

PROGRAM_DATA = os.environ.get(
    "PROGRAMDATA",
    r"C:\ProgramData"
)

PINVPN_DIR = os.path.join(
    PROGRAM_DATA,
    "PinVPN"
)

RUNTIME_DIR = os.path.join(
    PINVPN_DIR,
    "Runtime"
)

TOKEN_FILE = os.path.join(
    PINVPN_DIR,
    "service.token"
)

CONFIG_FILE = os.path.join(
    RUNTIME_DIR,
    "pinvpn.conf"
)

WIREGUARD_EXE = r"C:\Program Files\WireGuard\wireguard.exe"

TUNNEL_NAME = "pinvpn"

TUNNEL_SERVICE_NAME = (
    f"WireGuardTunnel${TUNNEL_NAME}"
)


# ============================================================
# WINDOWS ACL
# ============================================================

def run_icacls(path, arguments):

    command = [
        "icacls",
        path,
        *arguments,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
    )

    if result.returncode != 0:

        raise RuntimeError(
            "Не удалось настроить права Windows:\n"
            + (
                result.stderr
                or result.stdout
                or "icacls returned an error."
            )
        )


def setup_directories():

    os.makedirs(
        PINVPN_DIR,
        exist_ok=True,
    )

    os.makedirs(
        RUNTIME_DIR,
        exist_ok=True,
    )

    # Главная папка:
    # SYSTEM + Administrators = полный доступ
    # Users = чтение/переход
    run_icacls(
        PINVPN_DIR,
        [
            "/inheritance:r",
            "/grant:r",
            "*S-1-5-18:F",
            "*S-1-5-32-544:F",
            "*S-1-5-32-545:RX",
        ],
    )

    # Runtime:
    # только SYSTEM + Administrators
    run_icacls(
        RUNTIME_DIR,
        [
            "/inheritance:r",
            "/grant:r",
            "*S-1-5-18:F",
            "*S-1-5-32-544:F",
        ],
    )


def setup_token():

    setup_directories()

    if not os.path.exists(
        TOKEN_FILE
    ):

        token = secrets.token_urlsafe(
            48
        )

        with open(
            TOKEN_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(token)

    # Token должен читаться PinVPN.exe,
    # но не изменяться обычным пользователем.
    run_icacls(
        TOKEN_FILE,
        [
            "/inheritance:r",
            "/grant:r",
            "*S-1-5-18:F",
            "*S-1-5-32-544:F",
            "*S-1-5-32-545:R",
        ],
    )


def load_token():

    setup_token()

    with open(
        TOKEN_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        token = file.read().strip()

    if not token:

        raise RuntimeError(
            "PinVPN service token is empty."
        )

    return token


# ============================================================
# WIREGUARD HELPERS
# ============================================================

def run_command(
    command,
    timeout=30,
):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return result


def tunnel_exists():

    result = run_command(
        [
            "sc.exe",
            "query",
            TUNNEL_SERVICE_NAME,
        ],
        timeout=15,
    )

    text = (
        result.stdout
        + "\n"
        + result.stderr
    )

    return (
        "FAILED 1060" not in text
        and
        "does not exist" not in text.lower()
        and
        result.returncode == 0
    )


def tunnel_state():

    result = run_command(
        [
            "sc.exe",
            "query",
            TUNNEL_SERVICE_NAME,
        ],
        timeout=15,
    )

    if result.returncode != 0:

        return "NOT_INSTALLED"

    match = re.search(
        r"STATE\s*:\s*(\d+)\s+(\w+)",
        result.stdout,
        re.IGNORECASE,
    )

    if not match:

        return "UNKNOWN"

    state_name = match.group(2).upper()

    if state_name == "RUNNING":
        return "RUNNING"

    if state_name == "STOPPED":
        return "STOPPED"

    if state_name == "START_PENDING":
        return "STARTING"

    if state_name == "STOP_PENDING":
        return "STOPPING"

    return state_name


def stop_tunnel():

    if not tunnel_exists():

        return

    result = run_command(
        [
            "sc.exe",
            "stop",
            TUNNEL_SERVICE_NAME,
        ],
        timeout=30,
    )

    # 1062 = service not running.
    if (
        result.returncode != 0
        and
        "1062" not in (
            result.stdout
            + result.stderr
        )
    ):

        raise RuntimeError(
            "Не удалось остановить WireGuard-туннель:\n"
            +
            (
                result.stderr
                or result.stdout
                or "Unknown error."
            )
        )

    for _ in range(30):

        state = tunnel_state()

        if state in (
            "STOPPED",
            "NOT_INSTALLED",
        ):

            return

        time.sleep(0.2)

    raise RuntimeError(
        "WireGuard-туннель слишком долго "
        "переходил в состояние остановки."
    )


def start_existing_tunnel():

    result = run_command(
        [
            "sc.exe",
            "start",
            TUNNEL_SERVICE_NAME,
        ],
        timeout=30,
    )

    if (
        result.returncode != 0
        and
        "1056" not in (
            result.stdout
            + result.stderr
        )
    ):

        raise RuntimeError(
            "Не удалось запустить WireGuard-туннель:\n"
            +
            (
                result.stderr
                or result.stdout
                or "Unknown error."
            )
        )

    for _ in range(50):

        state = tunnel_state()

        if state == "RUNNING":

            return

        time.sleep(0.2)

    raise RuntimeError(
        "WireGuard-туннель не перешёл "
        "в состояние RUNNING."
    )


def install_tunnel():

    if not os.path.exists(
        WIREGUARD_EXE
    ):

        raise RuntimeError(
            "WireGuard не найден по адресу:\n"
            f"{WIREGUARD_EXE}"
        )

    if tunnel_exists():

        return

    result = run_command(
        [
            WIREGUARD_EXE,
            "/installtunnelservice",
            CONFIG_FILE,
        ],
        timeout=60,
    )

    if result.returncode != 0:

        raise RuntimeError(
            "WireGuard не смог установить "
            "туннельную службу.\n\n"
            +
            (
                result.stderr
                or result.stdout
                or "Unknown error."
            )
        )


def connect_tunnel(config):

    if not config:

        raise RuntimeError(
            "Получена пустая WireGuard-конфигурация."
        )

    if "[Interface]" not in config:

        raise RuntimeError(
            "Конфигурация WireGuard "
            "не содержит [Interface]."
        )

    if "[Peer]" not in config:

        raise RuntimeError(
            "Конфигурация WireGuard "
            "не содержит [Peer]."
        )

    setup_directories()

    # Если старый туннель работает —
    # сначала останавливаем.
    if tunnel_exists():

        stop_tunnel()

    # Записываем конфигурацию от имени
    # привилегированной службы.
    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            config.strip()
            + "\n"
        )

    # Защищаем конфигурацию:
    # обычный пользователь не может
    # читать/изменять этот файл напрямую.
    run_icacls(
        CONFIG_FILE,
        [
            "/inheritance:r",
            "/grant:r",
            "*S-1-5-18:F",
            "*S-1-5-32-544:F",
        ],
    )

    # Если служба ещё никогда не создавалась —
    # создаём её через официальный WireGuard CLI.
    if not tunnel_exists():

        install_tunnel()

    else:

        start_existing_tunnel()

    # После installtunnelservice WireGuard
    # должен создать и запустить сервис.
    for _ in range(50):

        state = tunnel_state()

        if state == "RUNNING":

            return

        if state == "NOT_INSTALLED":

            # Повторная попытка установки.
            install_tunnel()

        time.sleep(0.2)

    raise RuntimeError(
        "WireGuard-туннель не запустился."
    )


def uninstall_tunnel():

    if not tunnel_exists():

        return

    stop_tunnel()

    result = run_command(
        [
            WIREGUARD_EXE,
            "/uninstalltunnelservice",
            TUNNEL_NAME,
        ],
        timeout=60,
    )

    if (
        result.returncode != 0
        and
        "does not exist" not in (
            result.stdout
            + result.stderr
        ).lower()
    ):

        raise RuntimeError(
            "Не удалось удалить "
            "WireGuard-туннель:\n"
            +
            (
                result.stderr
                or result.stdout
                or "Unknown error."
            )
        )

    try:

        if os.path.exists(
            CONFIG_FILE
        ):

            os.remove(
                CONFIG_FILE
            )

    except OSError:

        pass


# ============================================================
# TCP SERVER
# ============================================================

class PinVPNRequestHandler(
    socketserver.StreamRequestHandler
):

    def send_response(
        self,
        payload,
    ):

        data = (
            json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n"
        ).encode(
            "utf-8"
        )

        self.wfile.write(
            data
        )

        self.wfile.flush()

    def handle(self):

        try:

            raw = self.rfile.readline(
                1024 * 1024
            )

            if not raw:

                return

            request = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

            token = request.get(
                "token"
            )

            expected_token = (
                self.server.service_token
            )

            if not secrets.compare_digest(
                str(token or ""),
                str(expected_token),
            ):

                self.send_response(
                    {
                        "status": "error",
                        "error": "unauthorized",
                    }
                )

                return

            action = request.get(
                "action"
            )

            if action == "ping":

                self.send_response(
                    {
                        "status": "ok",
                        "service": "PinVPN",
                    }
                )

                return

            if action == "status":

                state = tunnel_state()

                self.send_response(
                    {
                        "status": "ok",
                        "connected": (
                            state == "RUNNING"
                        ),
                        "state": state,
                    }
                )

                return

            if action == "connect":

                config = request.get(
                    "config"
                )

                connect_tunnel(
                    config
                )

                self.send_response(
                    {
                        "status": "ok",
                        "connected": True,
                    }
                )

                return

            if action == "disconnect":

                stop_tunnel()

                self.send_response(
                    {
                        "status": "ok",
                        "connected": False,
                    }
                )

                return

            if action == "remove_tunnel":

                uninstall_tunnel()

                self.send_response(
                    {
                        "status": "ok",
                        "connected": False,
                    }
                )

                return

            self.send_response(
                {
                    "status": "error",
                    "error": (
                        "Unknown action."
                    ),
                }
            )

        except Exception as error:

            self.send_response(
                {
                    "status": "error",
                    "error": str(error),
                }
            )


class PinVPNTCPServer(
    socketserver.ThreadingTCPServer
):

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address,
        handler_class,
        service_token,
    ):

        self.service_token = (
            service_token
        )

        super().__init__(
            server_address,
            handler_class,
        )


# ============================================================
# WINDOWS SERVICE
# ============================================================

class PinVPNService(
    win32serviceutil.ServiceFramework
):

    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = (
        SERVICE_DISPLAY_NAME
    )
    _svc_description_ = (
        SERVICE_DESCRIPTION
    )

    def __init__(
        self,
        args,
    ):

        super().__init__(
            args
        )

        self.stop_event = (
            win32event.CreateEvent(
                None,
                0,
                0,
                None,
            )
        )

        self.server = None
        self.server_thread = None

    def SvcStop(
        self
    ):

        self.ReportServiceStatus(
            win32service.SERVICE_STOP_PENDING
        )

        if self.server:

            try:

                self.server.shutdown()

            except Exception:
                pass

            try:

                self.server.server_close()

            except Exception:
                pass

        win32event.SetEvent(
            self.stop_event
        )

    def SvcDoRun(
        self
    ):

        servicemanager.LogInfoMsg(
            "PinVPN Service starting."
        )

        try:

            token = load_token()

            self.server = (
                PinVPNTCPServer(
                    (
                        SERVICE_HOST,
                        SERVICE_PORT,
                    ),
                    PinVPNRequestHandler,
                    token,
                )
            )

            self.server_thread = (
                threading.Thread(
                    target=self.server.serve_forever,
                    daemon=True,
                )
            )

            self.server_thread.start()

            servicemanager.LogInfoMsg(
                "PinVPN Service started."
            )

            win32event.WaitForSingleObject(
                self.stop_event,
                win32event.INFINITE,
            )

        except Exception as error:

            servicemanager.LogErrorMsg(
                "PinVPN Service error: "
                + str(error)
            )

            raise

        finally:

            if self.server:

                try:
                    self.server.shutdown()
                except Exception:
                    pass

                try:
                    self.server.server_close()
                except Exception:
                    pass

            servicemanager.LogInfoMsg(
                "PinVPN Service stopped."
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    win32serviceutil.HandleCommandLine(
        PinVPNService
    )
