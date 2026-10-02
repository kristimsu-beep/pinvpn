import sys
import os
import json
import socket
import keyring
import requests

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QStackedWidget,
    QFrame,
    QSizePolicy,
)


# ============================================================
# CONFIG
# ============================================================

SERVER_URL = "https://pinvpn.onrender.com"

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 47811

SERVICE_TOKEN_FILE = r"C:\ProgramData\PinVPN\service.token"

KEYRING_SERVICE = "PinVPN"
KEYRING_USERNAME = "client_token"


# ============================================================
# COLORS
# ============================================================

BG = "#08090d"
SIDEBAR = "#0d0f14"
CARD = "#11141b"
CARD_2 = "#151820"
BORDER = "#242832"

PINK = "#ff2f7d"
PINK_HOVER = "#ff438b"
PINK_DARK = "#d91d62"

GREEN = "#65e6a1"
RED = "#ff5c7c"
YELLOW = "#ffc857"

WHITE = "#ffffff"
TEXT = "#dce0e8"
MUTED = "#858c9c"
DIM = "#5e6574"


# ============================================================
# PINVPN SERVICE
# ============================================================

def read_service_token():

    if not os.path.exists(SERVICE_TOKEN_FILE):

        raise Exception(
            "PinVPN Service не установлена."
        )

    with open(
        SERVICE_TOKEN_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        token = file.read().strip()

    if not token:

        raise Exception(
            "Токен PinVPN Service пуст."
        )

    return token


def service_request(
    action,
    config=None
):

    token = read_service_token()

    payload = {
        "action": action,
        "token": token,
    }

    if config is not None:

        payload["config"] = config

    message = (
        json.dumps(
            payload,
            ensure_ascii=False
        )
        + "\n"
    ).encode("utf-8")

    try:

        with socket.create_connection(
            (
                SERVICE_HOST,
                SERVICE_PORT
            ),
            timeout=10
        ) as sock:

            sock.sendall(message)

            data = b""

            while True:

                part = sock.recv(65536)

                if not part:
                    break

                data += part

                if b"\n" in part:
                    break

    except OSError as error:

        raise Exception(
            "PinVPN Service недоступна.\n\n"
            f"{error}"
        )

    if not data:

        raise Exception(
            "PinVPN Service не ответила."
        )

    try:

        response = json.loads(
            data.decode("utf-8").strip()
        )

    except json.JSONDecodeError:

        raise Exception(
            "PinVPN Service вернула "
            "некорректный ответ."
        )

    if response.get("status") != "ok":

        raise Exception(
            response.get(
                "error",
                "Ошибка PinVPN Service."
            )
        )

    return response


# ============================================================
# SAVED LOGIN
# ============================================================

def save_login(token, username):

    keyring.set_password(
        KEYRING_SERVICE,
        KEYRING_USERNAME,
        token
    )

    keyring.set_password(
        KEYRING_SERVICE,
        "username",
        username
    )


def load_saved_token():

    return keyring.get_password(
        KEYRING_SERVICE,
        KEYRING_USERNAME
    )


def load_saved_username():

    return keyring.get_password(
        KEYRING_SERVICE,
        "username"
    )


def clear_saved_login():

    for name in (
        KEYRING_USERNAME,
        "username"
    ):

        try:

            keyring.delete_password(
                KEYRING_SERVICE,
                name
            )

        except Exception:

            pass


# ============================================================
# HELPERS
# ============================================================

def card():

    frame = QFrame()

    frame.setObjectName(
        "card"
    )

    return frame


def make_separator():

    line = QFrame()

    line.setFrameShape(
        QFrame.HLine
    )

    line.setObjectName(
        "separator"
    )

    return line


def status_dot():

    label = QLabel("●")

    label.setFixedWidth(18)

    return label


# ============================================================
# MAIN WINDOW
# ============================================================

class PinVPN(QWidget):

    def __init__(self):

        super().__init__()

        self.token = None
        self.devices = []
        self.connected = False
        self.current_username = ""

        self.pulse_animation = None

        self.setWindowTitle(
            "PinVPN"
        )

        self.setMinimumSize(
            980,
            680
        )

        self.resize(
            1250,
            760
        )

        self.build_ui()
        self.apply_style()

        self.service_timer = QTimer(
            self
        )

        self.service_timer.timeout.connect(
            self.refresh_service_status
        )

        self.service_timer.start(
            2500
        )

        self.try_auto_login()

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        root = QVBoxLayout()

        root.setContentsMargins(
            0,
            0,
            0,
            0
        )

        root.setSpacing(
            0
        )

        self.pages = QStackedWidget()

        self.pages.addWidget(
            self.build_login_page()
        )

        self.pages.addWidget(
            self.build_main_page()
        )

        root.addWidget(
            self.pages
        )

        self.setLayout(
            root
        )

    # ========================================================
    # LOGIN
    # ========================================================

    def build_login_page(self):

        page = QWidget()

        page.setObjectName(
            "loginPage"
        )

        outer = QVBoxLayout()

        outer.setAlignment(
            Qt.AlignCenter
        )

        outer.setContentsMargins(
            30,
            30,
            30,
            30
        )

        login_card = card()

        login_card.setMaximumWidth(
            480
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            52,
            48,
            52,
            48
        )

        layout.setSpacing(
            16
        )

        logo = QLabel(
            "PinVPN"
        )

        logo.setObjectName(
            "loginLogo"
        )

        logo.setAlignment(
            Qt.AlignCenter
        )

        subtitle = QLabel(
            "SECURE INTERNET"
        )

        subtitle.setObjectName(
            "loginSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        welcome = QLabel(
            "Добро пожаловать"
        )

        welcome.setObjectName(
            "welcomeText"
        )

        welcome.setAlignment(
            Qt.AlignCenter
        )

        self.username = QLineEdit()

        self.username.setPlaceholderText(
            "Имя пользователя"
        )

        self.username.setMinimumHeight(
            52
        )

        self.password = QLineEdit()

        self.password.setPlaceholderText(
            "Пароль"
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )

        self.password.setMinimumHeight(
            52
        )

        self.login_button = QPushButton(
            "ВОЙТИ"
        )

        self.login_button.setMinimumHeight(
            54
        )

        self.login_button.setCursor(
            Qt.PointingHandCursor
        )

        self.login_button.clicked.connect(
            self.login
        )

        self.login_status = QLabel(
            ""
        )

        self.login_status.setObjectName(
            "loginStatus"
        )

        self.login_status.setAlignment(
            Qt.AlignCenter
        )

        self.login_status.setWordWrap(
            True
        )

        layout.addWidget(
            logo
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            24
        )

        layout.addWidget(
            welcome
        )

        layout.addSpacing(
            10
        )

        layout.addWidget(
            self.username
        )

        layout.addWidget(
            self.password
        )

        layout.addSpacing(
            7
        )

        layout.addWidget(
            self.login_button
        )

        layout.addSpacing(
            8
        )

        layout.addWidget(
            self.login_status
        )

        login_card.setLayout(
            layout
        )

        outer.addWidget(
            login_card
        )

        page.setLayout(
            outer
        )

        return page

    # ========================================================
    # MAIN
    # ========================================================

    def build_main_page(self):

        page = QWidget()

        page.setObjectName(
            "mainPage"
        )

        root = QHBoxLayout()

        root.setContentsMargins(
            0,
            0,
            0,
            0
        )

        root.setSpacing(
            0
        )

        # ====================================================
        # SIDEBAR
        # ====================================================

        sidebar = QWidget()

        sidebar.setObjectName(
            "sidebar"
        )

        sidebar.setFixedWidth(
            245
        )

        side_layout = QVBoxLayout()

        side_layout.setContentsMargins(
            24,
            28,
            24,
            24
        )

        side_layout.setSpacing(
            12
        )

        logo = QLabel(
            "PinVPN"
        )

        logo.setObjectName(
            "sideLogo"
        )

        side_subtitle = QLabel(
            "SECURE INTERNET"
        )

        side_subtitle.setObjectName(
            "sideSubtitle"
        )

        side_layout.addWidget(
            logo
        )

        side_layout.addWidget(
            side_subtitle
        )

        side_layout.addSpacing(
            30
        )

        dashboard = QLabel(
            "◉   ПОДКЛЮЧЕНИЕ"
        )

        dashboard.setObjectName(
            "sideActive"
        )

        side_layout.addWidget(
            dashboard
        )

        side_layout.addStretch()

        version = QLabel(
            "PinVPN\nDesktop"
        )

        version.setObjectName(
            "sideVersion"
        )

        side_layout.addWidget(
            version
        )

        sidebar.setLayout(
            side_layout
        )

        # ====================================================
        # CONTENT
        # ====================================================

        content = QWidget()

        content_layout = QVBoxLayout()

        content_layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        content_layout.setSpacing(
            22
        )

        # Header
        header = QHBoxLayout()

        header.setSpacing(
            12
        )

        title_block = QVBoxLayout()

        title_block.setSpacing(
            2
        )

        title = QLabel(
            "Подключение"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Управление защищённым соединением"
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        title_block.addWidget(
            title
        )

        title_block.addWidget(
            subtitle
        )

        header.addLayout(
            title_block
        )

        header.addStretch()

        self.account_button = QPushButton(
            "●  Аккаунт"
        )

        self.account_button.setObjectName(
            "accountButton"
        )

        self.account_button.setCursor(
            Qt.PointingHandCursor
        )

        self.account_button.clicked.connect(
            self.logout
        )

        header.addWidget(
            self.account_button
        )

        content_layout.addLayout(
            header
        )

        # ====================================================
        # TOP CARDS
        # ====================================================

        top = QHBoxLayout()

        top.setSpacing(
            18
        )

        # Device card
        device_card = card()

        device_card.setMinimumHeight(
            120
        )

        device_layout = QVBoxLayout()

        device_layout.setContentsMargins(
            22,
            18,
            22,
            18
        )

        device_title = QLabel(
            "УСТРОЙСТВО"
        )

        device_title.setObjectName(
            "smallTitle"
        )

        self.device_box = QComboBox()

        self.device_box.setMinimumHeight(
            46
        )

        device_layout.addWidget(
            device_title
        )

        device_layout.addSpacing(
            7
        )

        device_layout.addWidget(
            self.device_box
        )

        device_card.setLayout(
            device_layout
        )

        top.addWidget(
            device_card,
            2
        )

        # Service card
        service_card = card()

        service_layout = QVBoxLayout()

        service_layout.setContentsMargins(
            22,
            18,
            22,
            18
        )

        service_title = QLabel(
            "СЕРВИС"
        )

        service_title.setObjectName(
            "smallTitle"
        )

        self.service_label = QLabel(
            "●  Проверка..."
        )

        self.service_label.setObjectName(
            "serviceValue"
        )

        service_layout.addWidget(
            service_title
        )

        service_layout.addSpacing(
            10
        )

        service_layout.addWidget(
            self.service_label
        )

        service_card.setLayout(
            service_layout
        )

        top.addWidget(
            service_card,
            1
        )

        content_layout.addLayout(
            top
        )

        # ====================================================
        # VPN CENTER
        # ====================================================

        center = card()

        center_layout = QVBoxLayout()

        center_layout.setContentsMargins(
            35,
            30,
            35,
            28
        )

        center_layout.setAlignment(
            Qt.AlignCenter
        )

        self.status_label = QLabel(
            "НЕ ПОДКЛЮЧЕНО"
        )

        self.status_label.setObjectName(
            "mainStatus"
        )

        self.status_hint = QLabel(
            "Ваше соединение не защищено"
        )

        self.status_hint.setObjectName(
            "statusHint"
        )

        # VPN button
        self.connect_button = QPushButton(
            "ПОДКЛЮЧИТЬ"
        )

        self.connect_button.setObjectName(
            "vpnButton"
        )

        self.connect_button.setFixedSize(
            230,
            230
        )

        self.connect_button.setCursor(
            Qt.PointingHandCursor
        )

        self.connect_button.clicked.connect(
            self.toggle_vpn
        )

        self.info_label = QLabel(
            "Выберите устройство и подключитесь к PinVPN"
        )

        self.info_label.setObjectName(
            "centerInfo"
        )

        self.info_label.setAlignment(
            Qt.AlignCenter
        )

        self.info_label.setWordWrap(
            True
        )

        center_layout.addWidget(
            self.status_label,
            alignment=Qt.AlignCenter
        )

        center_layout.addWidget(
            self.status_hint,
            alignment=Qt.AlignCenter
        )

        center_layout.addSpacing(
            22
        )

        center_layout.addWidget(
            self.connect_button,
            alignment=Qt.AlignCenter
        )

        center_layout.addSpacing(
            18
        )

        center_layout.addWidget(
            self.info_label,
            alignment=Qt.AlignCenter
        )

        center.setLayout(
            center_layout
        )

        content_layout.addWidget(
            center,
            1
        )

        # ====================================================
        # BOTTOM INFO
        # ====================================================

        bottom = QHBoxLayout()

        bottom.setSpacing(
            18
        )

        # Protocol
        protocol = card()

        protocol_layout = QVBoxLayout()

        protocol_layout.setContentsMargins(
            22,
            16,
            22,
            16
        )

        protocol_title = QLabel(
            "ПРОТОКОЛ"
        )

        protocol_title.setObjectName(
            "smallTitle"
        )

        self.protocol_value = QLabel(
            "WireGuard"
        )

        self.protocol_value.setObjectName(
            "infoValue"
        )

        protocol_layout.addWidget(
            protocol_title
        )

        protocol_layout.addSpacing(
            5
        )

        protocol_layout.addWidget(
            self.protocol_value
        )

        protocol.setLayout(
            protocol_layout
        )

        bottom.addWidget(
            protocol
        )

        # Network
        network = card()

        network_layout = QVBoxLayout()

        network_layout.setContentsMargins(
            22,
            16,
            22,
            16
        )

        network_title = QLabel(
            "СЕТЬ"
        )

        network_title.setObjectName(
            "smallTitle"
        )

        self.network_value = QLabel(
            "IPv6"
        )

        self.network_value.setObjectName(
            "infoValue"
        )

        network_layout.addWidget(
            network_title
        )

        network_layout.addSpacing(
            5
        )

        network_layout.addWidget(
            self.network_value
        )

        network.setLayout(
            network_layout
        )

        bottom.addWidget(
            network
        )

        # IPv6
        ipv6 = card()

        ipv6_layout = QVBoxLayout()

        ipv6_layout.setContentsMargins(
            22,
            16,
            22,
            16
        )

        ipv6_title = QLabel(
            "PINVPN IPv6"
        )

        ipv6_title.setObjectName(
            "smallTitle"
        )

        self.ipv6_value = QLabel(
            "Активен"
        )

        self.ipv6_value.setObjectName(
            "infoValue"
        )

        ipv6_layout.addWidget(
            ipv6_title
        )

        ipv6_layout.addSpacing(
            5
        )

        ipv6_layout.addWidget(
            self.ipv6_value
        )

        ipv6.setLayout(
            ipv6_layout
        )

        bottom.addWidget(
            ipv6
        )

        content_layout.addLayout(
            bottom
        )

        content.setLayout(
            content_layout
        )

        root.addWidget(
            sidebar
        )

        root.addWidget(
            content,
            1
        )

        page.setLayout(
            root
        )

        self.main_page = page

        return page

    # ========================================================
    # STYLE
    # ========================================================

    def apply_style(self):

        self.setStyleSheet(
            f"""
            * {{
                font-family: "Segoe UI";
            }}

            QWidget {{
                background: {BG};
                color: {WHITE};
                font-size: 14px;
            }}

            QWidget#loginPage {{
                background: {BG};
            }}

            QWidget#mainPage {{
                background: {BG};
            }}

            QFrame#card {{
                background: {CARD};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}

            QFrame#separator {{
                background: {BORDER};
                border: none;
                max-height: 1px;
            }}

            /* LOGIN */

            QLabel#loginLogo {{
                font-size: 54px;
                font-weight: 800;
                color: {PINK};
            }}

            QLabel#loginSubtitle {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 3px;
                color: {MUTED};
            }}

            QLabel#welcomeText {{
                font-size: 19px;
                font-weight: 700;
                color: {TEXT};
            }}

            QLabel#loginStatus {{
                color: {MUTED};
                font-size: 13px;
            }}

            /* SIDEBAR */

            QWidget#sidebar {{
                background: {SIDEBAR};
                border-right: 1px solid {BORDER};
            }}

            QLabel#sideLogo {{
                font-size: 31px;
                font-weight: 800;
                color: {PINK};
            }}

            QLabel#sideSubtitle {{
                color: {DIM};
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#sideActive {{
                background: #19131a;
                border: 1px solid #35202d;
                border-radius: 10px;
                padding: 13px;
                color: {PINK};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#sideVersion {{
                color: {DIM};
                font-size: 11px;
                line-height: 150%;
            }}

            /* HEADER */

            QLabel#pageTitle {{
                font-size: 28px;
                font-weight: 750;
                color: {WHITE};
            }}

            QLabel#pageSubtitle {{
                font-size: 12px;
                color: {MUTED};
            }}

            QPushButton#accountButton {{
                background: {CARD};
                border: 1px solid {BORDER};
                border-radius: 11px;
                padding: 10px 17px;
                color: {TEXT};
                font-weight: 600;
            }}

            QPushButton#accountButton:hover {{
                background: {CARD_2};
                border-color: #353a46;
            }}

            /* TITLES */

            QLabel#smallTitle {{
                color: {DIM};
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 1.8px;
            }}

            QLabel#serviceValue {{
                color: {GREEN};
                font-size: 14px;
                font-weight: 650;
            }}

            /* INPUTS */

            QLineEdit {{
                background: #0d1016;
                border: 1px solid #292e39;
                border-radius: 11px;
                padding: 0 15px;
                color: {WHITE};
                selection-background-color: {PINK};
            }}

            QLineEdit:hover {{
                border-color: #3a404c;
            }}

            QLineEdit:focus {{
                border: 1px solid {PINK};
            }}

            QComboBox {{
                background: #0d1016;
                border: 1px solid #292e39;
                border-radius: 10px;
                padding: 0 13px;
                color: {TEXT};
            }}

            QComboBox:hover {{
                border-color: #3a404c;
            }}

            QComboBox:focus {{
                border-color: {PINK};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 34px;
            }}

            QComboBox QAbstractItemView {{
                background: #151820;
                border: 1px solid #303540;
                color: {WHITE};
                selection-background-color: {PINK};
                selection-color: white;
                padding: 5px;
            }}

            /* BUTTON */

            QPushButton {{
                background: {PINK};
                border: none;
                border-radius: 11px;
                color: white;
                font-weight: 800;
            }}

            QPushButton:hover {{
                background: {PINK_HOVER};
            }}

            QPushButton:pressed {{
                background: {PINK_DARK};
            }}

            QPushButton:disabled {{
                background: #2a2e37;
                color: #666c78;
            }}

            QPushButton#vpnButton {{
                background: #12151c;
                border: 5px solid {PINK};
                border-radius: 115px;
                color: white;
                font-size: 20px;
                font-weight: 800;
            }}

            QPushButton#vpnButton:hover {{
                background: #1a1e27;
            }}

            /* CONNECTED */

            QLabel#mainStatus {{
                color: #aeb4c3;
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#statusHint {{
                color: {MUTED};
                font-size: 12px;
            }}

            QLabel#centerInfo {{
                color: {DIM};
                font-size: 12px;
            }}

            QLabel#infoValue {{
                color: {TEXT};
                font-size: 14px;
                font-weight: 650;
            }}
            """
        )

    # ========================================================
    # AUTO LOGIN
    # ========================================================

    def try_auto_login(self):

        saved_token = load_saved_token()

        saved_username = load_saved_username()

        if saved_username:

            self.username.setText(
                saved_username
            )

        if not saved_token:

            self.pages.setCurrentIndex(
                0
            )

            return

        self.token = saved_token

        self.current_username = (
            saved_username or ""
        )

        self.login_status.setText(
            "Восстановление сессии..."
        )

        self.load_devices(
            automatic=True
        )

    # ========================================================
    # LOGIN
    # ========================================================

    def login(self):

        username = (
            self.username
            .text()
            .strip()
        )

        password = (
            self.password
            .text()
        )

        if not username:

            QMessageBox.warning(
                self,
                "PinVPN",
                "Введите логин."
            )

            return

        if not password:

            QMessageBox.warning(
                self,
                "PinVPN",
                "Введите пароль."
            )

            return

        self.login_status.setText(
            "Авторизация..."
        )

        self.login_button.setEnabled(
            False
        )

        try:

            response = requests.post(

                f"{SERVER_URL}/api/client/login",

                json={
                    "username": username,
                    "password": password
                },

                timeout=20
            )

            if response.status_code != 200:

                raise Exception(
                    f"HTTP {response.status_code}\n"
                    f"{response.text}"
                )

            data = response.json()

            token = (
                data.get("token")
                or data.get("access_token")
            )

            if not token:

                raise Exception(
                    "Сервер не вернул токен."
                )

            self.token = token

            self.current_username = username

            save_login(
                token,
                username
            )

            self.load_devices(
                automatic=False
            )

        except Exception as error:

            self.token = None

            self.login_status.setText(
                "Ошибка входа"
            )

            QMessageBox.critical(
                self,
                "PinVPN",
                str(error)
            )

        finally:

            self.login_button.setEnabled(
                True
            )

    # ========================================================
    # LOAD DEVICES
    # ========================================================

    def load_devices(
        self,
        automatic=False
    ):

        if not self.token:

            return

        try:

            response = requests.get(

                f"{SERVER_URL}/api/client/devices",

                headers={
                    "Authorization":
                    f"Bearer {self.token}"
                },

                timeout=20
            )

            if response.status_code == 401:

                clear_saved_login()

                self.token = None

                self.pages.setCurrentIndex(
                    0
                )

                self.login_status.setText(
                    "Сессия истекла. "
                    "Войдите снова."
                )

                return

            if response.status_code != 200:

                raise Exception(
                    f"HTTP {response.status_code}\n"
                    f"{response.text}"
                )

            data = response.json()

            self.devices = data.get(
                "devices",
                []
            )

            self.device_box.clear()

            for device in self.devices:

                name = (
                    device.get("name")
                    or device.get("device_name")
                    or device.get("id")
                    or "Устройство"
                )

                self.device_box.addItem(
                    str(name),
                    device
                )

            if not self.devices:

                self.pages.setCurrentIndex(
                    1
                )

                self.connect_button.setEnabled(
                    False
                )

                self.info_label.setText(
                    "Нет доступных устройств"
                )

                return

            self.pages.setCurrentIndex(
                1
            )

            self.connect_button.setEnabled(
                True
            )

            self.account_button.setText(
                f"●  {self.current_username or 'Аккаунт'}"
            )

            self.refresh_service_status()

        except Exception as error:

            if automatic:

                self.token = None

                clear_saved_login()

                self.pages.setCurrentIndex(
                    0
                )

                self.login_status.setText(
                    "Не удалось восстановить "
                    "сессию. Войдите снова."
                )

                return

            QMessageBox.critical(
                self,
                "PinVPN",
                str(error)
            )

    # ========================================================
    # GET WIREGUARD
    # ========================================================

    def get_wireguard_config(
        self,
        device
    ):

        device_id = (
            device.get("id")
            or device.get("_id")
        )

        if not device_id:

            raise Exception(
                "Устройство не содержит ID."
            )

        response = requests.get(

            f"{SERVER_URL}/api/client/devices/"
            f"{device_id}/wireguard",

            headers={
                "Authorization":
                f"Bearer {self.token}"
            },

            timeout=30
        )

        if response.status_code != 200:

            raise Exception(
                "Не удалось получить "
                "WireGuard-конфигурацию.\n\n"
                f"HTTP {response.status_code}\n"
                f"{response.text}"
            )

        data = response.json()

        config = data.get(
            "wireguard_config"
        )

        if not config:

            raise Exception(
                "Сервер вернул пустую "
                "WireGuard-конфигурацию."
            )

        return config

    # ========================================================
    # SERVICE STATUS
    # ========================================================

    def refresh_service_status(self):

        try:

            response = service_request(
                "status"
            )

            self.service_label.setText(
                "●  Работает"
            )

            self.service_label.setStyleSheet(
                f"color: {GREEN};"
            )

            service_connected = bool(
                response.get(
                    "connected",
                    False
                )
            )

            self.connected = (
                service_connected
            )

            self.update_vpn_ui()

        except Exception:

            if hasattr(
                self,
                "service_label"
            ):

                self.service_label.setText(
                    "●  Недоступен"
                )

                self.service_label.setStyleSheet(
                    f"color: {RED};"
                )

            self.connected = False

            if hasattr(
                self,
                "connect_button"
            ):

                self.update_vpn_ui()

    # ========================================================
    # VPN UI
    # ========================================================

    def update_vpn_ui(self):

        if self.connected:

            self.status_label.setText(
                "ПОДКЛЮЧЕНО"
            )

            self.status_label.setStyleSheet(
                f"""
                color: {GREEN};
                font-size: 22px;
                font-weight: 800;
                """
            )

            self.status_hint.setText(
                "Ваше соединение защищено"
            )

            self.connect_button.setText(
                "ОТКЛЮЧИТЬ"
            )

            self.connect_button.setStyleSheet(
                f"""
                QPushButton#vpnButton {{
                    background: #111a17;
                    border: 5px solid {GREEN};
                    border-radius: 115px;
                    color: {GREEN};
                    font-size: 20px;
                    font-weight: 800;
                }}

                QPushButton#vpnButton:hover {{
                    background: #17251f;
                }}
                """
            )

            self.info_label.setText(
                "Защищённое соединение активно"
            )

            self.ipv6_value.setText(
                "Активен"
            )

            self.start_pulse()

        else:

            self.status_label.setText(
                "НЕ ПОДКЛЮЧЕНО"
            )

            self.status_label.setStyleSheet(
                f"""
                color: {MUTED};
                font-size: 22px;
                font-weight: 800;
                """
            )

            self.status_hint.setText(
                "Ваше соединение не защищено"
            )

            self.connect_button.setText(
                "ПОДКЛЮЧИТЬ"
            )

            self.connect_button.setStyleSheet(
                f"""
                QPushButton#vpnButton {{
                    background: #12151c;
                    border: 5px solid {PINK};
                    border-radius: 115px;
                    color: white;
                    font-size: 20px;
                    font-weight: 800;
                }}

                QPushButton#vpnButton:hover {{
                    background: #1a1e27;
                }}
                """
            )

            self.stop_pulse()

            if self.info_label.text() == "":
                self.info_label.setText(
                    "Выберите устройство и подключитесь к PinVPN"
                )

    # ========================================================
    # PULSE
    # ========================================================

    def start_pulse(self):

        if self.pulse_animation is not None:

            return

        self.pulse_animation = QPropertyAnimation(
            self.connect_button,
            b"minimumSize"
        )

        self.pulse_animation.setDuration(
            1200
        )

        self.pulse_animation.setStartValue(
            self.connect_button.minimumSize()
        )

        self.pulse_animation.setEndValue(
            self.connect_button.minimumSize()
        )

        self.pulse_animation.setEasingCurve(
            QEasingCurve.InOutSine
        )

        self.pulse_animation.setLoopCount(
            -1
        )

        self.pulse_animation.start()

    def stop_pulse(self):

        if self.pulse_animation:

            self.pulse_animation.stop()

            self.pulse_animation.deleteLater()

            self.pulse_animation = None

    # ========================================================
    # TOGGLE
    # ========================================================

    def toggle_vpn(self):

        if self.connected:

            self.disconnect_vpn()

        else:

            self.connect_vpn()

    # ========================================================
    # CONNECT
    # ========================================================

    def connect_vpn(self):

        if not self.token:

            QMessageBox.warning(
                self,
                "PinVPN",
                "Сначала войдите."
            )

            return

        device = (
            self.device_box.currentData()
        )

        if not device:

            QMessageBox.warning(
                self,
                "PinVPN",
                "Выберите устройство."
            )

            return

        self.connect_button.setEnabled(
            False
        )

        self.status_label.setText(
            "ПОДКЛЮЧЕНИЕ..."
        )

        self.status_label.setStyleSheet(
            f"""
            color: {PINK};
            font-size: 22px;
            font-weight: 800;
            """
        )

        self.status_hint.setText(
            "Устанавливаем защищённое соединение"
        )

        try:

            config = (
                self.get_wireguard_config(
                    device
                )
            )

            service_request(
                "connect",
                config=config
            )

            self.connected = True

            self.info_label.setText(
                "Защищённое соединение активно"
            )

            self.update_vpn_ui()

        except Exception as error:

            self.connected = False

            self.update_vpn_ui()

            QMessageBox.critical(
                self,
                "PinVPN",
                str(error)
            )

        finally:

            self.connect_button.setEnabled(
                True
            )

    # ========================================================
    # DISCONNECT
    # ========================================================

    def disconnect_vpn(self):

        self.connect_button.setEnabled(
            False
        )

        self.status_label.setText(
            "ОТКЛЮЧЕНИЕ..."
        )

        self.status_label.setStyleSheet(
            f"""
            color: {MUTED};
            font-size: 22px;
            font-weight: 800;
            """
        )

        try:

            service_request(
                "disconnect"
            )

            self.connected = False

            self.info_label.setText(
                "Соединение отключено"
            )

            self.update_vpn_ui()

        except Exception as error:

            QMessageBox.warning(
                self,
                "PinVPN",
                str(error)
            )

        finally:

            self.connect_button.setEnabled(
                True
            )

    # ========================================================
    # LOGOUT
    # ========================================================

    def logout(self):

        answer = QMessageBox.question(

            self,

            "PinVPN",

            (
                "Выйти из аккаунта?\n\n"
                "VPN-туннель при этом "
                "останется работать, "
                "если он сейчас подключён."
            ),

            QMessageBox.Yes
            | QMessageBox.No
        )

        if answer != QMessageBox.Yes:

            return

        clear_saved_login()

        self.token = None

        self.devices = []

        self.current_username = ""

        self.device_box.clear()

        self.pages.setCurrentIndex(
            0
        )

        self.password.clear()

        self.login_status.setText(
            ""
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        # VPN намеренно не отключаем.
        self.stop_pulse()

        event.accept()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "PinVPN"
    )

    app.setApplicationDisplayName(
        "PinVPN"
    )

    window = PinVPN()

    window.showMaximized()

    sys.exit(
        app.exec()
    )
