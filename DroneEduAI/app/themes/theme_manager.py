import os
from PySide6.QtGui import QColor, QPalette


class ThemeManager:
    # ─── Exact Spec Palette ───────────────────────────────────────────
    BG_DARK     = "#0F172A"   # Main application background
    BG_CARD     = "#1E293B"   # Rounded panel / card background
    BG_SIDEBAR  = "#1E293B"   # Panel header background
    BG_INPUT    = "#0F172A"   # Input field background
    BORDER_COLOR = "#334155"  # Subtle borders

    TEXT_PRIMARY   = "#F8FAFC"   # Primary text
    TEXT_SECONDARY = "#94A3B8"   # Secondary / muted text

    ACCENT        = "#8B5CF6"   # Main accent – violet / purple
    ACCENT_HOVER  = "#A78BFA"   # Hover variant of accent
    ACCENT_PRESSED = "#7C3AED"  # Pressed variant

    SUCCESS = "#22C55E"   # Green  – success / hand detected / good
    DANGER  = "#EF4444"   # Red    – error / stop / bad
    WARNING = "#F59E0B"   # Amber  – warning
    INFO    = "#38BDF8"   # Sky blue – info / secondary accent

    # Block type colours
    BLOCK_START     = "#22C55E"   # Mission Start
    BLOCK_TAKEOFF   = "#8B5CF6"   # Takeoff / Land
    BLOCK_MOVE      = "#3B82F6"   # Forward / Backward / Left / Right
    BLOCK_VERTICAL  = "#06B6D4"   # Up / Down
    BLOCK_HOVER     = "#F59E0B"   # Hover

    CARD_RADIUS = "12px"
    CARD_RADIUS_SM = "8px"

    # ─── Apply ────────────────────────────────────────────────────────
    @classmethod
    def apply_theme(cls, app):
        """
        Applies the DroneEduAI dark stylesheet to the QApplication.
        """
        palette = QPalette()
        palette.setColor(QPalette.Window,          QColor(cls.BG_DARK))
        palette.setColor(QPalette.WindowText,      QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.Base,            QColor(cls.BG_DARK))
        palette.setColor(QPalette.AlternateBase,   QColor(cls.BG_CARD))
        palette.setColor(QPalette.ToolTipBase,     QColor(cls.BG_CARD))
        palette.setColor(QPalette.ToolTipText,     QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.Text,            QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.Button,          QColor(cls.BG_CARD))
        palette.setColor(QPalette.ButtonText,      QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.BrightText,      QColor(cls.INFO))
        palette.setColor(QPalette.Highlight,       QColor(cls.ACCENT))
        palette.setColor(QPalette.HighlightedText, QColor(cls.TEXT_PRIMARY))
        app.setPalette(palette)

        qss = f"""
        /* ── Global ─────────────────────────────────────────────── */
        QWidget {{
            color: {cls.TEXT_PRIMARY};
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            font-size: 13px;
            background-color: transparent;
        }}
        QMainWindow {{
            background-color: {cls.BG_DARK};
        }}

        /* ── Scrollbars ──────────────────────────────────────────── */
        QScrollBar:vertical {{
            border: none;
            background: {cls.BG_DARK};
            width: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.BORDER_COLOR};
            min-height: 24px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.ACCENT};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{ height: 0px; }}

        QScrollBar:horizontal {{
            border: none;
            background: {cls.BG_DARK};
            height: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {cls.BORDER_COLOR};
            min-width: 24px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {cls.ACCENT};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{ width: 0px; }}

        /* ── Buttons ─────────────────────────────────────────────── */
        QPushButton {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS_SM};
            padding: 7px 16px;
            font-weight: 500;
            color: {cls.TEXT_PRIMARY};
        }}
        QPushButton:hover {{
            background-color: {cls.BORDER_COLOR};
            border-color: {cls.ACCENT};
            color: {cls.TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {cls.BG_DARK};
        }}
        QPushButton:disabled {{
            color: {cls.TEXT_SECONDARY};
            border-color: {cls.BORDER_COLOR};
            background-color: {cls.BG_CARD};
            opacity: 0.5;
        }}

        /* Accent primary button */
        QPushButton#btn-accent {{
            background-color: {cls.ACCENT};
            border: none;
            color: #FFFFFF;
            font-weight: 600;
        }}
        QPushButton#btn-accent:hover {{
            background-color: {cls.ACCENT_HOVER};
        }}
        QPushButton#btn-accent:pressed {{
            background-color: {cls.ACCENT_PRESSED};
        }}

        /* Success (Run Mission) button */
        QPushButton#btn-success {{
            background-color: {cls.SUCCESS};
            border: none;
            color: #FFFFFF;
            font-weight: 600;
        }}
        QPushButton#btn-success:hover {{
            background-color: #16A34A;
        }}

        /* Danger (Stop Mission) button */
        QPushButton#btn-danger {{
            background-color: {cls.DANGER};
            border: none;
            color: #FFFFFF;
            font-weight: 600;
        }}
        QPushButton#btn-danger:hover {{
            background-color: #DC2626;
        }}

        /* ── Labels ──────────────────────────────────────────────── */
        QLabel {{
            background: transparent;
            color: {cls.TEXT_PRIMARY};
        }}
        QLabel#lbl-secondary {{
            color: {cls.TEXT_SECONDARY};
            font-size: 11px;
        }}
        QLabel#lbl-section {{
            font-size: 11px;
            font-weight: 700;
            color: {cls.TEXT_SECONDARY};
            letter-spacing: 1.5px;
        }}
        QLabel#lbl-accent {{
            color: {cls.ACCENT};
            font-weight: 700;
        }}

        /* ── Progress Bar ────────────────────────────────────────── */
        QProgressBar {{
            background-color: {cls.BORDER_COLOR};
            border: none;
            border-radius: 5px;
            text-align: center;
            color: {cls.TEXT_PRIMARY};
            font-weight: bold;
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {cls.SUCCESS},
                stop:1 #16A34A
            );
            border-radius: 5px;
        }}

        /* ── Input Fields ────────────────────────────────────────── */
        QLineEdit {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS_SM};
            padding: 6px 10px;
            color: {cls.TEXT_PRIMARY};
        }}
        QLineEdit:focus {{
            border-color: {cls.ACCENT};
        }}

        QDoubleSpinBox, QSpinBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS_SM};
            padding: 5px 8px;
            color: {cls.TEXT_PRIMARY};
        }}
        QDoubleSpinBox:focus, QSpinBox:focus {{
            border-color: {cls.ACCENT};
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button {{
            background: {cls.BG_CARD};
            border: none;
            border-left: 1px solid {cls.BORDER_COLOR};
            width: 18px;
        }}
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            background: {cls.BG_CARD};
            border: none;
            border-left: 1px solid {cls.BORDER_COLOR};
            width: 18px;
        }}

        /* ── ComboBox ────────────────────────────────────────────── */
        QComboBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS_SM};
            padding: 5px 8px;
            color: {cls.TEXT_PRIMARY};
        }}
        QComboBox:focus {{
            border-color: {cls.ACCENT};
        }}
        QComboBox QAbstractItemView {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER_COLOR};
            selection-background-color: {cls.ACCENT};
        }}

        /* ── Menu ────────────────────────────────────────────────── */
        QMenu {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS_SM};
            padding: 6px;
        }}
        QMenu::item {{
            background: transparent;
            padding: 8px 24px 8px 12px;
            border-radius: 6px;
            color: {cls.TEXT_PRIMARY};
        }}
        QMenu::item:selected {{
            background-color: rgba(139, 92, 246, 0.15);
            color: {cls.ACCENT};
        }}
        QMenu::separator {{
            height: 1px;
            background: {cls.BORDER_COLOR};
            margin: 4px 8px;
        }}

        /* ── Tooltip ─────────────────────────────────────────────── */
        QToolTip {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: 6px;
            padding: 6px 10px;
        }}

        /* ── Named Frames ────────────────────────────────────────── */
        QFrame#card {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: {cls.CARD_RADIUS};
        }}
        QFrame#topbar {{
            background-color: {cls.BG_CARD};
            border-bottom: 1px solid {cls.BORDER_COLOR};
        }}
        QFrame#statusbar {{
            background-color: {cls.BG_CARD};
            border-top: 1px solid {cls.BORDER_COLOR};
        }}
        QFrame#left-panel {{
            background-color: {cls.BG_DARK};
        }}
        QFrame#right-panel {{
            background-color: {cls.BG_DARK};
        }}

        /* ── Splitter ────────────────────────────────────────────── */
        QSplitter::handle {{
            background-color: {cls.BORDER_COLOR};
            width: 1px;
        }}
        """
        app.setStyleSheet(qss)
