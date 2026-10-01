import sys
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

SERVER_URL = "https://pinnogram-server.onrender.com"


# ============================================================
# MAIN WINDOW
# ============================================================

class PinVPN(QWidget):

    def __init__(self):
        super().__init__()

        self.token = None
        self.devices = []

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
        layout.setContentsMargins(35, 35, 35, 35)

        # Logo
        title = QLabel("PinVPN")

        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet(
            """
            font-size: 34px;
            font-weight: bold;
            """
        )

        # Subtitle
        subtitle = QLabel("Secure VPN")

        subtitle.setAlignment(Qt.AlignCenter)

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

        # Login button
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

        # Connect button
        self.connect_button = QPushButton(
            "ПОДКЛЮЧИТЬ"
        )

        self.connect_button.setEnabled(
            False
        )

        self.connect_button.clicked.connect(
            self.connect_vpn
        )

        # Status
        self.status = QLabel(
            "Статус: Не подключено"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        # Add everything
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

                    "Сервер не вернул токен.",
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
    # VPN CONNECTION
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
            "Статус: Подготовка подключения..."
        )

        # ----------------------------------------------------
        # ВАЖНО:
        #
        # Настоящее WireGuard-подключение
        # добавим следующим этапом.
        # ----------------------------------------------------

        QMessageBox.information(

            self,

            "PinVPN",

            (
                "Авторизация работает.\n"
                "Устройство получено с сервера.\n\n"
                "Следующим шагом подключим "
                "настоящий WireGuard."
            ),
        )

        self.status.setText(
            "Статус: Готово к подключению"
        )


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
