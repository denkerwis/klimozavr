from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Dict, List

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from klimozawr.ui.strings import status_display, tr
from klimozawr.ui.widgets.elided_label import ElidedLabel

def _g(obj: Any, key: str, default: Any = None) -> Any:
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
        return default


def _first(*vals: Any) -> Any:
    for v in vals:
        if v is not None:
            return v
    return None


@dataclass
class _TileSpec:
    cols: int
    rows: int
    tile_w: int
    tile_h: int


class DeviceCardWidget(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        device_id: int,
        tile_width: int = 260,
        tile_height: int = 260,
        text_scale: float = 1.0,
    ) -> None:
        super().__init__()
        self._device_id = int(device_id)
        self._tile_width = int(tile_width)
        self._tile_height = int(tile_height)
        self._text_scale = float(text_scale)
        self._icon_path: str | None = None
        self._icon_scale: int = 100
        self._reference_h = 260
        self._font_min_scale = 0.75
        self._font_max_scale = 1.8
        self._font_base = {
            "title": 12,
            "ip": 10,
            "status": 10,
            "metrics": 9,
            "meta": 9,
        }

        self.setObjectName("DeviceCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(self._tile_width, self._tile_height)

        self.lbl_icon = QLabel("")
        self.lbl_icon.setFixedSize(48, 48)
        self.lbl_icon.setScaledContents(True)

        self.lbl_title = ElidedLabel("")
        f = QFont()
        f.setPointSize(int(self._font_base["title"] * self._text_scale))
        f.setBold(True)
        self.lbl_title.setFont(f)
        self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.lbl_ip = QLabel("")
        ip_font = QFont()
        ip_font.setPointSize(int(self._font_base["ip"] * self._text_scale))
        self.lbl_ip.setFont(ip_font)
        self.lbl_ip.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        status_font = QFont()
        status_font.setPointSize(int(self._font_base["status"] * self._text_scale))
        self.lbl_status.setFont(status_font)

        self.lbl_metrics = QLabel("")
        self.lbl_metrics.setWordWrap(True)
        self.lbl_metrics.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        metrics_font = QFont()
        metrics_font.setPointSize(int(self._font_base["metrics"] * self._text_scale))
        self.lbl_metrics.setFont(metrics_font)

        self.lbl_meta = QLabel("")
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        meta_font = QFont()
        meta_font.setPointSize(int(self._font_base["meta"] * self._text_scale))
        self.lbl_meta.setFont(meta_font)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(self.lbl_icon, 0)
        title_row.addWidget(self.lbl_title, 1)

        lay = QVBoxLayout()
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lay.addLayout(title_row)
        lay.addWidget(self.lbl_ip, 0)
        lay.addWidget(self.lbl_status, 0)
        lay.addWidget(self.lbl_metrics, 0)
        lay.addWidget(self.lbl_meta, 1)
        self.setLayout(lay)

        self._apply_bg("#2a2a2a")
        self._apply_text_scale(self._text_scale)

    def mousePressEvent(self, ev) -> None:  # type: ignore[override]
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self._device_id)
        super().mousePressEvent(ev)

    def set_tile_size(self, width: int, height: int) -> None:
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        if width == self._tile_width and height == self._tile_height:
            return
        self._tile_width = width
        self._tile_height = height
        self.setFixedSize(self._tile_width, self._tile_height)
        self._apply_text_scale(self._tile_height / self._reference_h)
        self._refresh_icon()

    def _apply_text_scale(self, scale: float) -> None:
        scale = max(self._font_min_scale, min(self._font_max_scale, scale * self._text_scale))

        def _set_font(label: QLabel, base: int, bold: bool = False) -> None:
            font = label.font()
            font.setPointSize(max(7, int(round(base * scale))))
            font.setBold(bold)
            label.setFont(font)

        _set_font(self.lbl_title, self._font_base["title"], bold=True)
        _set_font(self.lbl_ip, self._font_base["ip"])
        _set_font(self.lbl_status, self._font_base["status"])
        _set_font(self.lbl_metrics, self._font_base["metrics"])
        _set_font(self.lbl_meta, self._font_base["meta"])

    def _apply_bg(self, bg: str) -> None:
        self.setStyleSheet(
            f"""
QFrame#DeviceCard {{
  border: 2px solid #3a3a3a;
  border-radius: 10px;
  background: {bg};
}}
QLabel {{
  color: #f0f0f0;
}}
"""
        )

    def set_snapshot(self, snap: Any) -> None:
        did = _g(snap, "device_id", _g(snap, "id", self._device_id))
        self._device_id = int(did)

        ip = str(_g(snap, "target", _g(snap, "ip", ""))).strip()
        name = str(_g(snap, "name", "")).strip()
        title = name or ip
        self.lbl_title.setText(title)
        if name and ip:
            self.lbl_ip.setText(ip)
            self.lbl_ip.setVisible(True)
        else:
            self.lbl_ip.setText("")
            self.lbl_ip.setVisible(False)

        status = str(_g(snap, "status", "UNKNOWN")).upper()
        unstable = bool(_g(snap, "unstable", False))

        loss = _first(_g(snap, "loss_pct"), _g(snap, "loss"), _g(snap, "loss_percent"))
        rtt = _first(_g(snap, "rtt_last_ms"), _g(snap, "rtt_last"), _g(snap, "rtt_ms"))

        # loss
        loss_txt = tr("placeholder.na")
        try:
            if loss is not None:
                loss_txt = f"{int(float(loss))}%"
        except Exception:
            loss_txt = tr("placeholder.na")

        # rtt
        rtt_txt = tr("placeholder.na")
        try:
            if rtt is not None:
                rtt_txt = f"{int(float(rtt))} {tr('unit.ms')}"
        except Exception:
            rtt_txt = tr("placeholder.na")

        extra = f" {tr('device.status_unstable')}" if unstable else ""
        status_text = status_display(status)
        self.lbl_status.setText(f"{status_text}{extra}")
        self.lbl_metrics.setText(f"{tr('device.loss')}: {loss_txt}\n{tr('device.rtt')}: {rtt_txt}")

        owner = str(_g(snap, "owner", "")).strip()
        location = str(_g(snap, "location", "")).strip()
        comment = str(_g(snap, "comment", "")).strip()

        meta: List[str] = []
        if owner:
            meta.append(tr("device.meta.owner", value=owner))
        if location:
            meta.append(tr("device.meta.location", value=location))
        if comment:
            meta.append(tr("device.meta.comment", value=comment))
        self.lbl_meta.setText("\n".join(meta) if meta else "")

        self._icon_path = _g(snap, "icon_path", None)
        self._icon_scale = int(_g(snap, "icon_scale", 100) or 100)
        self._refresh_icon()

        if status == "GREEN":
            self._apply_bg("#1e4d2b")
        elif status == "YELLOW":
            self._apply_bg("#6b5a1e")
        elif status == "RED":
            self._apply_bg("#5a1e1e")
        else:
            self._apply_bg("#2a2a2a")

    def _refresh_icon(self) -> None:
        if not self._icon_path:
            self.lbl_icon.clear()
            return
        pix = QPixmap(self._icon_path)
        if pix.isNull():
            self.lbl_icon.clear()
            return
        base = int(min(self._tile_width, self._tile_height) * 0.23)
        scale = max(50, min(200, int(self._icon_scale)))
        size = max(28, int(base * scale / 100))
        self.lbl_icon.setFixedSize(size, size)
        self.lbl_icon.setPixmap(pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class DeviceCardsView(QWidget):
    """
    fit_viewport=True  -> плитки формируют адаптивную сетку по ширине окна (режим USER)
    fit_viewport=False -> фиксированный размер плитки и скролл (режим ADMIN)
    """
    device_selected = Signal(int)

    def __init__(
        self,
        *,
        fit_viewport: bool = False,
        base_tile_px: int = 260,
        spacing: int = 12,
        margins: int = 14,
        min_tile_px: int = 170,
        max_tile_px: int = 420,
        text_scale: float = 1.0,
    ) -> None:
        super().__init__()

        self._fit_viewport = bool(fit_viewport)
        self._base_tile_px = int(base_tile_px)
        self._spacing = int(spacing)
        self._margins = int(margins)
        self._min_tile_px = int(min_tile_px)
        self._max_tile_px = int(max_tile_px)
        self._text_scale = float(text_scale)

        self._cards: Dict[int, DeviceCardWidget] = {}
        self._order: List[int] = []
        self._relayout_pending = False

        self._wrapper = QWidget()
        if self._fit_viewport:
            self._wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        wrap_h = QHBoxLayout()
        wrap_h.setContentsMargins(0, 0, 0, 0)
        wrap_h.setSpacing(0)

        self._grid_host = QWidget()
        self._grid = QGridLayout()
        self._grid.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
        self._grid.setHorizontalSpacing(self._spacing)
        self._grid.setVerticalSpacing(self._spacing)
        if self._fit_viewport:
            self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._grid_host.setLayout(self._grid)
        if self._fit_viewport:
            self._grid_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        if self._fit_viewport:
            wrap_h.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        else:
            wrap_h.addStretch(1)
        align = Qt.AlignLeft | Qt.AlignTop if self._fit_viewport else Qt.AlignTop
        wrap_h.addWidget(self._grid_host, 0, align)
        if not self._fit_viewport:
            wrap_h.addStretch(1)
        self._wrapper.setLayout(wrap_h)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setWidget(self._wrapper)
        if self._fit_viewport:
            self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if self._fit_viewport:
            self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._scroll)
        self.setLayout(root)

    def set_devices(self, snapshots: List[Any]) -> None:
        order: List[int] = []
        for s in snapshots:
            did = _g(s, "device_id", _g(s, "id", None))
            if did is not None:
                order.append(int(did))

        # remove
        to_remove = set(self._cards.keys()) - set(order)
        for did in to_remove:
            w = self._cards.pop(did)
            w.setParent(None)
            w.deleteLater()

        # add/update
        for s in snapshots:
            did = _g(s, "device_id", _g(s, "id", None))
            if did is None:
                continue
            did = int(did)

            card = self._cards.get(did)
            if card is None:
                card = DeviceCardWidget(
                    did,
                    tile_width=self._base_tile_px,
                    tile_height=self._base_tile_px,
                    text_scale=self._text_scale,
                )
                card.clicked.connect(self.device_selected.emit)
                self._cards[did] = card
            card.set_snapshot(s)

        self._order = order
        self._rebuild_grid()

    def update_device(self, snapshot: Any) -> None:
        did = _g(snapshot, "device_id", _g(snapshot, "id", None))
        if did is None:
            return
        did = int(did)

        card = self._cards.get(did)
        if card is None:
            card = DeviceCardWidget(
                did,
                tile_width=self._base_tile_px,
                tile_height=self._base_tile_px,
                text_scale=self._text_scale,
            )
            card.clicked.connect(self.device_selected.emit)
            self._cards[did] = card
            if did not in self._order:
                self._order.append(did)

        card.set_snapshot(snapshot)
        self._rebuild_grid()

    def resizeEvent(self, ev) -> None:  # type: ignore[override]
        super().resizeEvent(ev)
        if self._fit_viewport:
            self._schedule_relayout()

    def _schedule_relayout(self) -> None:
        if self._relayout_pending:
            return
        self._relayout_pending = True
        QTimer.singleShot(0, self._flush_relayout)

    def _flush_relayout(self) -> None:
        self._relayout_pending = False
        self._rebuild_grid()

    def _best_fit(self, n: int, vw: int, vh: int) -> _TileSpec:
        margins = self._grid.contentsMargins()
        aw = max(1, vw - (margins.left() + margins.right()))
        ah = max(1, vh - (margins.top() + margins.bottom()))

        min_w = max(self._min_tile_px, 260)
        min_h = max(self._min_tile_px, 180)
        max_w = max(self._max_tile_px, 700)
        max_h = max(self._max_tile_px, 700)

        best = _TileSpec(cols=1, rows=n, tile_w=min_w, tile_h=min_h)
        best_score = 0
        best_area = 0

        max_cols = min(n, 12)
        for cols in range(1, max_cols + 1):
            rows = int(ceil(n / cols))
            tw = (aw - self._spacing * (cols - 1)) // cols
            th = (ah - self._spacing * (rows - 1)) // rows
            tw = max(min_w, min(max_w, int(tw)))
            th = max(min_h, min(max_h, int(th)))
            score = min(tw, th)
            area = tw * th
            if score > best_score or (score == best_score and area > best_area):
                best = _TileSpec(cols=cols, rows=rows, tile_w=tw, tile_h=th)
                best_score = score
                best_area = area

        return best

    def _clear_grid(self) -> None:
        while self._grid.count():
            it = self._grid.takeAt(0)
            w = it.widget()
            if w is not None:
                self._grid.removeWidget(w)

    def _rebuild_grid(self) -> None:
        ids = [did for did in self._order if did in self._cards]
        n = len(ids)

        self._clear_grid()
        if n == 0:
            return

        vw = int(self._scroll.viewport().width())
        vh = int(self._scroll.viewport().height())

        if self._fit_viewport:
            spec = self._best_fit(n, vw, vh)
            cols = spec.cols
            tile_w = spec.tile_w
            tile_h = spec.tile_h
        else:
            tile_w = self._base_tile_px
            tile_h = self._base_tile_px
            cols = max(1, (vw + self._spacing) // (tile_w + self._spacing))

        r = 0
        c = 0
        for did in ids:
            card = self._cards[did]
            card.set_tile_size(tile_w, tile_h)
            self._grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self._grid.setRowStretch(r + 1, 1)
        self._grid.setColumnStretch(cols, 1)
