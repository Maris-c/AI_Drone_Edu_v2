from PySide6.QtWidgets import QGraphicsObject
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QLinearGradient, QPolygonF
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QPropertyAnimation, Property

# Block type → colours
BLOCK_COLORS = {
    "start":    {"bg": "#0D3321", "border": "#22C55E", "accent": "#22C55E"},
    "takeoff":  {"bg": "#1E1040", "border": "#8B5CF6", "accent": "#8B5CF6"},
    "land":     {"bg": "#1E1040", "border": "#8B5CF6", "accent": "#8B5CF6"},
    "move":     {"bg": "#0C1A3A", "border": "#3B82F6", "accent": "#3B82F6"},
    "vertical": {"bg": "#031926", "border": "#06B6D4", "accent": "#06B6D4"},
    "hover":    {"bg": "#27190A", "border": "#F59E0B", "accent": "#F59E0B"},
}

# Block type → icon emoji (fallback when no SVG)
BLOCK_ICONS = {
    "start":    "▶",
    "takeoff":  "🚀",
    "land":     "🛬",
    "move":     "➤",
    "vertical": "↕",
    "hover":    "◎",
}

# Block name → specific emoji
NAME_ICONS = {
    "Mission Start": "▶",
    "Takeoff":       "🚀",
    "Land":          "🛬",
    "Forward":       "⬆",
    "Backward":      "⬇",
    "Turn Right":    "↻",
    "Turn Left":     "↺",
    "Move Right":    "➡",
    "Move Left":     "⬅",
    "Up":            "↑",
    "Down":          "↓",
    "Hover":         "◎",
}


class BlockGraphicsItem(QGraphicsObject):
    """
    A richly-styled mission block card for the GraphicsScene.
    Features:
      - Color-coded by block type
      - Left accent stripe
      - Icon + title + parameter text
      - Repeat ×N badge when repeat_count > 1
      - Hover glow effect
      - Fade-in animation on first paint
    """
    selected_signal  = Signal(str)   # block_id
    position_changed = Signal()

    WIDTH  = 280
    HEIGHT = 72

    def __init__(self, block_model, parent=None):
        super().__init__(parent)
        self.model   = block_model
        self.width   = self.WIDTH
        self.height  = self.HEIGHT
        self.hovered = False
        self._opacity = 0.0   # for fade-in animation

        self.setFlags(
            QGraphicsObject.ItemIsMovable |
            QGraphicsObject.ItemIsSelectable |
            QGraphicsObject.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setOpacity(0.0)

        # Fade-in animation
        self._anim = QPropertyAnimation(self, b"opacity", self)
        self._anim.setDuration(350)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    # ── Qt property for animation ─────────────────────────────────────
    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, val):
        self._opacity = val
        self.setOpacity(val)
        self.update()

    opacity = Property(float, _get_opacity, _set_opacity)

    # ── Bounding ─────────────────────────────────────────────────────
    def boundingRect(self):
        return QRectF(-2, -2, self.width + 4, self.height + 4)

    # ── Paint ─────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        btype  = getattr(self.model, "block_type", "move")
        colors = BLOCK_COLORS.get(btype, BLOCK_COLORS["move"])
        bg_col = QColor(colors["bg"])
        bd_col = QColor(colors["border"])
        ac_col = QColor(colors["accent"])

        # ── Background card ───────────────────────────────────────────
        card_path = QPainterPath()
        card_path.addRoundedRect(0, 0, self.width, self.height, 10, 10)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_col))
        painter.drawPath(card_path)

        # ── Border ───────────────────────────────────────────────────
        if self.isSelected():
            border_pen = QPen(QColor("#F8FAFC"), 2)
        elif self.hovered:
            border_pen = QPen(bd_col, 2)
        else:
            border_pen = QPen(bd_col.darker(130), 1)

        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(card_path)

        # ── Left accent stripe ────────────────────────────────────────
        stripe = QPainterPath()
        stripe.addRoundedRect(0, 0, 5, self.height, 3, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(ac_col))
        painter.drawPath(stripe)

        # ── Icon ──────────────────────────────────────────────────────
        icon_char = NAME_ICONS.get(self.model.name, BLOCK_ICONS.get(btype, "◆"))
        font_icon = QFont("Segoe UI Emoji", 16)
        painter.setFont(font_icon)
        painter.setPen(QColor(colors["accent"]))
        painter.drawText(QRectF(14, 0, 36, self.height), Qt.AlignCenter, icon_char)

        # ── Title ─────────────────────────────────────────────────────
        font_title = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(54, 26, self.model.name)

        # ── Parameter subtitle ────────────────────────────────────────
        font_sub = QFont("Segoe UI", 8)
        painter.setFont(font_sub)
        painter.setPen(QColor("#94A3B8"))

        rep = getattr(self.model, "repeat_count", 1)
        if rep > 1:
            param_text = f"Repeat × {rep}  ·  Duration = {self.model.duration:.1f}s"
        elif self.model.name == "Mission Start":
            param_text = "Initialization · triggers at launch"
        elif self.model.name == "Takeoff":
            param_text = "Altitude = 1.5 m"
        elif self.model.name == "Land":
            param_text = "Return to ground"
        elif self.model.name in ("Up", "Down"):
            param_text = f"Distance = 1.0 m  ·  Duration = {self.model.duration:.1f}s"
        else:
            param_text = f"Duration = {self.model.duration:.1f}s"

        painter.drawText(54, 46, param_text)

        # ── Execution order badge ─────────────────────────────────────
        badge_rect = QRectF(self.width - 34, 8, 28, 18)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#0F172A")))
        painter.drawRoundedRect(badge_rect, 4, 4)
        font_tag = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font_tag)
        painter.setPen(QColor("#475569"))
        painter.drawText(badge_rect, Qt.AlignCenter, f"#{self.model.execution_order}")

        # ── Repeat badge (top-left accent corner when repeat > 1) ────
        if rep > 1:
            rep_rect = QRectF(5, 2, 34, 14)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(ac_col.darker(120)))
            painter.drawRoundedRect(rep_rect, 3, 3)
            font_rep = QFont("Segoe UI", 7, QFont.Bold)
            painter.setFont(font_rep)
            painter.setPen(QColor("#F8FAFC"))
            painter.drawText(rep_rect, Qt.AlignCenter, f"×{rep}")

    # ── Events ────────────────────────────────────────────────────────
    def itemChange(self, change, value):
        if change == QGraphicsObject.ItemPositionHasChanged:
            self.position_changed.emit()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self.selected_signal.emit(self.model.id)
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    # ── Connector port positions ──────────────────────────────────────
    def top_port(self) -> QPointF:
        return self.pos() + QPointF(self.width / 2, 0)

    def bottom_port(self) -> QPointF:
        return self.pos() + QPointF(self.width / 2, self.height)
