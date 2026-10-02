import sys
import os
import json
import socket
import keyring
import requests

from PySide6.QtCore import Qt, QTimer
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
# PINVPN SERVICE
# ============================================================

def read_service_token():

    if not os.path.exists(
        SERVICE_TOKEN_FILE
    ):

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
# UI HELPERS
# ============================================================

def make_card():

    frame = QFrame()

    frame.setObjectName(
        "card"
    )

    return frame


# ============================================================
# MAIN WINDOW
# ============================================================

class PinVPN(QWidget):

    def __init__(self):

        super().__init__()

        self.token = None
        self.devices = []

        self.connected = False

        self.setWindowTitle(
            "PinVPN"
        )

        self.setMinimumSize(
            900,
            620
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
            2000
        )

        self.try_auto_login()

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        root = QVBoxLayout()

        root.setContentsMargins(
            40,
            35,
            40,
            30
        )

        root.setSpacing(
            25
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
    # LOGIN PAGE
    # ========================================================

    def build_login_page(self):

        page = QWidget()

        outer = QVBoxLayout()

        outer.setAlignment(
            Qt.AlignCenter
        )

        card = make_card()

        card.setMaximumWidth(
            480
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            45,
            45,
            45,
            45
        )

        layout.setSpacing(
            18
        )

        logo = QLabel(
            "PinVPN"
        )

        logo.setAlignment(
            Qt.AlignCenter
        )

        logo.setObjectName(
            "logo"
        )

        subtitle = QLabel(
            "Secure Internet"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setObjectName(
            "subtitle"
        )

        self.username = QLineEdit()

        self.username.setPlaceholderText(
            "Логин"
        )

        self.password = QLineEdit()

        self.password.setPlaceholderText(
            "Пароль"
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )

        self.login_button = QPushButton(
            "ВОЙТИ"
        )

        self.login_button.setMinimumHeight(
            52
        )

        self.login_button.clicked.connect(
            self.login
        )

        self.login_status = QLabel(
            ""
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
            25
        )

        layout.addWidget(
            self.username
        )

        layout.addWidget(
            self.password
        )

        layout.addSpacing(
            5
        )

        layout.addWidget(
            self.login_button
        )

        layout.addSpacing(
            10
        )

        layout.addWidget(
            self.login_status
        )

        card.setLayout(
            layout
        )

        outer.addWidget(
            card
        )

        page.setLayout(
            outer
        )

        return page

    # ========================================================
    # MAIN PAGE
    # ========================================================

    def build_main_page(self):

        page = QWidget()

        outer = QVBoxLayout()

        outer.setContentsMargins(
            30,
            10,
            30,
            10
        )

        outer.setSpacing(
            20
        )

        # Header
        header = QHBoxLayout()

        logo = QLabel(
            "PinVPN"
        )

        logo.setObjectName(
            "headerLogo"
        )

        account = QLabel(
            "Аккаунт"
        )

        account.setObjectName(
            "accountLabel"
        )

        self.logout_button = QPushButton(
            "ВЫЙТИ"
        )

        self.logout_button.setObjectName(
            "smallButton"
        )

        self.logout_button.clicked.connect(
            self.logout
        )

        header.addWidget(
            logo
        )

        header.addStretch()

        header.addWidget(
            account
        )

        header.addWidget(
            self.logout_button
        )

        outer.addLayout(
            header
        )

        # Content
        content = QHBoxLayout()

        content.setSpacing(
            25
        )

        # ----------------------------------------------------
        # Left card
        # ----------------------------------------------------

        left_card = make_card()

        left_layout = QVBoxLayout()

        left_layout.setContentsMargins(
            30,
            30,
            30,
            30
        )

        device_title = QLabel(
            "УСТРОЙСТВО"
        )

        device_title.setObjectName(
            "sectionTitle"
        )

        self.device_box = QComboBox()

        self.device_box.setMinimumHeight(
            48
        )

        left_layout.addWidget(
            device_title
        )

        left_layout.addSpacing(
            10
        )

        left_layout.addWidget(
            self.device_box
        )

        left_layout.addStretch()

        left_card.setLayout(
            left_layout
        )

        # ----------------------------------------------------
        # Center card
        # ----------------------------------------------------

        center_card = make_card()

        center_layout = QVBoxLayout()

        center_layout.setContentsMargins(
            30,
            30,
            30,
            30
        )

        center_layout.setAlignment(
            Qt.AlignCenter
        )

        self.status_label = QLabel(
            "НЕ ПОДКЛЮЧЕНО"
        )

        self.status_label.setObjectName(
            "vpnStatus"
        )

        self.connect_button = QPushButton(
            "ПОДКЛЮЧИТЬ"
        )

        self.connect_button.setObjectName(
            "vpnButton"
        )

        self.connect_button.setFixedSize(
            250,
            250
        )

        self.connect_button.clicked.connect(
            self.toggle_vpn
        )

        self.info_label = QLabel(
            "PinVPN"
        )

        self.info_label.setObjectName(
            "infoLabel"
        )

        center_layout.addStretch()

        center_layout.addWidget(
            self.status_label,
            alignment=Qt.AlignCenter
        )

        center_layout.addSpacing(
            25
        )

        center_layout.addWidget(
            self.connect_button,
            alignment=Qt.AlignCenter
        )

        center_layout.addSpacing(
            20
        )

        center_layout.addWidget(
            self.info_label,
            alignment=Qt.AlignCenter
        )

        center_layout.addStretch()

        center_card.setLayout(
            center_layout
        )

        # ----------------------------------------------------
        # Right card
        # ----------------------------------------------------

        right_card = make_card()

        right_layout = QVBoxLayout()

        right_layout.setContentsMargins(
            30,
            30,
            30,
            30
        )

        vpn_title = QLabel(
            "СОЕДИНЕНИЕ"
        )

        vpn_title.setObjectName(
            "sectionTitle"
        )

        self.service_label = QLabel(
            "Сервис: проверка..."
        )

        self.service_label.setObjectName(
            "infoRow"
        )

        self.protocol_label = QLabel(
            "Протокол: WireGuard"
        )

        self.protocol_label.setObjectName(
            "infoRow"
        )

        self.network_label = QLabel(
            "Сеть: IPv6"
        )

        self.network_label.setObjectName(
            "infoRow"
        )

        self.ipv4_label = QLabel(
            "IPv4: текущий"
        )

        self.ipv4_label.setObjectName(
            "infoRow"
        )

        self.ipv6_label = QLabel(
            "IPv6: PinVPN"
        )

        self.ipv6_label.setObjectName(
            "infoRow"
        )

        right_layout.addWidget(
            vpn_title
        )

        right_layout.addSpacing(
            20
        )

        right_layout.addWidget(
            self.service_label
        )

        right_layout.addSpacing(
            12
        )

        right_layout.addWidget(
            self.protocol_label
        )

        right_layout.addSpacing(
            12
        )

        right_layout.addWidget(
            self.network_label
        )

        right_layout.addSpacing(
            12
        )

        right_layout.addWidget(
            self.ipv4_label
        )

        right_layout.addSpacing(
            12
        )

        right_layout.addWidget(
            self.ipv6_label
        )

        right_layout.addStretch()

        right_card.setLayout(
            right_layout
        )

        content.addWidget(
            left_card,
            1
        )

        content.addWidget(
            center_card,
            2
        )

        content.addWidget(
            right_card,
            1
        )

        outer.addLayout(
            content
        )

        page.setLayout(
            outer
        )

        self.main_page = page

        return page

    # ========================================================
    # STYLE
    # ========================================================

    def apply_style(self):

        self.setStyleSheet(
            """
            QWidget {
                background: #0a0b0f;
                color: #ffffff;
                font-size: 15px;
            }

            QFrame#card {
                background: #12141a;
                border: 1px solid #242731;
                border-radius: 22px;
            }

            QLabel#logo {
                font-size: 52px;
                font-weight: 800;
                color: #ff2f7d;
            }

            QLabel#subtitle {
                color: #8e94a3;
                font-size: 16px;
            }

            QLabel#headerLogo {
                font-size: 34px;
                font-weight: 800;
                color: #ff2f7d;
            }

            QLabel#accountLabel {
                color: #9ca2b1;
                font-size: 14px;
            }

            QLabel#sectionTitle {
                color: #8e94a3;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;
            }

            QLabel#vpnStatus {
                font-size: 21px;
                font-weight: 700;
                color: #aeb4c3;
            }

            QLabel#infoLabel {
                color: #777d8c;
                font-size: 13px;
            }

            QLabel#infoRow {
                color: #c2c7d2;
                font-size: 14px;
            }

            QLineEdit,
            QComboBox {
                background: #1a1d25;
                border: 1px solid #2d313c;
                border-radius: 12px;
                padding: 13px;
                color: white;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 1px solid #ff2f7d;
            }

            QPushButton {
                background: #ff2f7d;
                border: none;
                border-radius: 12px;
                padding: 13px;
                color: white;
                font-weight: 800;
            }

            QPushButton:hover {
                background: #ff438b;
            }

            QPushButton:pressed {
                background: #db1f66;
            }

            QPushButton:disabled {
                background: #30333c;
                color: #777;
            }

            QPushButton#smallButton {
                background: #1b1e26;
                border: 1px solid #303440;
                padding: 8px 15px;
            }

            QPushButton#smallButton:hover {
                background: #252935;
            }

            QPushButton#vpnButton {
                background: #1b1e26;
                border: 5px solid #ff2f7d;
                border-radius: 125px;
                font-size: 22px;
                font-weight: 800;
            }

            QPushButton#vpnButton:hover {
                background: #232630;
            }
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

            self.status_label = getattr(
                self,
                "status_label",
                None
            )

            return

        self.token = saved_token

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

                    or device.get(
                        "device_name"
                    )

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
    # GET WIREGUARD CONFIG
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
                "Сервис: ● работает"
            )

            self.service_label.setStyleSheet(
                "color: #65e6a1;"
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
                    "Сервис: ● недоступен"
                )

                self.service_label.setStyleSheet(
                    "color: #ff5c7c;"
                )

            self.connected = False

    # ========================================================
    # VPN UI
    # ========================================================

    def update_vpn_ui(self):

        if self.connected:

            self.status_label.setText(
                "ПОДКЛЮЧЕНО"
            )

            self.status_label.setStyleSheet(
                "color: #65e6a1;"
                "font-size: 21px;"
                "font-weight: 700;"
            )

            self.connect_button.setText(
                "ОТКЛЮЧИТЬ"
            )

            self.connect_button.setStyleSheet(
                """
                QPushButton#vpnButton {
                    background: #151f1c;
                    border: 5px solid #65e6a1;
                    border-radius: 125px;
                    color: #65e6a1;
                    font-size: 22px;
                    font-weight: 800;
                }

                QPushButton#vpnButton:hover {
                    background: #1e2d28;
                }
                """
            )

        else:

            self.status_label.setText(
                "НЕ ПОДКЛЮЧЕНО"
            )

            self.status_label.setStyleSheet(
                "color: #aeb4c3;"
                "font-size: 21px;"
                "font-weight: 700;"
            )

            self.connect_button.setText(
                "ПОДКЛЮЧИТЬ"
            )

            self.connect_button.setStyleSheet(
                """
                QPushButton#vpnButton {
                    background: #1b1e26;
                    border: 5px solid #ff2f7d;
                    border-radius: 125px;
                    color: white;
                    font-size: 22px;
                    font-weight: 800;
                }

                QPushButton#vpnButton:hover {
                    background: #232630;
                }
                """
            )

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

        # VPN не отключаем.
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

    window = PinVPN()

    window.showMaximized()

    sys.exit(
        app.exec()
    )
