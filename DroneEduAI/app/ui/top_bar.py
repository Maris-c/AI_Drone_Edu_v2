from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QMenu, QWidget, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPainter, QColor, QPen, QBrush, QFont


# ── Battery Indicator ─────────────────────────────────────────────────
class BatteryIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.percentage = 100
        self.setFixedSize(100, 32)

    def set_level(self, pct):
        self.percentage = max(0, min(100, pct))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Label
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(0, 0, 56, 32, Qt.AlignVCenter | Qt.AlignLeft,
                         f"{self.percentage}%")

        # Battery outline
        bx, by, bw, bh = 58, 9, 30, 14
        painter.setPen(QPen(QColor("#334155"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(bx, by, bw, bh, 2, 2)
        # Tip
        painter.drawRect(bx + bw, by + 4, 3, 6)

        # Fill colour
        if self.percentage > 50:
            fill = QColor("#22C55E")
        elif self.percentage > 20:
            fill = QColor("#F59E0B")
        else:
            fill = QColor("#EF4444")

        fill_w = max(2, int((bw - 4) * (self.percentage / 100)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(bx + 2, by + 2, fill_w, bh - 4, 2, 2)
        painter.end()


# ── Connection Dot Indicator ──────────────────────────────────────────
class DotIndicator(QWidget):
    def __init__(self, label="Connected", active_color="#22C55E", parent=None):
        super().__init__(parent)
        self.label_text  = label
        self.active_color = QColor(active_color)
        self.is_active   = True
        self.setFixedHeight(32)
        fm = self.fontMetrics()
        self.setFixedWidth(fm.horizontalAdvance(label) + 24)

    def set_state(self, active: bool):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        dot_color = self.active_color if self.is_active else QColor("#EF4444")
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot_color)
        painter.drawEllipse(0, 10, 10, 10)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(16, 0, self.width() - 16, 32,
                         Qt.AlignVCenter | Qt.AlignLeft, self.label_text)
        painter.end()


# ── Avatar Button ─────────────────────────────────────────────────────
class AvatarButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("AV", parent)
        self.setFixedSize(34, 34)
        self.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                border-radius: 17px;
                border: 2px solid #334155;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #38BDF8;
                background-color: #A78BFA;
            }
        """)


# ── Top Bar ───────────────────────────────────────────────────────────
class TopBar(QFrame):
    profile_clicked     = Signal()
    preferences_clicked = Signal()
    about_clicked       = Signal()
    logout_clicked      = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        # ── Logo Section ─────────────────────────────────────────────
        logo_widget = QWidget(self)
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)

        drone_icon = QLabel("🚁", self)
        drone_icon.setStyleSheet("font-size: 22px; background: transparent;")
        logo_layout.addWidget(drone_icon)

        name_layout = QWidget(self)
        nl = QHBoxLayout(name_layout)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(2)

        lbl_app = QLabel("DroneEdu", self)
        lbl_app.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #F8FAFC; "
            "letter-spacing: -0.5px; background: transparent;"
        )
        lbl_ai = QLabel("AI", self)
        lbl_ai.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #8B5CF6; "
            "letter-spacing: -0.5px; background: transparent;"
        )
        nl.addWidget(lbl_app)
        nl.addWidget(lbl_ai)
        logo_layout.addWidget(name_layout)

        # Vertical separator  |  Mission Builder subtitle
        sep = QLabel(" │ ", self)
        sep.setStyleSheet("color: #334155; font-size: 18px; background: transparent;")
        logo_layout.addWidget(sep)

        lbl_page = QLabel("Mission Builder", self)
        lbl_page.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #94A3B8; background: transparent;"
        )
        logo_layout.addWidget(lbl_page)

        layout.addWidget(logo_widget)

        # Spacer
        layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # ── Right Indicators ─────────────────────────────────────────
        layout.setSpacing(20)

        self.conn_indicator = DotIndicator("Connected", "#22C55E", self)
        layout.addWidget(self.conn_indicator)

        lbl_bat = QLabel("Battery", self)
        lbl_bat.setStyleSheet("font-size: 9px; color: #94A3B8; background: transparent;")
        layout.addWidget(lbl_bat)

        self.battery_indicator = BatteryIndicator(self)
        layout.addWidget(self.battery_indicator)

        lbl_tele = QLabel("Telemetry", self)
        lbl_tele.setStyleSheet("font-size: 9px; color: #94A3B8; background: transparent;")
        layout.addWidget(lbl_tele)

        self.tele_indicator = DotIndicator("Connected", "#22C55E", self)
        layout.addWidget(self.tele_indicator)

        # Separator
        sep2 = QLabel("|", self)
        sep2.setStyleSheet("color: #334155; background: transparent; padding: 0 4px;")
        layout.addWidget(sep2)

        # Avatar
        self.avatar_btn = AvatarButton(self)
        layout.addWidget(self.avatar_btn)

        # ── Avatar Context Menu ───────────────────────────────────────
        self.menu = QMenu(self)
        self.profile_act = QAction("👤  Profile", self)
        self.prefs_act   = QAction("⚙  Preferences", self)
        self.about_act   = QAction("ℹ  About", self)
        self.logout_act  = QAction("⏻  Exit", self)
        self.menu.addAction(self.profile_act)
        self.menu.addAction(self.prefs_act)
        self.menu.addSeparator()
        self.menu.addAction(self.about_act)
        self.menu.addAction(self.logout_act)

        self.avatar_btn.clicked.connect(self._show_menu)
        self.profile_act.triggered.connect(self.profile_clicked.emit)
        self.prefs_act.triggered.connect(self.preferences_clicked.emit)
        self.about_act.triggered.connect(self.about_clicked.emit)
        self.logout_act.triggered.connect(self.logout_clicked.emit)

    def set_connection_status(self, connected: bool):
        self.conn_indicator.set_state(connected)

    def set_telemetry_status(self, connected: bool):
        self.tele_indicator.set_state(connected)

    def set_battery_level(self, pct: int):
        self.battery_indicator.set_level(pct)

    # Keep compatibility with old MainWindow calls
    def set_mavlink_status(self, active: bool):
        pass

    def set_page_title(self, title: str):
        pass

    def _show_menu(self):
        pos = self.avatar_btn.mapToGlobal(self.avatar_btn.rect().bottomLeft())
        pos.setX(pos.x() - 120)
        pos.setY(pos.y() + 4)
        self.menu.exec(pos)
