"""Four-second UP/DOWN paper-market presentation."""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from .prediction import Forecast


class TrialPanel(QtWidgets.QWidget):
    """Multi-ball overview with one focused ball for detailed annotations."""
    selected = QtCore.Signal(int)

    def __init__(self, config, colors, make_plot):
        super().__init__()
        self.config, self.colors, self.state = config, colors, None
        self.visible_ids = set(config.active_ids)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = QtWidgets.QLabel("AUTOMATIC UP / DOWN · 4 seconds · 10 virtual credits per bet")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.ticker = QtWidgets.QTableWidget(len(config.active_ids), 6)
        self.ticker.setHorizontalHeaderLabels(["BALL", "BET", "LEFT", "QUOTE", "CASH", "RESULT"])
        self.ticker.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ticker.verticalHeader().hide()
        self.ticker.verticalHeader().setDefaultSectionSize(22)
        self.ticker.horizontalHeader().setFixedHeight(24)
        self.ticker.setFixedHeight(138)
        self.ticker.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ticker.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.ticker.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.ticker.cellClicked.connect(self.choose_row)
        layout.addWidget(self.ticker)

        heading = QtWidgets.QHBoxLayout()
        heading.addWidget(QtWidgets.QLabel("Focus"))
        self.ball = QtWidgets.QComboBox()
        for mid in config.active_ids:
            self.ball.addItem(f"Ball {mid}", mid)
        self.ball.currentIndexChanged.connect(self.choose)
        heading.addWidget(self.ball)
        heading.addSpacing(8)
        heading.addWidget(QtWidgets.QLabel("Show"))
        self.visibility = {}
        for mid in config.active_ids:
            toggle = QtWidgets.QCheckBox(f"● {mid}")
            toggle.setChecked(True)
            toggle.setStyleSheet(f"QCheckBox {{ color: {colors[mid]}; }}")
            toggle.setToolTip(f"Show or hide Ball {mid} in both trial charts")
            toggle.toggled.connect(lambda checked, marker=mid: self.set_ball_visible(marker, checked))
            self.visibility[mid] = toggle
            heading.addWidget(toggle)
        self.round_label = QtWidgets.QLabel("Waiting for fresh motion history")
        self.round_label.setWordWrap(True)
        heading.addWidget(self.round_label, 1)
        layout.addLayout(heading)

        self.height_plot = make_plot(
            "Height · all enabled balls / dashed original / dotted live", "Height (% ROI)")
        self.height_plot.setToolTip(
            "Colours match ball IDs. Dots are actual sightings and straight lines join consecutive sightings.\n"
            "Dashed curves are original forecasts; dotted curves are current forecasts.\n"
            "Each coloured vertical line marks that ball's expiry. The focus ball shows its uncertainty band.")
        self.quote_plot = make_plot(
            "Credits per unit · solid sightings / dashed estimates / dot settlement", "Credits per unit")
        self.quote_plot.setToolTip(
            "Colours match ball IDs. Solid quote segments update from fresh sightings; dashed segments\n"
            "continue from retained models while evidence is missing. Each labelled vertical line is an expiry.\n"
            "The focus ball shows its entry reference and detailed result below the charts.")
        for chart in (self.height_plot, self.quote_plot):
            chart.setMinimumHeight(190)
            chart.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Ignored)
            layout.addWidget(chart, 1)

        self.series = {mid: self.make_ball_series(mid) for mid in config.active_ids}
        self.band_low = pg.PlotCurveItem(pen=None)
        self.band_high = pg.PlotCurveItem(pen=None)
        self.height_plot.addItem(self.band_low)
        self.height_plot.addItem(self.band_high)
        self.band = pg.FillBetweenItem(self.band_low, self.band_high,
                                       brush=pg.mkBrush(135, 174, 246, 25))
        self.height_plot.addItem(self.band)
        self.band.setZValue(-5)
        self.neutral = pg.LinearRegionItem(
            orientation="horizontal", movable=False,
            brush=pg.mkBrush(160, 170, 185, 20), pen=pg.mkPen("#526273"))
        self.height_plot.addItem(self.neutral)
        self.neutral.setZValue(-10)
        self.now_line = pg.InfiniteLine(
            angle=90, pen=pg.mkPen("#8c9aac"), label="NOW", labelOpts={"position": .95})
        self.height_plot.addItem(self.now_line)
        self.entry_line = pg.InfiniteLine(
            angle=0, pen=pg.mkPen("#526273", style=QtCore.Qt.PenStyle.DotLine))
        self.quote_plot.addItem(self.entry_line)
        self.quote_plot.setYRange(0, 100, padding=.06)
        self.quote_plot.setMouseEnabled(x=False, y=False)

        self.ledger = QtWidgets.QLabel()
        self.ledger.setWordWrap(True)
        layout.addWidget(self.ledger)
        self.caption = QtWidgets.QLabel(
            "Toggle balls with Show. Coloured expiry lines and labels identify each contract. "
            "The focus ball adds its uncertainty band and detail. Settlement still needs a real sighting.")
        self.caption.setObjectName("muted")
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        self.set_compatibility_aliases(config.active_ids[0])
        self.clear()

    def make_ball_series(self, mid):
        color = self.colors[mid]
        result = {
            "observed": self.height_plot.plot(symbol="o", symbolSize=3, connect="finite"),
            "original": self.height_plot.plot(),
            "live": self.height_plot.plot(),
            "ghost": self.height_plot.plot(pen=None, symbol="o", symbolSize=9, symbolBrush="#111922"),
            "settlement": self.height_plot.plot(pen=None, symbol="x", symbolSize=10),
            "quote": self.quote_plot.plot(connect="finite"),
            "estimated_quote": self.quote_plot.plot(connect="finite"),
            "quote_points": self.quote_plot.plot(pen=None, symbol="o", symbolSize=3),
            "quote_settlement": self.quote_plot.plot(pen=None, symbol="o", symbolSize=7),
            "height_label": pg.TextItem("", color=color, anchor=(1.05, .5)),
            "quote_label": pg.TextItem("", color=color, anchor=(0, 1.1)),
        }
        self.height_plot.addItem(result["height_label"])
        self.quote_plot.addItem(result["quote_label"])
        label_position = .95 - .1 * self.config.active_ids.index(mid)
        for name, chart in (("height_expiry", self.height_plot), ("quote_expiry", self.quote_plot)):
            line = pg.InfiniteLine(
                angle=90, pen=pg.mkPen(QtGui.QColor(color), width=1,
                                       style=QtCore.Qt.PenStyle.DashLine),
                label=f"B{mid} EXP", labelOpts={"position": label_position})
            chart.addItem(line)
            result[name] = line
        return result

    def set_compatibility_aliases(self, mid):
        """Keep existing checks and integrations pointed at the focused series."""
        series = self.series[mid]
        for name in ("observed", "original", "live", "ghost", "settlement", "quote",
                     "estimated_quote", "quote_points", "quote_settlement"):
            setattr(self, name, series[name])
        self.expiry_lines = [series["height_expiry"], series["quote_expiry"]]

    def focused_id(self):
        return self.ball.currentData()

    def choose_row(self, row, _column):
        mid = self.config.active_ids[row]
        self.ball.setCurrentIndex(self.ball.findData(mid))
        if not self.visibility[mid].isChecked():
            self.visibility[mid].setChecked(True)

    def choose(self, _index):
        mid = self.focused_id()
        self.set_compatibility_aliases(mid)
        self.selected.emit(mid)
        if self.state:
            self.update_state(self.state)

    def set_ball_visible(self, mid, visible):
        if visible:
            self.visible_ids.add(mid)
        else:
            self.visible_ids.discard(mid)
        if self.state:
            self.update_state(self.state)
        else:
            self.set_series_visible(mid, False)

    def set_series_visible(self, mid, visible):
        series = self.series[mid]
        for name in ("observed", "original", "live", "ghost", "settlement", "quote",
                     "estimated_quote", "quote_points", "quote_settlement", "height_label",
                     "quote_label", "height_expiry", "quote_expiry"):
            series[name].setVisible(visible)

    def clear_series(self, mid):
        series = self.series[mid]
        for name in ("observed", "original", "live", "ghost", "settlement", "quote",
                     "estimated_quote", "quote_points", "quote_settlement"):
            series[name].setData([], [])
        for name in ("height_label", "quote_label", "height_expiry", "quote_expiry"):
            series[name].hide()

    def clear(self):
        self.state = None
        for row, mid in enumerate(self.config.active_ids):
            for col, value in enumerate([str(mid), "WAIT", "—", "—", "1000.00", "—"]):
                self.ticker.setItem(row, col, QtWidgets.QTableWidgetItem(value))
            self.clear_series(mid)
        self.band_low.setData([], [])
        self.band_high.setData([], [])
        for item in (self.neutral, self.entry_line, self.now_line):
            item.hide()
        self.round_label.setText("Waiting for fresh motion history")
        self.ledger.setText("No settled rounds · camera ghost marks the focused ball's original forecast")
        self.summary.setText("AUTOMATIC UP / DOWN · 4 seconds · 10 virtual credits per bet")

    def update_state(self, state):
        self.state = state
        now, market = state["timestamp"], state["market"]
        total_profit = 0.
        for row, mid in enumerate(self.config.active_ids):
            ball = market["balls"][mid]
            round_ = ball["round"]
            active = round_ and round_["status"] == "OPEN"
            quote = round_["quotes"][-1][1] if round_ else None
            if active and now >= round_["terms"]["expiry"]:
                quote = None
            total_profit += ball["balance"] + (market["stake"] if active else 0) - 1000
            values = [str(mid), round_["terms"]["direction"] if active else "WAIT",
                      f"{max(0, round_['terms']['expiry'] - now):.1f}s" if active else "—",
                      (("~" if ball["quote_mode"] == "estimated" else "") + f"{quote:.1f}")
                      if quote is not None and active else "—",
                      f"{ball['balance']:.2f}",
                      ball["results"][-1]["status"] if ball["results"] else "—"]
            for col, value in enumerate(values):
                item = self.ticker.item(row, col)
                item.setText(value)
                item.setForeground(QtGui.QColor(self.colors[mid] if col == 0 else "#dae1e9"))
                item.setToolTip(ball["message"])
        self.summary.setText(
            f"AUTOMATIC UP / DOWN · 4s rounds · 10-credit stake · "
            f"{len(self.visible_ids)} balls shown · settled P/L {total_profit:+.2f}")

        focus = self.focused_id()
        for mid in self.config.active_ids:
            self.update_ball_series(mid, state, now, market, focused=mid == focus)
        self.update_focus_detail(focus, state, now, market)

        self.now_line.show()
        self.now_line.setValue(now)
        self.height_plot.setXRange(max(0, now - 8), now + market["horizon"] + .5, padding=0)
        visible_rounds = [market["balls"][mid]["round"] for mid in self.visible_ids
                          if market["balls"][mid]["round"]]
        if visible_rounds:
            left = max(0, min(now - 8, min(r["terms"]["opened"] for r in visible_rounds) - .15))
            right = max(now + .5, max(r["terms"]["expiry"] for r in visible_rounds)
                        + market["settlement_window"] + .2)
        else:
            left, right = max(0, now - 8), now + market["horizon"]
        self.quote_plot.setXRange(left, right, padding=0)
        self.height_plot.enableAutoRange(axis="y", enable=True)
        if not any(state["histories"][mid] for mid in self.visible_ids) and not visible_rounds:
            self.height_plot.setYRange(0, 100, padding=.05)

    def update_ball_series(self, mid, state, now, market, focused=False):
        series = self.series[mid]
        visible = mid in self.visible_ids
        self.set_series_visible(mid, visible)
        if not visible:
            return
        color = self.colors[mid]
        width = 2.5 if focused else 1.5
        history = state["histories"][mid]
        xs = [sample["timestamp"] for sample in history]
        ys = [100 * (1 - sample["normalised"][1]) for sample in history]
        series["observed"].setData(
            xs, ys, pen=pg.mkPen(color, width=width), symbolBrush=color, symbolPen=None,
            symbolSize=5 if focused else 3)
        for name in ("original", "live", "ghost", "settlement", "quote", "estimated_quote",
                     "quote_points", "quote_settlement"):
            series[name].setData([], [])
        for name in ("height_label", "quote_label", "height_expiry", "quote_expiry"):
            series[name].hide()

        ball = market["balls"][mid]
        round_ = ball["round"]
        if not round_:
            return
        terms = round_["terms"]
        forecast = Forecast(**terms["forecast"])
        offsets = np.linspace(0, market["horizon"], 41)
        times = offsets + terms["opened"]
        heights = np.array([forecast.at(float(t)) * 100 for t in offsets])
        series["original"].setData(
            times, heights,
            pen=pg.mkPen(color, width=width, style=QtCore.Qt.PenStyle.DashLine))
        series["ghost"].setData(
            [terms["expiry"]], [heights[-1]], symbolPen=pg.mkPen(color, width=width))
        series["height_label"].setText(f"B{mid} {terms['direction']}")
        series["height_label"].setPos(terms["expiry"], heights[-1])
        series["height_label"].show()
        for name in ("height_expiry", "quote_expiry"):
            series[name].setValue(terms["expiry"])
            series[name].show()

        live = ball["forecast"]
        if live and now < terms["expiry"] and round_["status"] == "OPEN":
            current = Forecast(**live)
            live_offsets = np.linspace(0, max(0, terms["expiry"] - current.issued), 41)
            series["live"].setData(
                current.issued + live_offsets,
                [100 * current.at(float(t)) for t in live_offsets],
                pen=pg.mkPen(color, width=width, style=QtCore.Qt.PenStyle.DotLine))

        quotes = round_["quotes"]
        solid_x, solid_y, estimated_x, estimated_y = self.quote_segments(quotes)
        series["quote"].setData(solid_x, solid_y, pen=pg.mkPen(color, width=width))
        series["estimated_quote"].setData(
            estimated_x, estimated_y,
            pen=pg.mkPen(color, width=width, style=QtCore.Qt.PenStyle.DashLine))
        sightings = [q for q in quotes if q[2] == "sighting"]
        series["quote_points"].setData(
            [q[0] for q in sightings], [q[1] for q in sightings],
            symbolBrush=color, symbolPen=None, symbolSize=5 if focused else 3)
        latest = quotes[-1]
        prefix = "~" if latest[2] == "estimated" else ""
        series["quote_label"].setText(f"B{mid} {prefix}{latest[1]:.1f}")
        series["quote_label"].setPos(latest[0], latest[1])
        series["quote_label"].show()
        if round_["status"] != "OPEN":
            series["quote_settlement"].setData(
                [latest[0]], [latest[1]], symbolBrush=color, symbolPen=None)
            if round_["settlement_height"] is not None:
                series["settlement"].setData(
                    [round_["settled_at"]], [100 * round_["settlement_height"]], symbolPen=color)

    @staticmethod
    def quote_segments(quotes):
        solid_x, solid_y, estimated_x, estimated_y = [], [], [], []
        previous_estimated = None
        for a, b in zip(quotes, quotes[1:]):
            if b[2] == "settlement":
                continue
            estimated = a[2] == "estimated" or b[2] == "estimated"
            xs, ys = (estimated_x, estimated_y) if estimated else (solid_x, solid_y)
            if estimated != previous_estimated:
                if xs:
                    xs.append(np.nan)
                    ys.append(np.nan)
                xs.append(a[0])
                ys.append(a[1])
            xs.append(b[0])
            ys.append(b[1])
            previous_estimated = estimated
        return solid_x, solid_y, estimated_x, estimated_y

    def update_focus_detail(self, mid, state, now, market):
        ball = market["balls"][mid]
        color = self.colors[mid]
        round_ = ball["round"]
        self.band_low.setData([], [])
        self.band_high.setData([], [])
        self.neutral.setVisible(bool(round_ and mid in self.visible_ids))
        self.entry_line.setVisible(bool(round_ and mid in self.visible_ids))
        if round_:
            terms = round_["terms"]
            forecast = Forecast(**terms["forecast"])
            offsets = np.linspace(0, market["horizon"], 41)
            times = offsets + terms["opened"]
            heights = np.array([forecast.at(float(t)) * 100 for t in offsets])
            spreads = np.array([2 * forecast.spread(float(t)) * 100 for t in offsets])
            if mid in self.visible_ids:
                self.band_low.setData(times, heights - spreads)
                self.band_high.setData(times, heights + spreads)
                fill = QtGui.QColor(color)
                fill.setAlpha(24)
                self.band.setBrush(pg.mkBrush(fill))
                self.neutral.setRegion([
                    100 * (terms["opening_height"] - terms["neutral"]),
                    100 * (terms["opening_height"] + terms["neutral"])])
                self.entry_line.setValue(terms["entry_quote"])
                live = ball["forecast"]
                if live and now < terms["expiry"] and round_["status"] == "OPEN":
                    current = Forecast(**live)
                    band_times = np.linspace(now, terms["expiry"], 31)
                    band_heights = np.array([
                        100 * current.at(float(t - current.issued)) for t in band_times])
                    band_spreads = np.array([
                        200 * current.projected_spread(float(t), now) for t in band_times])
                    self.band_low.setData(band_times, band_heights - band_spreads)
                    self.band_high.setData(band_times, band_heights + band_spreads)
            status = (f"{max(0, terms['expiry'] - now):.1f}s left"
                      if round_["status"] == "OPEN"
                      else f"{round_['status']} · {round_['profit']:+.2f} credits")
            hidden = " · hidden from charts" if mid not in self.visible_ids else ""
            self.round_label.setText(
                f"B{mid} focus · #{terms['number']} {terms['direction']} · "
                f"entry {terms['entry_quote']:.1f} · {status}{hidden}\n{ball['message']}")
        else:
            hidden = " · hidden from charts" if mid not in self.visible_ids else ""
            self.round_label.setText(f"B{mid} focus{hidden} · {ball['message']}")

        recent = " · ".join(
            f"#{r['number']} {r['direction']} {r['status']} {r['profit']:+.1f}"
            for r in ball["results"][-3:])
        errors = (f"Settled-sample error: forecast {100 * ball['forecast_mae']:.1f} / "
                  f"stay-put {100 * ball['hold_mae']:.1f} height points (n={ball['scored']})"
                  if ball["scored"] else
                  "Waiting for settled observations to compare forecast with stay-put baseline")
        self.ledger.setText((recent or "No settled rounds") + "\n" + errors)
