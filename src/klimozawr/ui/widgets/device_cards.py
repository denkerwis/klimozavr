from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
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
    tile: int


class DeviceCardWidget(QFrame):
    clicked = Signal(int)

    def __init__(self, device_id: int, tile_px: int = 260) -> None:
        super().__init__()
        self._device_id = int(device_id)
        self._tile_px = int(tile_px)

        self.setObjectName("DeviceCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(self._tile_px, self._tile_px)

        self.lbl_title = QLabel("")
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        self.lbl_title.setFont(f)
        self.lbl_title.setWordWrap(True)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)

        self.lbl_meta = QLabel("")
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        lay = QVBoxLayout()
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        lay.addWidget(self.lbl_title, 0)
        lay.addWidget(self.lbl_status, 0)
        lay.addWidget(self.lbl_meta, 1)
        self.setLayout(lay)

        self._apply_bg("#2a2a2a")

    def mousePressEvent(self, ev) -> None:  # type: ignore[override]
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self._device_id)
        super().mousePressEvent(ev)

    def set_tile_size(self, px: int) -> None:
        px = int(px)
        if px <= 0 or px == self._tile_px:
            return
        self._tile_px = px
        self.setFixedSize(self._tile_px, self._tile_px)

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

        ip = str(_g(snap, "ip", "")).strip()
        name = str(_g(snap, "name", "")).strip()
        title = f"{name}\n{ip}" if name else ip
        self.lbl_title.setText(title)

        status = str(_g(snap, "status", "UNKNOWN")).upper()
        unstable = bool(_g(snap, "unstable", False))

        loss = _first(_g(snap, "loss_pct"), _g(snap, "loss"), _g(snap, "loss_percent"))
        rtt = _first(_g(snap, "rtt_last_ms"), _g(snap, "rtt_last"), _g(snap, "rtt_ms"))

        # loss
        loss_txt = "—"
        try:
            if loss is not None:
                loss_txt = f"{int(float(loss))}%"
        except Exception:
            loss_txt = "—"

        # rtt
        rtt_txt = "—"
        try:
            if rtt is not None:
                rtt_txt = f"{int(float(rtt))} ms"
        except Exception:
            rtt_txt = "—"

        extra = " • нестабильно" if unstable else ""
        self.lbl_status.setText(f"{status}{extra}\nпотери: {loss_txt}  •  задержка: {rtt_txt}")

        owner = str(_g(snap, "owner", "")).strip()
        location = str(_g(snap, "location", "")).strip()
        comment = str(_g(snap, "comment", "")).strip()

        meta: List[str] = []
        if owner:
            meta.append(f"владелец: {owner}")
        if location:
            meta.append(f"локация: {location}")
        if comment:
            meta.append(f"коммент: {comment}")
        self.lbl_meta.setText("\n".join(meta) if meta else "")

        if status == "GREEN":
            self._apply_bg("#1e4d2b")
        elif status == "YELLOW":
            self._apply_bg("#6b5a1e")
        elif status == "RED":
            self._apply_bg("#5a1e1e")
        else:
            self._apply_bg("#2a2a2a")


class DeviceCardsView(QWidget):
    """
    fit_viewport=True  -> плитки автоскейлятся и заполняют доступную область (режим USER)
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
    ) -> None:
        super().__init__()

        self._fit_viewport = bool(fit_viewport)
        self._base_tile_px = int(base_tile_px)
        self._spacing = int(spacing)
        self._margins = int(margins)
        self._min_tile_px = int(min_tile_px)
        self._max_tile_px = int(max_tile_px)

        self._cards: Dict[int, DeviceCardWidget] = {}
        self._order: List[int] = []

        self._wrapper = QWidget()
        wrap_h = QHBoxLayout()
        wrap_h.setContentsMargins(0, 0, 0, 0)
        wrap_h.setSpacing(0)
        wrap_h.addStretch(1)

        self._grid_host = QWidget()
        self._grid = QGridLayout()
        self._grid.setContentsMargins(self._margins, self._margins, self._margins, self._margins)
        self._grid.setHorizontalSpacing(self._spacing)
        self._grid.setVerticalSpacing(self._spacing)
        self._grid_host.setLayout(self._grid)

        align = Qt.AlignCenter if self._fit_viewport else Qt.AlignTop
        wrap_h.addWidget(self._grid_host, 0, align)
        wrap_h.addStretch(1)
        self._wrapper.setLayout(wrap_h)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setWidget(self._wrapper)

        if self._fit_viewport:
            self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
                card = DeviceCardWidget(did, tile_px=self._base_tile_px)
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
            card = DeviceCardWidget(did, tile_px=self._base_tile_px)
            card.clicked.connect(self.device_selected.emit)
            self._cards[did] = card
            if did not in self._order:
                self._order.append(did)

        card.set_snapshot(snapshot)
        self._rebuild_grid()

    def resizeEvent(self, ev) -> None:  # type: ignore[override]
        super().resizeEvent(ev)
        if self._fit_viewport:
            self._rebuild_grid()

    def _best_fit(self, n: int, vw: int, vh: int) -> _TileSpec:
        m = self._margins
        aw = max(1, vw - (m * 2))
        ah = max(1, vh - (m * 2))

        best = _TileSpec(cols=1, rows=n, tile=self._min_tile_px)

        for cols in range(1, n + 1):
            rows = int(ceil(n / cols))
            tw = (aw - self._spacing * (cols - 1)) // cols
            th = (ah - self._spacing * (rows - 1)) // rows
            tile = int(min(tw, th))
            tile = max(self._min_tile_px, min(self._max_tile_px, tile))
            if tile > best.tile:
                best = _TileSpec(cols=cols, rows=rows, tile=tile)

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
            cols, tile = spec.cols, spec.tile
        else:
            tile = self._base_tile_px
            cols = max(1, (vw + self._spacing) // (tile + self._spacing))

        r = 0
        c = 0
        for did in ids:
            card = self._cards[did]
            card.set_tile_size(tile)
            self._grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self._grid.setRowStretch(r + 1, 1)
        self._grid.setColumnStretch(cols, 1)