from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import QWidget, QVBoxLayout


class RttLossChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._series_rtt = QLineSeries()
        self._series_loss = QLineSeries()

        chart = QChart()
        chart.legend().setVisible(True)
        self._series_rtt.setName("RTT (ms)")
        self._series_loss.setName("loss (%)")
        chart.addSeries(self._series_rtt)
        chart.addSeries(self._series_loss)

        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("HH:mm")
        self._axis_x.setTitleText("время")
        chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series_rtt.attachAxis(self._axis_x)
        self._series_loss.attachAxis(self._axis_x)

        self._axis_rtt = QValueAxis()
        self._axis_rtt.setTitleText("RTT (мс)")
        chart.addAxis(self._axis_rtt, Qt.AlignLeft)
        self._series_rtt.attachAxis(self._axis_rtt)

        self._axis_loss = QValueAxis()
        self._axis_loss.setRange(0, 100)
        self._axis_loss.setTitleText("потери (%)")
        chart.addAxis(self._axis_loss, Qt.AlignRight)
        self._series_loss.attachAxis(self._axis_loss)

        self.view = QChartView(chart)
        self.view.setRenderHint(self.view.renderHints())

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def set_data(self, points: list[tuple[datetime, float | None, float | None]]) -> None:
        self._series_rtt.clear()
        self._series_loss.clear()

        if not points:
            return

        xs = []
        for ts, rtt, loss in points:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            qdt = QDateTime(ts)
            x = qdt.toMSecsSinceEpoch()
            xs.append(x)
            if rtt is not None:
                self._series_rtt.append(x, float(rtt))
            if loss is not None:
                self._series_loss.append(x, float(loss))

        if xs:
            self._axis_x.setRange(QDateTime.fromMSecsSinceEpoch(min(xs)), QDateTime.fromMSecsSinceEpoch(max(xs)))

        # auto-scale rtt
        rtts = [p[1] for p in points if p[1] is not None]
        if rtts:
            mn = min(rtts)
            mx = max(rtts)
            if mn == mx:
                mx = mn + 1
            self._axis_rtt.setRange(float(mn) * 0.9, float(mx) * 1.1)
        else:
            self._axis_rtt.setRange(0, 100)


