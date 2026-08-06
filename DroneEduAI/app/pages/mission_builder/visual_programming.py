from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, Signal, QPoint, QPointF

from app.pages.mission_builder.blocks import BlockGraphicsItem


class BlocklyCanvas(QGraphicsView):
    """
    Visual mission canvas.
    - Dot-grid background (Figma-style)
    - Vertical column of BlockGraphicsItems
    - Bezier connector lines drawn between consecutive blocks
    - Blocks animate in on creation
    - Pan (right/middle click) + zoom (scroll wheel)
    - Auto-scrolls to the latest block after load
    """

    block_selected = Signal(str)   # block_id
    layout_changed = Signal()

    BLOCK_W     = BlockGraphicsItem.WIDTH
    BLOCK_H     = BlockGraphicsItem.HEIGHT
    BLOCK_GAP   = 32                 # vertical gap between blocks
    BLOCK_STEP  = BLOCK_H + BLOCK_GAP

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(
            "background-color: #080D1A; border: none; border-radius: 10px;"
        )

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -3000, 4000, 8000)
        self.setScene(self._scene)

        self._block_items: dict[str, BlockGraphicsItem] = {}
        self._ordered_items: list[BlockGraphicsItem] = []

        # Pan state
        self._panning    = False
        self._pan_start  = QPoint()

        # Zoom state
        self._zoom       = 1.0
        self._zoom_min   = 0.4
        self._zoom_max   = 2.5

    # ── Background ────────────────────────────────────────────────────
    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        dot_color = QColor("#1A2236")
        painter.setPen(QPen(dot_color, 1.2))

        gs = 28
        left  = int(rect.left())  - (int(rect.left())  % gs)
        top   = int(rect.top())   - (int(rect.top())   % gs)
        right  = int(rect.right())
        bottom = int(rect.bottom())

        for x in range(left, right + gs, gs):
            for y in range(top, bottom + gs, gs):
                painter.drawPoint(x, y)

        painter.restore()

    # ── Foreground – connector lines ──────────────────────────────────
    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw bezier connector lines between consecutive blocks."""
        if len(self._ordered_items) < 2:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        for i in range(len(self._ordered_items) - 1):
            top_item = self._ordered_items[i]
            bot_item = self._ordered_items[i + 1]

            from_pt = top_item.bottom_port()
            to_pt   = bot_item.top_port()

            ctrl_y = (from_pt.y() + to_pt.y()) / 2

            path = QPainterPath(from_pt)
            path.cubicTo(
                QPointF(from_pt.x(), ctrl_y),
                QPointF(to_pt.x(),   ctrl_y),
                to_pt,
            )

            # Line colour: accent of the source block
            accent_hex = getattr(top_item.model, "color", "#334155")
            line_color  = QColor(accent_hex)
            line_color.setAlpha(160)
            pen = QPen(line_color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            pen.setDashPattern([6, 4])
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

            # Arrow at destination port
            arrow_size = 6
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(accent_hex))
            arrow = QPainterPath(to_pt)
            arrow.lineTo(to_pt.x() - arrow_size / 2, to_pt.y() - arrow_size)
            arrow.lineTo(to_pt.x() + arrow_size / 2, to_pt.y() - arrow_size)
            arrow.closeSubpath()
            painter.drawPath(arrow)

        painter.restore()

    # ── Load Mission ──────────────────────────────────────────────────
    def load_mission(self, blocks_list):
        """Clears scene and redraws all blocks in sequence."""
        self._scene.clear()
        self._block_items.clear()
        self._ordered_items.clear()

        for block_model in blocks_list:
            item = BlockGraphicsItem(block_model)
            item.selected_signal.connect(self.block_selected.emit)
            item.position_changed.connect(self.layout_changed.emit)
            self._scene.addItem(item)
            self._block_items[block_model.id] = item

        self._auto_layout()

    def scroll_to_latest(self):
        """Smoothly pan view to the last block."""
        if self._ordered_items:
            self.ensureVisible(
                self._ordered_items[-1],
                xmargin=60, ymargin=40
            )

    # ── Layout ────────────────────────────────────────────────────────
    def _auto_layout(self):
        """Arrange blocks vertically centred in the scene."""
        sorted_items = sorted(
            self._block_items.values(),
            key=lambda x: x.model.execution_order
        )
        self._ordered_items = sorted_items

        total_h = len(sorted_items) * self.BLOCK_STEP
        start_y = -total_h / 2

        for idx, item in enumerate(sorted_items):
            item.setPos(-self.BLOCK_W / 2, start_y + idx * self.BLOCK_STEP)

        self.layout_changed.emit()

    def auto_layout_blocks(self):
        """Public alias for compatibility."""
        self._auto_layout()

    # ── Select Block ──────────────────────────────────────────────────
    def select_block(self, block_id: str):
        self._scene.clearSelection()
        if block_id in self._block_items:
            self._block_items[block_id].setSelected(True)
            self.centerOn(self._block_items[block_id])
            self.block_selected.emit(block_id)

    # ── Mouse events: Pan & Zoom ──────────────────────────────────────
    def wheelEvent(self, event):
        zoom_in  = 1.15
        zoom_out = 1 / zoom_in

        old_pos = self.mapToScene(event.position().toPoint())
        factor  = zoom_in if event.angleDelta().y() > 0 else zoom_out

        new_zoom = self._zoom * factor
        if self._zoom_min <= new_zoom <= self._zoom_max:
            self._zoom = new_zoom
            self.scale(factor, factor)
            delta = old_pos - self.mapToScene(event.position().toPoint())
            self.translate(-delta.x(), -delta.y())

        self.layout_changed.emit()

    def mousePressEvent(self, event):
        if event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning    = True
            self._pan_start  = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
