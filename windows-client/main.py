import sys
import os
import subprocess
import tempfile
import ctypes
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
# WIREGUARD
# ============================================================

WIREGUARD_EXE = r"C:\Program Files\WireGuard\wireguard.exe"

WG_TEMP_CONFIG = os.path.join(
    tempfile.gettempdir(),
    "pinvpn.conf"
)


# ============================================================
# ADMINISTRATOR HELPER
# ============================================================

def run_as_admin(command):
    """
    Запускает команду через UAC Windows.
    """

    command_line = subprocess.list2cmdline(
        command
    )

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        command[0],
        command_line[
            len(command[0]) + 1:
        ],
        None,
        1,
    )

    if result <= 32:

        raise Exception(
            "Windows не смог предоставить "
            "права администратора."
        )

    return result


# ============================================================
# MAIN WINDOW
# ============================================================

class PinVPN(QWidget):

    def __init__(self):
        super().__init__()

        self.token = None
        self.devices = []

        self.connected = False
        self.current_config_path = None

        self.setWindowTitle("PinVPN")
        self.setFixedSize(420, 520)

        self.build_ui()
        self.apply_style()

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

        title = QLabel("PinVPN")

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setStyleSheet(
            """
            font-size: 34px;
            font-weight: bold;
            """
        )

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

        self.login_button.clicked.connect(
            self.login
        )

        device_label = QLabel(
            "Устройство:"
        )

        self.device_box = QComboBox()

        self.device_box.setEnabled(
            False
        )

        self.connect_button = QPushButton(
            "ПОДКЛЮЧИТЬ"
        )

        self.connect_button.setEnabled(
            False
        )

        self.connect_button.clicked.connect(
            self.toggle_vpn
        )

        self.status = QLabel(
            "Статус: Не подключено"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        layout.addWidget(
            self.username
        )

        layout.addWidget(
            self.password
        )

        layout.addWidget(
            self.login_button
        )

        layout.addSpacing(15)

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
    # LOGIN
    # ========================================================

    def login(self):

        username = self.username.text().strip()

        password = self.password.text()

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
                    or device.get("device_name")
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
    # TOGGLE VPN
    # ========================================================

    def toggle_vpn(self):

        if self.connected:

            self.disconnect_vpn()

        else:

            self.connect_vpn()

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
    # CONNECT VPN
    # ========================================================

    def connect_vpn(self):

        if not self.token:

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

            if not os.path.exists(
                WIREGUARD_EXE
            ):

                raise Exception(
                    "WireGuard не найден.\n\n"
                    f"{WIREGUARD_EXE}"
                )

            # Получаем конфигурацию
            config = self.get_wireguard_config(
                device
            )

            # Сохраняем её
            with open(
                WG_TEMP_CONFIG,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(config)

            self.current_config_path = (
                WG_TEMP_CONFIG
            )

            self.status.setText(
                "Статус: Ожидание разрешения Windows..."
            )

            # Запрашиваем права администратора
            run_as_admin(
                [
                    WIREGUARD_EXE,
                    "/installtunnelservice",
                    WG_TEMP_CONFIG,
                ]
            )

            self.connected = True

            self.status.setText(
                "Статус: 🟢 Подключено"
            )

            self.connect_button.setText(
                "ОТКЛЮЧИТЬ"
            )

        except Exception as error:

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

            run_as_admin(
                [
                    WIREGUARD_EXE,
                    "/uninstalltunnelservice",
                    "pinvpn",
                ]
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
    # CLOSE WINDOW
    # ========================================================

    def closeEvent(self, event):

        # Не отключаем VPN автоматически при
        # закрытии окна. VPN может продолжать
        # работать в фоновом режиме.

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
