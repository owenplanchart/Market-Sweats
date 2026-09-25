"""Four-second UP/DOWN paper-market presentation."""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from .prediction import Forecast


class TrialPanel(QtWidgets.QWidget):
    selected = QtCore.Signal(int)

    def __init__(self, config, colors, make_plot):
        super().__init__()
        self.config, self.colors, self.state = config, colors, None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = QtWidgets.QLabel("AUTOMATIC UP / DOWN · 4 seconds · 10 virtual credits per bet")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.ticker = QtWidgets.QTableWidget(5, 6)
        self.ticker.setHorizontalHeaderLabels(["BALL", "BET", "LEFT", "QUOTE", "CASH", "RESULT"])
        self.ticker.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ticker.verticalHeader().hide()
        self.ticker.verticalHeader().setDefaultSectionSize(22)
        self.ticker.horizontalHeader().setFixedHeight(24)
        self.ticker.setFixedHeight(138)
        self.ticker.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ticker.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ticker.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.ticker.cellClicked.connect(lambda row, col: self.ball.setCurrentIndex(row))
        layout.addWidget(self.ticker)
        heading = QtWidgets.QHBoxLayout()
        self.ball = QtWidgets.QComboBox()
        self.ball.addItems([f"Ball {mid}" for mid in config.active_ids])
        self.ball.currentIndexChanged.connect(self.choose)
        heading.addWidget(self.ball)
        self.round_label = QtWidgets.QLabel("Waiting for fresh motion history")
        self.round_label.setWordWrap(True)
        heading.addWidget(self.round_label, 1)
        layout.addLayout(heading)
        self.height_plot = make_plot("Height · joined sightings / dashed original / dotted live", "Height (% ROI)")
        self.height_plot.setToolTip("Dots are actual sightings. Straight lines join consecutive sightings of this ball,\n"
                                    "including gaps. These interpolated connections are not additional measurements.")
        self.quote_plot = make_plot("Quote · solid: sightings / dashed: estimated / dot: settlement", "Credits per unit")
        self.quote_plot.setToolTip("Solid segments update from fresh sightings. Dashed segments keep pricing the existing bet\n"
                                   "from its last motion model while evidence is missing; uncertainty grows with age.\n"
                                   "Quotes stop at expiry. The final dot is the actual payout or refund.")
        for chart in (self.height_plot, self.quote_plot):
            chart.setMinimumHeight(190)
            chart.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Ignored)
            layout.addWidget(chart, 1)
        self.observed = self.height_plot.plot(symbol="o", symbolSize=4, connect="finite")
        self.original = self.height_plot.plot()
        self.live = self.height_plot.plot()
        self.band_low = pg.PlotCurveItem(pen=None)
        self.band_high = pg.PlotCurveItem(pen=None)
        self.height_plot.addItem(self.band_low)
        self.height_plot.addItem(self.band_high)
        self.band = pg.FillBetweenItem(self.band_low, self.band_high, brush=pg.mkBrush(135, 174, 246, 25))
        self.height_plot.addItem(self.band)
        self.band.setZValue(-5)
        self.ghost = self.height_plot.plot(pen=None, symbol="o", symbolSize=11, symbolBrush="#111922")
        self.settlement = self.height_plot.plot(pen=None, symbol="x", symbolSize=12)
        self.neutral = pg.LinearRegionItem(orientation="horizontal", movable=False,
                                           brush=pg.mkBrush(160, 170, 185, 20), pen=pg.mkPen("#526273"))
        self.height_plot.addItem(self.neutral)
        self.neutral.setZValue(-10)
        self.now_line = pg.InfiniteLine(angle=90, pen=pg.mkPen("#8c9aac"), label="NOW", labelOpts={"position": .95})
        self.height_plot.addItem(self.now_line)
        self.expiry_lines = []
        for chart in (self.height_plot, self.quote_plot):
            line = pg.InfiniteLine(angle=90, pen=pg.mkPen("#65778d", style=QtCore.Qt.PenStyle.DashLine), label="EXPIRY", labelOpts={"position": .85})
            chart.addItem(line)
            self.expiry_lines.append(line)
        self.quote = self.quote_plot.plot(connect="finite")
        self.estimated_quote = self.quote_plot.plot(connect="finite")
        self.quote_points = self.quote_plot.plot(pen=None, symbol="o", symbolSize=3)
        self.quote_settlement = self.quote_plot.plot(pen=None, symbol="o", symbolSize=7)
        self.entry_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("#526273", style=QtCore.Qt.PenStyle.DotLine))
        self.quote_plot.addItem(self.entry_line)
        self.quote_plot.setYRange(0, 100, padding=.06)
        self.quote_plot.setMouseEnabled(x=False, y=False)
        self.ledger = QtWidgets.QLabel()
        self.ledger.setWordWrap(True)
        layout.addWidget(self.ledger)
        self.caption = QtWidgets.QLabel("Dashed quotes extrapolate while hidden; shading widens with missing evidence. Estimates are uncalibrated. Settlement needs a real sighting.")
        self.caption.setObjectName("muted")
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        self.clear()

    def choose(self, mid):
        self.selected.emit(mid)
        if self.state:
            self.update_state(self.state)

    def clear(self):
        self.state = None
        for row in range(5):
            for col, value in enumerate([str(row), "WAIT", "—", "—", "1000.00", "—"]):
                self.ticker.setItem(row, col, QtWidgets.QTableWidgetItem(value))
        for curve in (self.observed, self.original, self.live, self.band_low, self.band_high,
                      self.ghost, self.settlement, self.quote, self.estimated_quote, self.quote_points, self.quote_settlement):
            curve.setData([], [])
        for item in (self.neutral, self.entry_line, self.now_line, *self.expiry_lines):
            item.hide()
        self.round_label.setText("Waiting for fresh motion history")
        self.ledger.setText("No settled rounds · camera ghost marks the original vertical forecast")
        self.summary.setText("AUTOMATIC UP / DOWN · 4 seconds · 10 virtual credits per bet")

    def update_state(self, state):
        self.state = state
        now, market = state["timestamp"], state["market"]
        total_profit = 0.
        for mid, ball in market["balls"].items():
            round_ = ball["round"]
            active = round_ and round_["status"] == "OPEN"
            quote = round_["quotes"][-1][1] if round_ else None
            if active and now >= round_["terms"]["expiry"]:
                quote = None
            total_profit += ball["balance"] + (market["stake"] if active else 0) - 1000
            values = [str(mid), round_["terms"]["direction"] if active else "WAIT",
                      f"{max(0, round_['terms']['expiry'] - now):.1f}s" if active else "—",
                      ("~" if ball["quote_mode"] == "estimated" else "") + f"{quote:.1f}" if quote is not None and active else "—",
                      f"{ball['balance']:.2f}", ball["results"][-1]["status"] if ball["results"] else "—"]
            for col, value in enumerate(values):
                item = self.ticker.item(mid, col)
                item.setText(value)
                item.setForeground(QtGui.QColor(self.colors[mid] if col == 0 else "#dae1e9"))
                item.setToolTip(ball["message"])
        self.summary.setText(f"AUTOMATIC UP / DOWN · 4s rounds · 10-credit stake · settled P/L {total_profit:+.2f}")
        mid = self.ball.currentIndex()
        ball, color = market["balls"][mid], self.colors[mid]
        round_ = ball["round"]
        history = state["histories"][mid]
        xs = [sample["timestamp"] for sample in history]
        ys = [100 * (1 - sample["normalised"][1]) for sample in history]
        self.observed.setData(xs, ys, pen=pg.mkPen(color, width=2), symbolBrush=color, symbolPen=None)
        self.now_line.show()
        self.now_line.setValue(now)
        for curve in (self.original, self.live, self.band_low, self.band_high, self.ghost,
                      self.settlement, self.quote, self.estimated_quote, self.quote_points, self.quote_settlement):
            curve.setData([], [])
        for item in (self.neutral, self.entry_line, *self.expiry_lines):
            item.setVisible(bool(round_))
        if round_:
            terms = round_["terms"]
            forecast = Forecast(**terms["forecast"])
            offsets = np.linspace(0, market["horizon"], 41)
            times = offsets + terms["opened"]
            heights = np.array([forecast.at(float(t)) * 100 for t in offsets])
            spreads = np.array([2 * forecast.spread(float(t)) * 100 for t in offsets])
            self.original.setData(times, heights, pen=pg.mkPen(color, width=2, style=QtCore.Qt.PenStyle.DashLine))
            self.band_low.setData(times, heights - spreads)
            self.band_high.setData(times, heights + spreads)
            fill = QtGui.QColor(color); fill.setAlpha(24)
            self.band.setBrush(pg.mkBrush(fill))
            self.ghost.setData([terms["expiry"]], [heights[-1]], symbolPen=pg.mkPen(color, width=2))
            self.neutral.setRegion([100 * (terms["opening_height"] - terms["neutral"]),
                                    100 * (terms["opening_height"] + terms["neutral"])])
            for line in self.expiry_lines:
                line.setValue(terms["expiry"])
            self.entry_line.setValue(terms["entry_quote"])
            live = ball["forecast"]
            if live and now < terms["expiry"] and round_["status"] == "OPEN":
                current = Forecast(**live)
                offsets = np.linspace(0, terms["expiry"] - current.issued, 41)
                self.live.setData(current.issued + offsets, [100 * current.at(float(t)) for t in offsets],
                                  pen=pg.mkPen("#dce4ee", width=2, style=QtCore.Qt.PenStyle.DotLine))
                times = np.linspace(now, terms["expiry"], 31)
                heights = np.array([100 * current.at(float(t - current.issued)) for t in times])
                spreads = np.array([200 * current.projected_spread(float(t), now) for t in times])
                self.band_low.setData(times, heights - spreads)
                self.band_high.setData(times, heights + spreads)
            quotes = round_["quotes"]
            solid_x, solid_y, estimated_x, estimated_y = [], [], [], []
            previous_estimated = None
            for a, b in zip(quotes, quotes[1:]):
                if b[2] == "settlement":
                    continue
                estimated = a[2] == "estimated" or b[2] == "estimated"
                xs, ys = (estimated_x, estimated_y) if estimated else (solid_x, solid_y)
                if estimated != previous_estimated:
                    if xs:
                        xs.append(np.nan); ys.append(np.nan)
                    xs.append(a[0]); ys.append(a[1])
                xs.append(b[0]); ys.append(b[1])
                previous_estimated = estimated
            self.quote.setData(solid_x, solid_y, pen=pg.mkPen(color, width=2))
            self.estimated_quote.setData(estimated_x, estimated_y,
                                         pen=pg.mkPen(color, width=2, style=QtCore.Qt.PenStyle.DashLine))
            sightings = [q for q in quotes if q[2] == "sighting"]
            self.quote_points.setData([q[0] for q in sightings], [q[1] for q in sightings],
                                      symbolBrush=color, symbolPen=None)
            if round_["status"] != "OPEN":
                self.quote_settlement.setData([quotes[-1][0]], [quotes[-1][1]], symbolBrush=color, symbolPen=None)
                if round_["settlement_height"] is not None:
                    self.settlement.setData([round_["settled_at"]], [100 * round_["settlement_height"]], symbolPen=color)
            status = (f"{max(0, terms['expiry'] - now):.1f}s left" if round_["status"] == "OPEN" else
                      f"{round_['status']} · {round_['profit']:+.2f} credits")
            self.round_label.setText(f"#{terms['number']} · {terms['direction']} · entry {terms['entry_quote']:.1f} · {status}\n{ball['message']}")
            self.quote_plot.setXRange(terms["opened"] - .15, terms["expiry"] + market["settlement_window"] + .2, padding=0)
        else:
            self.round_label.setText(ball["message"])
            self.quote_plot.setXRange(now, now + market["horizon"], padding=0)
        self.height_plot.setXRange(max(0, now - 8), now + market["horizon"] + .5, padding=0)
        self.height_plot.enableAutoRange(axis="y", enable=True)
        if not ys and not round_:
            self.height_plot.setYRange(0, 100, padding=.05)
        recent = " · ".join(f"#{r['number']} {r['direction']} {r['status']} {r['profit']:+.1f}" for r in ball["results"][-3:])
        errors = (f"Settled-sample error: forecast {100 * ball['forecast_mae']:.1f} / stay-put {100 * ball['hold_mae']:.1f} height points (n={ball['scored']})"
                  if ball["scored"] else "Waiting for settled observations to compare forecast with stay-put baseline")
        self.ledger.setText((recent or "No settled rounds") + "\n" + errors)
