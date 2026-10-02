import sys
import os
import json
import socket
import requests

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
)


# ============================================================
# PINVPN SERVER
# ============================================================

SERVER_URL = "https://pinvpn.onrender.com"


# ============================================================
# LOCAL PINVPN SERVICE
# ============================================================

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 47811

SERVICE_TOKEN_FILE = r"C:\ProgramData\PinVPN\service.token"


# ============================================================
# LOCAL SERVICE COMMUNICATION
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
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    try:

        with socket.create_connection(
            (
                SERVICE_HOST,
                SERVICE_PORT,
            ),
            timeout=10,
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
            "Не удалось связаться "
            "с PinVPN Service.\n\n"
            f"{error}"
        )

    if not data:

        raise Exception(
            "PinVPN Service не вернула ответ."
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
                "Неизвестная ошибка PinVPN Service."
            )
        )

    return response


# ============================================================
# MAIN WINDOW
# ============================================================

class PinVPN(QWidget):

    def __init__(self):

        super().__init__()

        self.token = None
        self.devices = []

        self.connected = False

        self.setWindowTitle("PinVPN")
        self.setFixedSize(420, 520)

        self.build_ui()
        self.apply_style()

        self.check_service()

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        layout = QVBoxLayout()

        layout.setSpacing(14)
        layout.setContentsMargins(
            35,
            35,
            35,
            35
        )

        # Logo
        title = QLabel(
            "PinVPN"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setStyleSheet(
            """
            font-size: 34px;
            font-weight: bold;
            """
        )

        # Subtitle
        subtitle = QLabel(
            "Secure VPN"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setStyleSheet(
            """
            color: #9ca0aa;
            font-size: 14px;
            """
        )

        # Username
        self.username = QLineEdit()

        self.username.setPlaceholderText(
            "Логин"
        )

        # Password
        self.password = QLineEdit()

        self.password.setPlaceholderText(
            "Пароль"
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )

        # Login
        self.login_button = QPushButton(
            "ВОЙТИ"
        )

        self.login_button.clicked.connect(
            self.login
        )

        # Device label
        device_label = QLabel(
            "Устройство:"
        )

        # Device selector
        self.device_box = QComboBox()

        self.device_box.setEnabled(
            False
        )

        # Connect
        self.connect_button = QPushButton(
            "ПОДКЛЮЧИТЬ"
        )

        self.connect_button.setEnabled(
            False
        )

        self.connect_button.clicked.connect(
            self.toggle_vpn
        )

        # Status
        self.status = QLabel(
            "Статус: Проверка..."
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        # Layout
        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            20
        )

        layout.addWidget(
            self.username
        )

        layout.addWidget(
            self.password
        )

        layout.addWidget(
            self.login_button
        )

        layout.addSpacing(
            15
        )

        layout.addWidget(
            device_label
        )

        layout.addWidget(
            self.device_box
        )

        layout.addWidget(
            self.connect_button
        )

        layout.addStretch()

        layout.addWidget(
            self.status
        )

        self.setLayout(
            layout
        )

    # ========================================================
    # STYLE
    # ========================================================

    def apply_style(self):

        self.setStyleSheet(
            """
            QWidget {
                background: #101114;
                color: white;
                font-size: 14px;
            }

            QLineEdit,
            QComboBox {

                background: #1a1c22;

                border: 1px solid #30333b;

                border-radius: 9px;

                padding: 11px;

                color: white;
            }

            QLineEdit:focus,
            QComboBox:focus {

                border: 1px solid #e91e63;
            }

            QPushButton {

                background: #e91e63;

                border: none;

                border-radius: 9px;

                padding: 12px;

                color: white;

                font-weight: bold;
            }

            QPushButton:hover {

                background: #f22970;
            }

            QPushButton:pressed {

                background: #c91652;
            }

            QPushButton:disabled {

                background: #35373e;

                color: #888;
            }

            QLabel {
                background: transparent;
            }
            """
        )

    # ========================================================
    # SERVICE CHECK
    # ========================================================

    def check_service(self):

        try:

            response = service_request(
                "status"
            )

            self.connected = bool(
                response.get(
                    "connected",
                    False
                )
            )

            if self.connected:

                self.status.setText(
                    "Статус: 🟢 Подключено"
                )

                self.connect_button.setText(
                    "ОТКЛЮЧИТЬ"
                )

            else:

                self.status.setText(
                    "Статус: Не подключено"
                )

        except Exception:

            self.connected = False

            self.status.setText(
                "Статус: Служба PinVPN недоступна"
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

        self.status.setText(
            "Статус: Авторизация..."
        )

        self.login_button.setEnabled(
            False
        )

        try:

            response = requests.post(

                f"{SERVER_URL}/api/client/login",

                json={
                    "username": username,
                    "password": password,
                },

                timeout=20,
            )

            if response.status_code != 200:

                QMessageBox.warning(

                    self,

                    "Ошибка входа",

                    (
                        f"Сервер вернул "
                        f"{response.status_code}\n\n"
                        f"{response.text}"
                    ),
                )

                self.status.setText(
                    "Статус: Не подключено"
                )

                return

            data = response.json()

            self.token = (
                data.get("token")
                or data.get("access_token")
            )

            if not self.token:

                QMessageBox.warning(

                    self,

                    "Ошибка",

                    "Сервер не вернул токен."
                )

                self.status.setText(
                    "Статус: Ошибка"
                )

                return

            self.load_devices()

        except requests.RequestException as error:

            QMessageBox.critical(

                self,

                "Ошибка соединения",

                (
                    "Не удалось связаться "
                    "с сервером:\n\n"
                    f"{error}"
                ),
            )

            self.status.setText(
                "Статус: Ошибка"
            )

        finally:

            self.login_button.setEnabled(
                True
            )

    # ========================================================
    # LOAD DEVICES
    # ========================================================

    def load_devices(self):

        try:

            response = requests.get(

                f"{SERVER_URL}/api/client/devices",

                headers={
                    "Authorization":
                    f"Bearer {self.token}"
                },

                timeout=20,
            )

            if response.status_code != 200:

                QMessageBox.warning(

                    self,

                    "Ошибка",

                    (
                        "Не удалось получить "
                        "устройства.\n\n"
                        f"HTTP {response.status_code}\n"
                        f"{response.text}"
                    ),
                )

                return

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

            has_devices = bool(
                self.devices
            )

            self.device_box.setEnabled(
                has_devices
            )

            self.connect_button.setEnabled(
                has_devices
            )

            if has_devices:

                self.check_service()

                if not self.connected:

                    self.status.setText(
                        "Статус: Готово к подключению"
                    )

            else:

                self.status.setText(
                    "Статус: Нет устройств"
                )

                QMessageBox.information(

                    self,

                    "PinVPN",

                    (
                        "У вашего аккаунта "
                        "пока нет устройств."
                    ),
                )

        except requests.RequestException as error:

            QMessageBox.critical(

                self,

                "Ошибка",

                (
                    "Не удалось получить "
                    "список устройств:\n\n"
                    f"{error}"
                ),
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
                "У выбранного устройства "
                "отсутствует ID."
            )

        response = requests.get(

            f"{SERVER_URL}/api/client/devices/"
            f"{device_id}/wireguard",

            headers={
                "Authorization":
                f"Bearer {self.token}"
            },

            timeout=30,
        )

        if response.status_code != 200:

            raise Exception(

                "Сервер не смог вернуть "
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
                "Сервер не вернул "
                "WireGuard-конфигурацию."
            )

        return config

    # ========================================================
    # TOGGLE VPN
    # ========================================================

    def toggle_vpn(self):

        if self.connected:

            self.disconnect_vpn()

        else:

            self.connect_vpn()

    # ========================================================
    # CONNECT VPN
    # ========================================================

    def connect_vpn(self):

        if not self.token:

            QMessageBox.warning(
                self,
                "PinVPN",
                "Сначала войдите в аккаунт."
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

        self.status.setText(
            "Статус: Получение конфигурации..."
        )

        self.connect_button.setEnabled(
            False
        )

        try:

            # Получаем конфигурацию
            # непосредственно с PinVPN-сервера.
            config = (
                self.get_wireguard_config(
                    device
                )
            )

            self.status.setText(
                "Статус: Подключение..."
            )

            # Передаём конфигурацию
            # привилегированной службе.
            response = service_request(
                "connect",
                config=config
            )

            if not response.get(
                "connected",
                False
            ):

                raise Exception(
                    "PinVPN Service не "
                    "подтвердила подключение."
                )

            self.connected = True

            self.status.setText(
                "Статус: 🟢 Подключено"
            )

            self.connect_button.setText(
                "ОТКЛЮЧИТЬ"
            )

        except Exception as error:

            self.connected = False

            self.status.setText(
                "Статус: Ошибка подключения"
            )

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
    # DISCONNECT VPN
    # ========================================================

    def disconnect_vpn(self):

        self.status.setText(
            "Статус: Отключение..."
        )

        self.connect_button.setEnabled(
            False
        )

        try:

            service_request(
                "disconnect"
            )

            self.connected = False

            self.status.setText(
                "Статус: 🔴 Не подключено"
            )

            self.connect_button.setText(
                "ПОДКЛЮЧИТЬ"
            )

        except Exception as error:

            QMessageBox.warning(

                self,

                "PinVPN",

                (
                    "Не удалось отключить VPN:\n\n"
                    f"{error}"
                ),
            )

        finally:

            self.connect_button.setEnabled(
                True
            )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        # VPN специально НЕ отключаем.
        # Системная служба продолжает
        # держать туннель активным.

        event.accept()


# ============================================================
# APPLICATION
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    window = PinVPN()

    window.show()

    sys.exit(
        app.exec()
    )
