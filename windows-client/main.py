import sys
import os
import json
import socket
import traceback
import keyring
from shiboken6 import isValid
import requests

from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QStackedWidget, QFrame,
    QSizePolicy, QGraphicsDropShadowEffect
)


SERVER_URL = "https://pinvpn.onrender.com"
SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 47811
SERVICE_TOKEN_FILE = r"C:\ProgramData\PinVPN\service.token"
BUILD_ID = "1.0.3 / 36bfe6b"
GUI_LOG_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PinVPN", "gui.log")

KEYRING_SERVICE = "PinVPN"
KEYRING_USERNAME = "client_token"

BG = "#07080c"
SIDEBAR = "#0b0d12"
CARD = "#10131a"
CARD_HOVER = "#151923"
BORDER = "#222733"
PINK = "#ff2f7d"
PINK_SOFT = "#ff5b98"
GREEN = "#65e6a1"
RED = "#ff5c7c"
WHITE = "#ffffff"
TEXT = "#e5e8ef"
MUTED = "#858c9c"
DIM = "#555d6d"


def write_gui_log(message):
    try:
        folder = os.path.dirname(GUI_LOG_FILE)
        os.makedirs(folder, exist_ok=True)
        with open(GUI_LOG_FILE, "a", encoding="utf-8") as file:
            file.write(message.rstrip() + "\n")
    except Exception:
        pass


def read_service_token():
    if not os.path.exists(SERVICE_TOKEN_FILE):
        raise Exception("PinVPN Service не установлена.")

    try:
        with open(SERVICE_TOKEN_FILE, "r", encoding="utf-8") as file:
            token = file.read().strip()
    except OSError as error:
        raise Exception(
            "Не удалось прочитать токен PinVPN Service.\n\n"
            f"{type(error).__name__}: {error}"
        )

    if not token:
        raise Exception("Токен PinVPN Service пуст.")

    return token


def service_request(action, config=None):
    try:
        token = read_service_token()
        payload = {"action": action, "token": token}

        if config is not None:
            payload["config"] = config

        message = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

        with socket.create_connection(
            (SERVICE_HOST, SERVICE_PORT),
            timeout=10,
        ) as sock:
            sock.settimeout(10)
            sock.sendall(message)

            data = b""

            while True:
                part = sock.recv(65536)

                if not part:
                    break

                data += part

                if b"\n" in part:
                    break

        if not data:
            raise Exception("PinVPN Service не ответила.")

        raw_response = data.decode("utf-8").strip()

        try:
            response = json.loads(raw_response)
        except json.JSONDecodeError as error:
            raise Exception(
                "PinVPN Service вернула некорректный ответ.\n\n"
                f"{type(error).__name__}: {error}\n"
                f"Ответ: {raw_response[:500]}"
            )

        if response.get("status") != "ok":
            raise Exception(
                response.get("error", "Ошибка PinVPN Service.")
            )

        return response

    except Exception as error:
        write_gui_log(
            "SERVICE REQUEST ERROR\n"
            f"Action: {action}\n"
            f"Type: {type(error).__name__}\n"
            f"Error: {error}\n"
            f"{traceback.format_exc()}"
        )
        raise


def save_login(token, username):
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
    keyring.set_password(KEYRING_SERVICE, "username", username)


def load_saved_token():
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)


def load_saved_username():
    return keyring.get_password(KEYRING_SERVICE, "username")


def clear_saved_login():
    for name in (KEYRING_USERNAME, "username"):
        try:
            keyring.delete_password(KEYRING_SERVICE, name)
        except Exception:
            pass


def add_shadow(widget, color="#000000", blur=32, y=8, opacity=140):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)
    return effect


