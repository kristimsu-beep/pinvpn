import sys
import os
import json
import socket
import traceback
import math
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
BUILD_ID = "1.0.4 / 3DCORE"
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
    """Premium 3D animated PinVPN core button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.active = False
        self.busy = False
        self.hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(310, 310)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)
        self.setMouseTracking(True)

    def set_active(self, active):
        self.active = active
        self.update()

    def set_busy(self, busy):
        self.busy = busy
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
        speed = 0.045 if self.active else 0.028
        if self.busy:
            speed = 0.075
        self.phase = (self.phase + speed) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        cx, cy = center.x(), center.y()
        pulse = math.sin(self.phase * math.tau)
        hover_lift = 4 if self.hovered and not self.busy else 0
        depth = 13 if not self.hovered else 9
        base = 108 + (2.5 * pulse if self.active or self.busy else 0)
        if self.busy:
            base += 2

        accent = QColor(GREEN if self.active else PINK)
        if self.busy:
            accent = QColor(PINK_SOFT)

        # Атмосферное неоновое свечение.
        for radius, alpha, width in (
            (base + 42, 10, 18),
            (base + 31, 18, 13),
            (base + 21, 30, 8),
        ):
            color = QColor(accent)
            color.setAlpha(alpha)
            painter.setPen(QPen(color, width))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, int(radius), int(radius))

        # Вращающееся энергетическое кольцо.
        ring_alpha = 80 + int(35 * (0.5 + 0.5 * pulse))
        ring_color = QColor(accent.red(), accent.green(), accent.blue(), ring_alpha)
        painter.setPen(QPen(ring_color, 2))
        painter.setBrush(Qt.NoBrush)
        ring_r = int(base + 25)
        painter.drawArc(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2,
                        int(self.phase * 360 * 16), 230 * 16)
        painter.drawArc(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2,
                        int(self.phase * 360 * 16 + 250 * 16), 65 * 16)

        # Нижняя часть корпуса — создаёт настоящий 3-D эффект.
        shadow_gradient = QLinearGradient(0, cy - base, 0, cy + base + depth)
        shadow_gradient.setColorAt(0.0, QColor("#0b0d12"))
        shadow_gradient.setColorAt(0.72, QColor("#050609"))
        shadow_gradient.setColorAt(1.0, QColor("#020305"))
        painter.setBrush(QBrush(shadow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - int(base), cy - int(base) + depth,
                            int(base * 2), int(base * 2))

        # Основная глянцевая сфера.
        top_offset = -hover_lift
        sphere_gradient = QLinearGradient(
            0, cy - base + top_offset,
            0, cy + base + top_offset
        )

        if self.active:
            sphere_gradient.setColorAt(0.0, QColor("#63ffc0"))
            sphere_gradient.setColorAt(0.18, QColor("#1df28d"))
            sphere_gradient.setColorAt(0.55, QColor("#0aa85d"))
            sphere_gradient.setColorAt(0.82, QColor("#075033"))
            sphere_gradient.setColorAt(1.0, QColor("#021a10"))
            edge = QColor("#8affc9")
        else:
            sphere_gradient.setColorAt(0.0, QColor("#343946"))
            sphere_gradient.setColorAt(0.18, QColor("#1d202a"))
            sphere_gradient.setColorAt(0.58, QColor("#10131b"))
            sphere_gradient.setColorAt(0.86, QColor("#090b10"))
            sphere_gradient.setColorAt(1.0, QColor("#030406"))
            edge = QColor(PINK_SOFT)

        sx, sy = cx, cy + top_offset
        painter.setBrush(QBrush(sphere_gradient))
        painter.setPen(QPen(edge, 5))
        painter.drawEllipse(sx - int(base), sy - int(base),
                            int(base * 2), int(base * 2))

        # Внутренний фасочный контур.
        inner_r = int(base - 15)
        inner_color = QColor(accent)
        inner_color.setAlpha(115)
        painter.setPen(QPen(inner_color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(sx - inner_r, sy - inner_r, inner_r * 2, inner_r * 2)

        # Блик сверху.
        highlight = QLinearGradient(0, sy - base, 0, sy - 5)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 115))
        highlight.setColorAt(0.28, QColor(255, 255, 255, 35))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            sx - int(base - 9),
            sy - int(base - 9),
            int((base - 9) * 2),
            int(base * 0.88)
        )

        # Центральная кнопка.
        plate_r = 63
        plate_gradient = QLinearGradient(0, sy - plate_r, 0, sy + plate_r)
        if self.active:
            plate_gradient.setColorAt(0.0, QColor("#b9ffe0"))
            plate_gradient.setColorAt(0.35, QColor("#3effa7"))
            plate_gradient.setColorAt(1.0, QColor("#0b7449"))
            plate_edge = QColor("#d7ffea")
            icon_color = QColor("#042519")
        else:
            plate_gradient.setColorAt(0.0, QColor("#292d38"))
            plate_gradient.setColorAt(1.0, QColor("#0c0f15"))
            plate_edge = QColor("#555d6d")
            icon_color = QColor(WHITE)

        painter.setBrush(QBrush(plate_gradient))
        painter.setPen(QPen(plate_edge, 3))
        painter.drawEllipse(sx - plate_r, sy - plate_r, plate_r * 2, plate_r * 2)

        # Кнопка питания.
        painter.setPen(QPen(icon_color, 6, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(cx - 28, sy - 28, 56, 56, 35 * 16, 290 * 16)
        painter.drawLine(cx, sy - 34, cx, sy - 12)

        painter.setPen(QColor("#042519" if self.active else WHITE))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        if self.busy:
            text = "ПОДОЖДИТЕ"
        elif self.active:
            text = "ОТКЛЮЧИТЬ"
        else:
            text = "ПОДКЛЮЧИТЬ"
        painter.drawText(cx - 78, sy + 88, 156, 26, Qt.AlignCenter, text)

        state_color = QColor(GREEN if self.active else PINK)
        if self.busy:
            state_color = QColor(PINK_SOFT)
        painter.setBrush(state_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - 4, sy + 112, 8, 8)


class PinVPN(QWidget):
    def __init__(self):
        super().__init__()

        self.token = None
        self.devices = []
        self.connected = False
        self.busy = False
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
        sidebar.setFixedWidth(250)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 28, 24, 24)
        side.setSpacing(8)

        logo = QLabel("PinVPN")
        logo.setObjectName("sideLogo")
        side.addWidget(logo)

        sub = QLabel("SECURE INTERNET")
        sub.setObjectName("sideSubtitle")
        side.addWidget(sub)
        side.addSpacing(30)

        active = QLabel("●   ПОДКЛЮЧЕНИЕ")
        active.setObjectName("sideActive")
        side.addWidget(active)

        side.addSpacing(7)
        side.addWidget(self.side_item("◌   УСТРОЙСТВА"))
        side.addWidget(self.side_item("◌   СЕТЬ"))
        side.addStretch()

        security = QLabel("●  ЗАЩИЩЕНО")
        security.setObjectName("sideSecurity")
        side.addWidget(security)

        version = QLabel("PINVPN DESKTOP\nVERSION 1.0.4\nBUILD 3DCORE")
        version.setObjectName("sideVersion")
        side.addWidget(version)

        content = QWidget()
        content.setObjectName("content")
        main = QVBoxLayout(content)
        main.setContentsMargins(34, 28, 34, 26)
        main.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("Подключение")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Ваш защищённый туннель в реальном времени")
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
        top.setSpacing(14)

        device_card = self.make_card()
        dl = QVBoxLayout(device_card)
        dl.setContentsMargins(20, 14, 20, 14)
        dl.setSpacing(6)
        dl.addWidget(self.caption("УСТРОЙСТВО"))
        self.device_box = QComboBox()
        self.device_box.setMinimumHeight(42)
        dl.addWidget(self.device_box)
        top.addWidget(device_card, 2)

        service_card = self.make_card()
        sl = QVBoxLayout(service_card)
        sl.setContentsMargins(20, 14, 20, 14)
        sl.setSpacing(6)
        sl.addWidget(self.caption("PINVPN SERVICE"))
        self.service_label = QLabel("●  Проверка...")
        self.service_label.setObjectName("serviceValue")
        sl.addWidget(self.service_label)
        top.addWidget(service_card, 1)

        state_card = self.make_card()
        st = QVBoxLayout(state_card)
        st.setContentsMargins(20, 14, 20, 14)
        st.setSpacing(6)
        st.addWidget(self.caption("ЗАЩИТА"))
        self.state_chip = QLabel("НЕ АКТИВНА")
        self.state_chip.setObjectName("stateChip")
        st.addWidget(self.state_chip)
        top.addWidget(state_card, 1)

        main.addLayout(top)

        center = self.make_card("vpnCard")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(28, 8, 28, 8)
        center_layout.setSpacing(0)
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
        center_layout.addWidget(self.connect_button, alignment=Qt.AlignCenter)
        center_layout.addWidget(self.info_label)

        main.addWidget(center, 1)
        add_shadow(center, blur=46, y=12, opacity=150)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)

        self.protocol_value = QLabel("WireGuard")
        bottom.addWidget(self.info_card("ПРОТОКОЛ", self.protocol_value))

        self.network_value = QLabel("IPv6")
        bottom.addWidget(self.info_card("СЕТЬ", self.network_value))

        self.ipv6_value = QLabel("Ожидание")
        bottom.addWidget(self.info_card("VPN IPv6", self.ipv6_value))

        self.ping_value = QLabel("—")
        bottom.addWidget(self.info_card("ЗАДЕРЖКА", self.ping_value))

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
        #loginPage {{
            background: qradialgradient(cx:0.5, cy:0.25, radius:1.0,
                stop:0 #17111a, stop:0.42 #0b0b10, stop:1 #050609);
        }}
        #mainPage, #content {{
            background: qradialgradient(cx:0.45, cy:0.42, radius:1.0,
                stop:0 #15111a, stop:0.34 #0b0d13, stop:1 #06070a);
        }}
        #sidebar {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #090a0f, stop:1 #0d0f15);
            border-right: 1px solid #20242d;
        }}
        #card, #loginCard {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #141720, stop:1 #0d1016);
            border: 1px solid #252a35;
            border-radius: 18px;
        }}
        #loginCard {{ border-radius: 26px; }}
        #vpnCard {{
            background: qradialgradient(cx:0.5, cy:0.44, radius:0.72,
                stop:0 #17131d, stop:0.45 #10121a, stop:1 #0a0c11);
            border: 1px solid #2a2e3a;
            border-radius: 28px;
        }}
        #loginLogo, #sideLogo {{
            color: {WHITE};
            font-size: 34px;
            font-weight: 900;
        }}
        #sideLogo {{ font-size: 31px; }}
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
        }}
        QLineEdit {{
            background: #0a0d12;
            border: 1px solid #262b36;
            border-radius: 12px;
            padding: 0 16px;
            color: {WHITE};
            font-size: 14px;
        }}
        QLineEdit:focus {{ border: 1px solid {PINK}; }}
        #primaryButton {{
            background: {PINK};
            border: 0;
            border-radius: 12px;
            color: white;
            font-size: 13px;
            font-weight: 900;
        }}
        #primaryButton:hover {{ background: {PINK_SOFT}; }}
        #primaryButton:disabled {{ background: #5a263d; color: #a88b98; }}
        #pageTitle {{
            color: {WHITE};
            font-size: 29px;
            font-weight: 900;
        }}
        #pageSubtitle, #statusHint {{
            color: #8f96a6;
            font-size: 12px;
        }}
        #accountButton {{
            background: #11151d;
            border: 1px solid #292e39;
            border-radius: 12px;
            padding: 10px 16px;
            color: {TEXT};
            font-weight: 750;
        }}
        #accountButton:hover {{ background: #171b24; border-color: #414754; }}
        #smallTitle {{
            color: #626a7a;
            font-size: 9px;
            font-weight: 900;
            letter-spacing: 1.5px;
        }}
        QComboBox {{
            background: #0b0e14;
            border: 1px solid #272c37;
            border-radius: 10px;
            padding: 0 12px;
            color: {TEXT};
            font-size: 13px;
        }}
        QComboBox:hover, QComboBox:focus {{ border-color: #444a58; }}
        QComboBox QAbstractItemView {{
            background: #11151d;
            border: 1px solid #303642;
            selection-background-color: #272d38;
            color: {TEXT};
        }}
        #serviceValue {{
            color: {GREEN};
            font-size: 13px;
            font-weight: 800;
        }}
        #stateChip {{
            color: {PINK};
            font-size: 12px;
            font-weight: 900;
        }}
        #mainStatus {{
            color: #aeb4c0;
            font-size: 23px;
            font-weight: 900;
            letter-spacing: 1.5px;
        }}
        #centerInfo {{
            color: #767e8e;
            font-size: 11px;
        }}
        #infoValue {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 800;
        }}
        #sideActive {{
            background: #19101a;
            border: 1px solid #3a2130;
            border-radius: 10px;
            padding: 12px 10px;
            color: {PINK};
            font-size: 11px;
            font-weight: 850;
        }}
        #sideItem {{
            padding: 11px 10px;
            color: #5f6776;
            font-size: 11px;
            font-weight: 750;
        }}
        #sideItem:hover {{ color: #aab0bc; }}
        #sideSecurity {{
            background: #0d1713;
            border: 1px solid #173c2b;
            border-radius: 10px;
            padding: 10px;
            color: {GREEN};
            font-size: 10px;
            font-weight: 850;
        }}
        #sideVersion {{
            color: #454c59;
            font-size: 9px;
            line-height: 1.5;
        }}
        #loginStatus {{ color: {RED}; font-size: 11px; }}
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
            self.connect_button.set_busy(False)
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

        if self.busy:
            return

        if self.connected:
            self.status_label.setText("ПОДКЛЮЧЕНО")
            self.status_label.setStyleSheet(
                f"color: {GREEN}; font-size: 23px; font-weight: 900; letter-spacing: 1.5px;"
            )
            self.status_hint.setText("Ваше соединение защищено")
            self.connect_button.set_active(True)
            self.ipv6_value.setText("Активен")
            self.info_label.setText("Защищённое соединение активно")
            if isValid(self.state_chip):
                self.state_chip.setText("●  ЗАЩИЩЕНО")
                self.state_chip.setStyleSheet(f"color: {GREEN}; font-weight: 900;")
        else:
            self.status_label.setText("НЕ ПОДКЛЮЧЕНО")
            self.status_label.setStyleSheet(
                f"color: {MUTED}; font-size: 23px; font-weight: 900; letter-spacing: 1.5px;"
            )
            self.status_hint.setText("Ваше соединение не защищено")
            self.connect_button.set_active(False)
            self.ipv6_value.setText("Ожидание")
            if isValid(self.state_chip):
                self.state_chip.setText("НЕ АКТИВНА")
                self.state_chip.setStyleSheet(f"color: {PINK}; font-weight: 900;")
            if self.info_label.text() == "":
                self.info_label.setText("Выберите устройство и подключитесь к PinVPN")

    def set_busy(self, busy, text):
        self.busy = busy
        self.connect_button.set_busy(busy)
        self.connect_button.setEnabled(not busy)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {PINK}; font-size: 23px; font-weight: 900; letter-spacing: 1.5px;"
        )
        if isValid(self.state_chip):
            self.state_chip.setText("СОЕДИНЕНИЕ...")
            self.state_chip.setStyleSheet(f"color: {PINK_SOFT}; font-weight: 900;")

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
            self.busy = False
            self.connect_button.set_busy(False)
            self.connect_button.setEnabled(True)

    def disconnect_vpn(self):
        self.set_busy(True, "ОТКЛЮЧЕНИЕ...")
        self.status_hint.setText("Закрываем защищённое соединение")

        try:
            service_request("disconnect")
            self.connected = False
            self.info_label.setText("Защищённый туннель отключён")
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
            self.busy = False
            self.connect_button.set_busy(False)
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