class GlowButton(QPushButton):
    """Large animated PinVPN control button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.active = False
        self.hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(270, 270)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(35)
        self.setMouseTracking(True)

    def set_active(self, active):
        self.active = active
        self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def animate(self):
        self.phase = (self.phase + (0.035 if self.active else 0.02)) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        base = 103
        pulse = 4.0 * (0.5 + 0.5 * __import__("math").sin(self.phase * 6.283185))
        if not self.active:
            pulse *= 0.35
        radius = base + pulse

        glow_color = QColor(GREEN if self.active else PINK)
        glow_levels = ((24, 12, 24), (15, 24, 15), (7, 70, 5))
        for width, alpha, extra in glow_levels:
            color = QColor(glow_color)
            color.setAlpha(alpha)
            painter.setPen(QPen(color, width))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, int(radius + extra), int(radius + extra))

        if self.active:
            for extra, alpha in ((28, 18), (20, 28), (13, 42)):
                color = QColor(GREEN)
                color.setAlpha(alpha)
                painter.setPen(QPen(color, 3))
                painter.drawEllipse(center, int(radius + extra), int(radius + extra))

        gradient = QLinearGradient(0, 35, 0, 215)
        if self.active:
            gradient.setColorAt(0.0, QColor("#2cff9a"))
            gradient.setColorAt(0.38, QColor("#0fcf72"))
            gradient.setColorAt(1.0, QColor("#063b27"))
            ring = QColor("#7affbc")
        else:
            gradient.setColorAt(0.0, QColor("#171a22"))
            gradient.setColorAt(1.0, QColor("#0e1016"))
            ring = QColor(PINK)

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(ring, 6))
        painter.drawEllipse(center, int(radius), int(radius))

        if self.active:
            inner = QLinearGradient(0, 75, 0, 195)
            inner.setColorAt(0.0, QColor("#43ffab"))
            inner.setColorAt(1.0, QColor("#0a6f45"))
            painter.setBrush(QBrush(inner))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, int(radius - 13), int(radius - 13))

        icon_pen = QPen(QColor("#062417" if self.active else WHITE), 5)
        painter.setPen(icon_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(center.x() - 35, center.y() - 35, 70, 70, 35 * 16, 290 * 16)
        painter.drawLine(center.x(), center.y() - 39, center.x(), center.y() - 20)

        painter.setPen(QColor(GREEN if self.active else WHITE))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        text = "ОТКЛЮЧИТЬ" if self.active else "ПОДКЛЮЧИТЬ"
        painter.drawText(center.x() - 65, center.y() + 61, 130, 28, Qt.AlignCenter, text)


class PinVPN(QWidget):
    def __init__(self):
        super().__init__()

        self.token = None
        self.devices = []
        self.connected = False
        self.current_username = ""

        self.setWindowTitle("PinVPN")
        self.setMinimumSize(1000, 700)
        self.resize(1280, 800)

        self.build_ui()
        self.apply_style()

        self.service_timer = QTimer(self)
        self.service_timer.timeout.connect(self.refresh_service_status)
        self.service_timer.start(2500)

        self.try_auto_login()

    def make_card(self, object_name="card"):
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return frame

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_login_page())
        self.pages.addWidget(self.build_main_page())
        root.addWidget(self.pages)

    def build_login_page(self):
        page = QWidget()
        page.setObjectName("loginPage")

        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setAlignment(Qt.AlignCenter)

        shell = self.make_card("loginCard")
        shell.setMaximumWidth(500)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(54, 48, 54, 48)
        layout.setSpacing(14)

        logo = QLabel("PinVPN")
        logo.setObjectName("loginLogo")
        logo.setAlignment(Qt.AlignCenter)

        sub = QLabel("SECURE INTERNET")
        sub.setObjectName("loginSubtitle")
        sub.setAlignment(Qt.AlignCenter)

        line = QLabel("Защищённое соединение\nв одном нажатии")
        line.setObjectName("loginHeadline")
        line.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Имя пользователя")
        self.username.setMinimumHeight(52)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(52)
        self.password.returnPressed.connect(self.login)

        self.login_button = QPushButton("ВОЙТИ")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setMinimumHeight(54)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self.login)

        self.login_status = QLabel("")
        self.login_status.setObjectName("loginStatus")
        self.login_status.setAlignment(Qt.AlignCenter)
        self.login_status.setWordWrap(True)

        layout.addWidget(logo)
        layout.addWidget(sub)
        layout.addSpacing(22)
        layout.addWidget(line)
        layout.addSpacing(12)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addSpacing(8)
        layout.addWidget(self.login_button)
        layout.addWidget(self.login_status)

        outer.addWidget(shell)
        add_shadow(shell, blur=50, y=14, opacity=170)
        return page

    def build_main_page(self):
        page = QWidget()
        page.setObjectName("mainPage")

        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 28, 24, 24)
        side.setSpacing(10)

        logo = QLabel("PinVPN")
        logo.setObjectName("sideLogo")
        side.addWidget(logo)

        sub = QLabel("SECURE INTERNET")
        sub.setObjectName("sideSubtitle")
        side.addWidget(sub)
        side.addSpacing(32)

        active = QLabel("●   ПОДКЛЮЧЕНИЕ")
        active.setObjectName("sideActive")
        side.addWidget(active)

        side.addSpacing(8)
        side.addWidget(self.side_item("◌   УСТРОЙСТВА"))
        side.addWidget(self.side_item("◌   СЕТЬ"))
        side.addStretch()

        version = QLabel("PINVPN DESKTOP\nVERSION 1.0.3\nBUILD 36BFE6B")
        version.setObjectName("sideVersion")
        side.addWidget(version)

        content = QWidget()
        content.setObjectName("content")
        main = QVBoxLayout(content)
        main.setContentsMargins(30, 26, 30, 26)
        main.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Подключение")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Управление защищённым соединением")
        subtitle.setObjectName("pageSubtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.account_button = QPushButton("●  Аккаунт")
        self.account_button.setObjectName("accountButton")
        self.account_button.clicked.connect(self.logout)
        header.addWidget(self.account_button)
        main.addLayout(header)

        top = QHBoxLayout()
        top.setSpacing(16)

        device_card = self.make_card()
        dl = QVBoxLayout(device_card)
        dl.setContentsMargins(20, 16, 20, 16)
        dl.setSpacing(7)
        dl.addWidget(self.caption("УСТРОЙСТВО"))

        self.device_box = QComboBox()
        self.device_box.setMinimumHeight(44)
        dl.addWidget(self.device_box)
        top.addWidget(device_card, 2)

        service_card = self.make_card()
        sl = QVBoxLayout(service_card)
        sl.setContentsMargins(20, 16, 20, 16)
        sl.setSpacing(7)
        sl.addWidget(self.caption("PINVPN SERVICE"))

        self.service_label = QLabel("●  Проверка...")
        self.service_label.setObjectName("serviceValue")
        sl.addWidget(self.service_label)
        top.addWidget(service_card, 1)

        main.addLayout(top)

        center = self.make_card("vpnCard")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(28, 16, 28, 16)
        center_layout.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("НЕ ПОДКЛЮЧЕНО")
        self.status_label.setObjectName("mainStatus")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.status_hint = QLabel("Ваше соединение не защищено")
        self.status_hint.setObjectName("statusHint")
        self.status_hint.setAlignment(Qt.AlignCenter)

        self.connect_button = GlowButton()
        self.connect_button.clicked.connect(self.toggle_vpn)

        self.info_label = QLabel("Выберите устройство и подключитесь к PinVPN")
        self.info_label.setObjectName("centerInfo")
        self.info_label.setAlignment(Qt.AlignCenter)

        center_layout.addWidget(self.status_label)
        center_layout.addWidget(self.status_hint)
        center_layout.addSpacing(8)
        center_layout.addWidget(self.connect_button, alignment=Qt.AlignCenter)
        center_layout.addSpacing(7)
        center_layout.addWidget(self.info_label)

        main.addWidget(center, 1)
        add_shadow(center, blur=40, y=10, opacity=130)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        self.protocol_value = QLabel("WireGuard")
        bottom.addWidget(self.info_card("ПРОТОКОЛ", self.protocol_value))

        self.network_value = QLabel("IPv6")
        bottom.addWidget(self.info_card("СЕТЬ", self.network_value))

        self.ipv6_value = QLabel("Ожидание")
        bottom.addWidget(self.info_card("VPN IPv6", self.ipv6_value))

        root.addWidget(sidebar)
        root.addWidget(content, 1)
        return page

    def side_item(self, text):
        label = QLabel(text)
        label.setObjectName("sideItem")
        return label

    def caption(self, text):
        label = QLabel(text)
        label.setObjectName("smallTitle")
        return label

    def info_card(self, title, value):
        card = self.make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(4)
        layout.addWidget(self.caption(title))
        value.setObjectName("infoValue")
        layout.addWidget(value)
        return card

    def apply_style(self):
        self.setStyleSheet(f"""
        QWidget {{
            font-family: "Segoe UI";
            color: {TEXT};
        }}
        #loginPage, #mainPage, #content {{
            background: {BG};
        }}
        #sidebar {{
            background: {SIDEBAR};
            border-right: 1px solid {BORDER};
        }}
        #card, #loginCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 20px;
        }}
        #loginCard {{
            border-radius: 26px;
        }}
        #loginLogo, #sideLogo {{
            color: {WHITE};
            font-size: 34px;
            font-weight: 900;
        }}
        #loginSubtitle, #sideSubtitle {{
            color: {PINK};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 2px;
        }}
        #loginHeadline {{
            color: {TEXT};
            font-size: 20px;
            font-weight: 700;
            line-height: 1.3;
        }}
        QLineEdit {{
            background: #0c0f15;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 0 16px;
            color: {WHITE};
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 1px solid {PINK};
        }}
        #primaryButton {{
            background: {PINK};
            border: 0;
            border-radius: 12px;
            color: white;
            font-size: 13px;
            font-weight: 900;
        }}
        #primaryButton:hover {{
            background: {PINK_SOFT};
        }}
        #primaryButton:disabled {{
            background: #5a263d;
            color: #a88b98;
        }}
        #pageTitle {{
            color: {WHITE};
            font-size: 28px;
            font-weight: 850;
        }}
        #pageSubtitle, #statusHint {{
            color: {MUTED};
            font-size: 12px;
        }}
        #accountButton {{
            background: #11151d;
            border: 1px solid {BORDER};
            border-radius: 11px;
            padding: 9px 15px;
            color: {TEXT};
            font-weight: 700;
        }}
        #accountButton:hover {{
            background: {CARD_HOVER};
            border-color: #343a47;
        }}
        #smallTitle {{
            color: {DIM};
            font-size: 9px;
            font-weight: 900;
            letter-spacing: 1.4px;
        }}
        QComboBox {{
            background: #0c0f15;
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 0 12px;
            color: {TEXT};
            font-size: 13px;
        }}
        QComboBox:hover, QComboBox:focus {{
            border-color: #343a47;
        }}
        QComboBox QAbstractItemView {{
            background: #11151d;
            border: 1px solid {BORDER};
            selection-background-color: #252a35;
            color: {TEXT};
        }}
        #serviceValue {{
            color: {GREEN};
            font-size: 13px;
            font-weight: 750;
        }}
        #mainStatus {{
            color: {MUTED};
            font-size: 21px;
            font-weight: 900;
            letter-spacing: 1px;
        }}
        #centerInfo {{
            color: {MUTED};
            font-size: 11px;
        }}
        #infoValue {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 750;
        }}
        #sideActive {{
            background: #18111a;
            border: 1px solid #34202c;
            border-radius: 10px;
            padding: 12px 10px;
            color: {PINK};
            font-size: 11px;
            font-weight: 850;
        }}
        #sideItem {{
            padding: 11px 10px;
            color: {DIM};
            font-size: 11px;
            font-weight: 700;
        }}
        #sideVersion {{
            color: #454c59;
            font-size: 9px;
            line-height: 1.5;
        }}
        #loginStatus {{
            color: {RED};
            font-size: 11px;
        }}
        """)

    def try_auto_login(self):
        token = load_saved_token()
        username = load_saved_username()
        if not token:
            return

        self.token = token
        self.current_username = username or ""
        self.login_status.setText("Восстановление сессии...")
        self.load_devices(automatic=True)

    def login(self):
        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            self.login_status.setText("Введите имя пользователя и пароль.")
            return

        self.login_button.setEnabled(False)
        self.login_status.setText("Выполняется вход...")

        try:
            response = requests.post(
                f"{SERVER_URL}/api/client/login",
                json={"username": username, "password": password},
                timeout=20,
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}\n{response.text}")

            data = response.json()
            token = data.get("token") or data.get("access_token")
            if not token:
                raise Exception("Сервер не вернул токен.")

            self.token = token
            self.current_username = username
            save_login(token, username)
            self.load_devices(automatic=False)

        except Exception as error:
            self.token = None
            self.login_status.setText("Ошибка входа.")
            write_gui_log(
                "LOGIN ERROR\n"
                f"Type: {type(error).__name__}\n"
                f"Error: {error}\n"
                f"{traceback.format_exc()}"
            )
            QMessageBox.critical(self, "PinVPN", str(error))
        finally:
            self.login_button.setEnabled(True)

    def load_devices(self, automatic=False):
        if not self.token:
            return

        try:
            response = requests.get(
                f"{SERVER_URL}/api/client/devices",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=20,
            )

            if response.status_code == 401:
                clear_saved_login()
                self.token = None
                self.pages.setCurrentIndex(0)
                self.login_status.setText("Сессия истекла. Войдите снова.")
                return

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}\n{response.text}")

            data = response.json()
            self.devices = data.get("devices", [])

            self.device_box.clear()
            for device in self.devices:
                name = (
                    device.get("name")
                    or device.get("device_name")
                    or device.get("id")
                    or "Устройство"
                )
                self.device_box.addItem(str(name), device)

            self.pages.setCurrentIndex(1)
            self.connect_button.setEnabled(bool(self.devices))
            self.account_button.setText(
                f"●  {self.current_username or 'Аккаунт'}"
            )

            if not self.devices:
                self.info_label.setText("Нет доступных устройств")
            else:
                self.info_label.setText(
                    "Выберите устройство и подключитесь к PinVPN"
                )

            self.refresh_service_status()

        except Exception as error:
            write_gui_log(
                "LOAD DEVICES ERROR\n"
                f"Automatic: {automatic}\n"
                f"Type: {type(error).__name__}\n"
                f"Error: {error}\n"
                f"{traceback.format_exc()}"
            )
            if automatic:
                self.token = None
                clear_saved_login()
                self.pages.setCurrentIndex(0)
                self.login_status.setText(
                    "Не удалось восстановить сессию. Войдите снова."
                )
                return
            QMessageBox.critical(self, "PinVPN", str(error))

    def get_wireguard_config(self, device):
        device_id = device.get("id") or device.get("_id")
        if not device_id:
            raise Exception("Устройство не содержит ID.")

        response = requests.get(
            f"{SERVER_URL}/api/client/devices/{device_id}/wireguard",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(
                "Не удалось получить WireGuard-конфигурацию.\n\n"
                f"HTTP {response.status_code}\n{response.text}"
            )

        data = response.json()
        config = data.get("wireguard_config")
        if not config:
            raise Exception("Сервер вернул пустую WireGuard-конфигурацию.")
        return config

    def refresh_service_status(self):
        try:
            if not isValid(self) or not isValid(self.service_label):
                return
            if not isValid(self.info_label) or not isValid(self.connect_button):
                return
        except RuntimeError:
            return

        try:
            response = service_request("status")
            self.service_label.setText("●  Работает")
            self.service_label.setStyleSheet(f"color: {GREEN};")
            self.service_label.setToolTip("")
            self.connected = bool(response.get("connected", False))
            self.update_vpn_ui()

        except Exception as error:
            message = str(error).strip() or f"{type(error).__name__}"

            if isValid(self.service_label):
                self.service_label.setText("●  Ошибка")
                self.service_label.setStyleSheet(f"color: {RED};")
                self.service_label.setToolTip(message)

            if isValid(self.info_label):
                self.info_label.setText(
                    "Ошибка PinVPN Service. Наведите курсор на статус службы."
                )

            self.connected = False

            if isValid(self.connect_button):
                self.update_vpn_ui()

    def update_vpn_ui(self):
        try:
            if not isValid(self) or not isValid(self.status_label):
                return
            if not isValid(self.status_hint) or not isValid(self.connect_button):
                return
            if not isValid(self.ipv6_value) or not isValid(self.info_label):
                return
        except RuntimeError:
            return

        if self.connected:
            self.status_label.setText("ПОДКЛЮЧЕНО")
            self.status_label.setStyleSheet(
                f"color: {GREEN}; font-size: 21px; font-weight: 900; letter-spacing: 1px;"
            )
            self.status_hint.setText("Ваше соединение защищено")
            self.connect_button.set_active(True)
            self.ipv6_value.setText("Активен")
            self.info_label.setText("Защищённое соединение активно")
        else:
            self.status_label.setText("НЕ ПОДКЛЮЧЕНО")
            self.status_label.setStyleSheet(
                f"color: {MUTED}; font-size: 21px; font-weight: 900; letter-spacing: 1px;"
            )
            self.status_hint.setText("Ваше соединение не защищено")
            self.connect_button.set_active(False)
            self.ipv6_value.setText("Ожидание")
            if self.info_label.text() == "":
                self.info_label.setText(
                    "Выберите устройство и подключитесь к PinVPN"
                )

    def set_busy(self, busy, text):
        self.connect_button.setEnabled(not busy)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {PINK}; font-size: 21px; font-weight: 900; letter-spacing: 1px;"
        )

    def toggle_vpn(self):
        if self.connected:
            self.disconnect_vpn()
        else:
            self.connect_vpn()

    def connect_vpn(self):
        if not self.token:
            QMessageBox.warning(self, "PinVPN", "Сначала войдите.")
            return

        device = self.device_box.currentData()
        if not device:
            QMessageBox.warning(self, "PinVPN", "Выберите устройство.")
            return

        self.set_busy(True, "ПОДКЛЮЧЕНИЕ...")
        self.status_hint.setText("Устанавливаем защищённое соединение")

        try:
            config = self.get_wireguard_config(device)
            service_request("connect", config=config)
            self.connected = True
            self.info_label.setText("Защищённое соединение активно")
            self.update_vpn_ui()
        except Exception as error:
            self.connected = False
            self.update_vpn_ui()
            write_gui_log(
                "CONNECT ERROR\n"
                f"Type: {type(error).__name__}\n"
                f"Error: {error}\n"
                f"{traceback.format_exc()}"
            )
            QMessageBox.critical(self, "PinVPN", str(error))
        finally:
            self.connect_button.setEnabled(True)

    def disconnect_vpn(self):
        self.set_busy(True, "ОТКЛЮЧЕНИЕ...")
        self.status_hint.setText("Закрываем защищённое соединение")

        try:
            service_request("disconnect")
            self.connected = False
            self.info_label.setText("Соединение отключено")
            self.update_vpn_ui()
        except Exception as error:
            write_gui_log(
                "DISCONNECT ERROR\n"
                f"Type: {type(error).__name__}\n"
                f"Error: {error}\n"
                f"{traceback.format_exc()}"
            )
            QMessageBox.warning(self, "PinVPN", str(error))
        finally:
            self.connect_button.setEnabled(True)

    def logout(self):
        answer = QMessageBox.question(
            self,
            "PinVPN",
            "Выйти из аккаунта?\n\nVPN-туннель останется работать, если он подключён.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        clear_saved_login()
        self.token = None
        self.devices = []
        self.current_username = ""
        self.service_timer.stop()
        self.device_box.clear()
        self.pages.setCurrentIndex(0)
        self.password.clear()
        self.login_status.setText("")

    def closeEvent(self, event):
        if hasattr(self, "service_timer"):
            self.service_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PinVPN")
    app.setApplicationDisplayName("PinVPN")
    app.setStyle("Fusion")

    window = PinVPN()
    window.showMaximized()
    sys.exit(app.exec())
