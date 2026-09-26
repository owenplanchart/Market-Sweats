"""Restrained camera composite and source-time market panels."""
from queue import Empty
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from .worker import Worker
from .trial_ui import TrialPanel
from .prediction import Forecast

COLORS = ["#f0af68", "#67d4c3", "#87aef6", "#c3a0ec", "#d8d879"]


class CameraView(QtWidgets.QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.image = None
        self.state = None
        self.outlines = self.labels = self.trails = self.held = True
        self.trail_seconds = config.trail_seconds
        self.prediction_ball = 0
        self.show_prediction = True
        self.setMinimumSize(260, 320)

    def set_frame(self, image, state):
        self.image = QtGui.QImage(image.data, image.shape[1], image.shape[0], image.strides[0],
                                  QtGui.QImage.Format.Format_BGR888).copy()
        self.state = state
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor("#0b1015"))
        if self.image is None:
            p.setPen(QtGui.QColor("#8a98a8"))
            p.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "Waiting for source…")
            return
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        scale = min(self.width()/self.image.width(), self.height()/self.image.height())
        x = (self.width()-self.image.width()*scale)/2
        y = (self.height()-self.image.height()*scale)/2
        p.translate(x, y)
        p.scale(scale, scale)
        p.drawImage(0, 0, self.image)
        now = self.state["timestamp"]
        for mid, history in self.state["histories"].items():
            color = QtGui.QColor(COLORS[mid])
            if self.trails:
                visible = [s for s in history if now-s["timestamp"] <= self.trail_seconds]
                for a, b in zip(visible, visible[1:]):
                    color.setAlphaF(max(.12, 1-(now-b["timestamp"])/self.trail_seconds))
                    pen = QtGui.QPen(color, 1.5/scale)
                    p.setPen(pen)
                    p.drawLine(QtCore.QPointF(*a["centre"]), QtCore.QPointF(*b["centre"]))
            if self.held and history and self.state["states"][mid] != "observed":
                last = history[-1]
                color.setAlpha(110 if self.state["states"][mid] != "lost" else 50)
                p.setPen(QtGui.QPen(color, 1/scale, QtCore.Qt.PenStyle.DashLine))
                p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                p.drawEllipse(QtCore.QPointF(*last["centre"]), 10/scale, 10/scale)
        if self.show_prediction and "market" in self.state:
            ball = self.state["market"]["balls"][self.prediction_ball]
            round_ = ball["round"]
            if round_ and round_["status"] == "OPEN":
                terms = round_["terms"]
                forecast = Forecast(**terms["forecast"])
                roi = self.config.roi
                height = self.image.height() - 1
                width = self.image.width() - 1
                gx = (roi[0] + forecast.x * roi[2]) * width
                gy = (roi[1] + (1 - forecast.at(4.)) * roi[3]) * height
                origin_y = (roi[1] + (1 - forecast.height) * roi[3]) * height
                spread = 2 * forecast.spread(4.) * roi[3] * height
                color = QtGui.QColor(COLORS[self.prediction_ball])
                p.save()
                p.setClipRect(QtCore.QRectF(0, 0, width, height))
                fill = QtGui.QColor(color); fill.setAlpha(28)
                p.setBrush(fill)
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                # Width is just a glyph: only vertical movement is forecast.
                p.drawEllipse(QtCore.QPointF(gx, gy), 14/scale, spread)
                p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                p.setPen(QtGui.QPen(color, 2/scale, QtCore.Qt.PenStyle.DotLine))
                p.drawLine(QtCore.QPointF(gx, origin_y), QtCore.QPointF(gx, gy))
                p.setPen(QtGui.QPen(color, 2/scale))
                p.drawEllipse(QtCore.QPointF(gx, gy), 10/scale, 10/scale)
                p.setFont(QtGui.QFont("Menlo", max(9, int(10/scale))))
                label_y = min(max(gy, 18/scale), height - 12/scale)
                label_x = min(max(gx + 15/scale, 8/scale), max(8/scale, width - 210/scale))
                p.drawText(QtCore.QPointF(label_x, label_y), f"{self.prediction_ball} {terms['direction']} · original +4s")
                p.restore()
        p.setFont(QtGui.QFont("Menlo", max(9, int(10/scale))))
        for obs in self.state["raw"]:
            mid = obs["marker_id"]
            p.setPen(QtGui.QPen(QtGui.QColor(COLORS[mid]), 1.5/scale))
            if self.outlines:
                p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(*xy) for xy in obs["display_corners"]]))
            if self.labels:
                x, y = obs["display_centre"]
                nx, ny = obs["normalised"]
                suffix = " ?" if self.state["states"][mid] == "ambiguous" else ""
                p.drawText(QtCore.QPointF(x+12/scale, y-8/scale), f"{mid}{suffix}  {nx:.2f}, {ny:.2f}")
        p.end()


class Candles(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.picture = QtGui.QPicture()

    def set_data(self, candles, color, interval):
        self.prepareGeometryChange()
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(color, width=1))
        for c in candles:
            x = c["start"]+interval/2
            p.drawLine(QtCore.QPointF(x, c["low"]), QtCore.QPointF(x, c["high"]))
            p.setBrush(pg.mkBrush(color) if c["close"] >= c["open"] else pg.mkBrush("#111922"))
            low = min(c["open"], c["close"])
            height = abs(c["open"]-c["close"])
            if height < .04:
                p.drawLine(QtCore.QPointF(x-interval*.3, low), QtCore.QPointF(x+interval*.3, low))
            else:
                p.drawRect(QtCore.QRectF(x-interval*.3, low, interval*.6, height))
        p.end()
        self.update()
        self.informViewBoundsChanged()

    def paint(self, painter, option, widget=None):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())


def plot(title, ylabel):
    widget = pg.PlotWidget(title=title)
    widget.setBackground("#111922")
    widget.setLabel("left", ylabel)
    widget.setLabel("bottom", "Source time", units="s")
    widget.showGrid(x=True, y=True, alpha=.12)
    widget.setMenuEnabled(False)
    widget.hideButtons()
    widget.setMinimumSize(280, 220)
    for name in ("left", "bottom"):
        axis = widget.getAxis(name)
        axis.setTextPen(pg.mkPen("#c8d2df"))
        axis.setPen(pg.mkPen("#708297"))
        axis.setTickFont(QtGui.QFont("Helvetica", 11))
    return widget


class Window(QtWidgets.QMainWindow):
    def __init__(self, config, kind, value, log=None, start_worker=True):
        super().__init__()
        self.config = config
        self.worker = Worker(config, kind, value, log)
        self.last_payload = None
        self._layout_pending = False
        self._layout_ready = False
        self._portrait_layout = None
        self.setWindowTitle("ArUcoMarket · UP / DOWN trial")
        screen = self.screen().availableGeometry()
        width, height = config.window_width, config.window_height
        if height > screen.height()-80 and screen.width() > screen.height():
            width, height = min(1440, screen.width()-80), screen.height()-80
        self.resize(min(width, screen.width()-40), min(height, screen.height()-60))
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #0c1219; color: #dae1e9; }
            QLabel#title { font-size: 23px; font-weight: 600; }
            QLabel#muted { color: #8c9aac; }
            QPushButton, QComboBox, QSpinBox, QDoubleSpinBox { background: #1b2735; padding: 6px; border: 1px solid #2b3a4c; border-radius: 3px; }
            QPushButton:checked { background: #354d60; }
            QHeaderView::section { background: #15202c; color: #91a0b2; padding: 7px; border: 0; }
            QTableWidget { background: #111922; gridline-color: #223142; border: 0; }
            QSplitter::handle { background: #263441; width: 5px; }
        """)
        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 12)
        heading = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("ARUCO / MARKET")
        title.setObjectName("title")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(QtWidgets.QLabel("UP / DOWN   /   PAPER MARKET TRIAL"))
        layout.addLayout(heading)
        self.source_label = QtWidgets.QLabel()
        self.source_label.setObjectName("muted")
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)
        controls = QtWidgets.QHBoxLayout()
        self.play = QtWidgets.QPushButton("Pause")
        self.play.setCheckable(True)
        self.play.clicked.connect(self.toggle_pause)
        controls.addWidget(self.play)
        for text, callback in [("Reset", self.reset), ("Open movie…", self.open_movie),
                               ("Synthetic test", lambda: self.change_source("synthetic", None))]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(callback)
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)
        view_controls = QtWidgets.QHBoxLayout()
        self.camera_index = QtWidgets.QSpinBox()
        self.camera_index.setRange(0, 20)
        self.camera_index.setValue(config.camera_index)
        self.camera_index.setPrefix("Device ")
        self.camera_index.setToolTip("Choose the macOS camera index for your iPhone. Device 0 is not necessarily the iPhone.")
        view_controls.addWidget(self.camera_index)
        camera = QtWidgets.QPushButton("Connect iPhone / camera")
        camera.setToolTip("Mount the iPhone vertically and enable Continuity Camera, then select its device index.")
        camera.clicked.connect(lambda: self.change_source("camera", self.camera_index.value()))
        view_controls.addWidget(camera)
        view_controls.addStretch()
        self.layout_mode = QtWidgets.QComboBox()
        self.layout_mode.addItem("Fit screen", "auto")
        self.layout_mode.addItem("Portrait views", "portrait")
        self.layout_mode.addItem("Side by side", "side_by_side")
        self.layout_mode.setCurrentIndex(self.layout_mode.findData(config.layout))
        view_controls.addWidget(self.layout_mode)
        self.camera_only = QtWidgets.QCheckBox("Camera only")
        view_controls.addWidget(self.camera_only)
        fullscreen = QtWidgets.QPushButton("Fullscreen")
        fullscreen.clicked.connect(self.fullscreen)
        view_controls.addWidget(fullscreen)
        layout.addLayout(view_controls)
        self.split = QtWidgets.QSplitter()
        self.split.setChildrenCollapsible(False)
        self.view = CameraView(config)
        self.split.addWidget(self.view)
        self.panels = QtWidgets.QWidget()
        self.market_scroll = QtWidgets.QScrollArea()
        self.market_scroll.setWidgetResizable(True)
        self.market_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.market_scroll.setWidget(self.panels)
        self.market_scroll.setMinimumWidth(320)
        self.market_scroll.viewport().installEventFilter(self)
        outer = QtWidgets.QVBoxLayout(self.panels)
        outer.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinAndMaxSize)
        outer.setContentsMargins(12, 0, 0, 0)
        self.tabs = QtWidgets.QTabWidget()
        self.trial = TrialPanel(config, COLORS, plot)
        self.trial.selected.connect(self.select_prediction)
        self.tabs.addTab(self.trial, "UP / DOWN trial")
        observed_panel = QtWidgets.QWidget()
        markets = QtWidgets.QVBoxLayout(observed_panel)
        markets.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(observed_panel, "Observed index / OHLC")
        self.tabs.currentChanged.connect(self.change_market_view)
        outer.addWidget(self.tabs)
        note = QtWidgets.QLabel(f"OBSERVED INDEX   P = {config.index_base:g} + {config.index_gain:g} × x\nArtistic index · x is horizontal position · y increases downward")
        note.setObjectName("muted")
        markets.addWidget(note)
        self.ticker = QtWidgets.QTableWidget(5, 6)
        self.ticker.setHorizontalHeaderLabels(["BALL", "INDEX / HELD", "Y", "AGE", "STATE", "ACTIVITY¹"])
        self.ticker.verticalHeader().hide()
        self.ticker.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ticker.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ticker.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ticker.verticalHeader().setDefaultSectionSize(26)
        self.ticker.horizontalHeader().setFixedHeight(30)
        self.ticker.setFixedHeight(162)
        markets.addWidget(self.ticker)
        self.history = plot("Observed index · dots are sightings", "Index")
        self.history.setToolTip("Each colour connects successive sightings of the same ball.\n"
                               "Straight lines interpolate between sightings, including gaps; only dots are measured.")
        self.curves = [self.history.plot(pen=pg.mkPen(c, width=2), symbol="o", symbolSize=6,
                                         symbolBrush=c, symbolPen=None, connect="finite") for c in COLORS]
        self.charts = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.charts.setChildrenCollapsible(False)
        self.charts.addWidget(self.history)
        self.candle_panel = QtWidgets.QWidget()
        candle_layout = QtWidgets.QVBoxLayout(self.candle_panel)
        candle_layout.setContentsMargins(0, 0, 0, 0)
        candle_heading = QtWidgets.QHBoxLayout()
        candle_heading.addWidget(QtWidgets.QLabel("OHLC / OBSERVED RANGE"))
        candle_heading.addStretch()
        self.candle_ball = QtWidgets.QComboBox()
        self.candle_ball.addItems([f"Ball {i}" for i in config.active_ids])
        self.candle_ball.currentIndexChanged.connect(self.refresh_panels)
        candle_heading.addWidget(self.candle_ball)
        candle_layout.addLayout(candle_heading)
        self.ohlc = plot(f"{config.candle_seconds:g}s intervals · empty intervals stay empty", "Index")
        self.ohlc.setToolTip("Each candle summarises actual index sightings for the selected ball.\n"
                            "Body: first (open) and last (close) values. Wick: lowest and highest values.\n"
                            "Filled body: close at or above open; hollow: close below open.\n"
                            "A single value produces a dash. No sightings means no candle. These are not trades.")
        self.candles = Candles()
        self.ohlc.addItem(self.candles)
        self.empty_candles = pg.TextItem("No observations for this ball", color="#8c9aac", anchor=(.5,.5))
        self.ohlc.addItem(self.empty_candles)
        candle_layout.addWidget(self.ohlc, 1)
        self.charts.addWidget(self.candle_panel)
        markets.addWidget(self.charts, 1)
        caption = QtWidgets.QLabel("¹ Activity = sightings, not trades. Lines interpolate between sightings.\nSolid outlines: observed · Dashed rings: held · OHLC uses actual sightings only")
        caption.setObjectName("muted")
        markets.addWidget(caption)
        self.split.addWidget(self.market_scroll)
        self.layout_mode.currentIndexChanged.connect(self.set_layout)
        self.camera_only.toggled.connect(self.market_scroll.setHidden)
        layout.addWidget(self.split, 1)
        layers = QtWidgets.QHBoxLayout()
        for label, attr in [("Outlines", "outlines"), ("IDs / coordinates", "labels"),
                            ("Trails", "trails"), ("Held locations", "held")]:
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda enabled, a=attr: self.set_layer(a, enabled))
            layers.addWidget(checkbox)
        layers.addStretch()
        layers.addWidget(QtWidgets.QLabel("Trail persistence"))
        self.trail = QtWidgets.QDoubleSpinBox()
        self.trail.setRange(.1, 120)
        self.trail.setValue(config.trail_seconds)
        self.trail.setSuffix(" s")
        self.trail.valueChanged.connect(lambda value: self.set_layer("trail_seconds", value))
        layers.addWidget(self.trail)
        layout.addLayout(layers)
        self.seek = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.seek.setRange(0, 10000)
        self.seek.sliderReleased.connect(self.seek_to)
        layout.addWidget(self.seek)
        self.status = QtWidgets.QLabel("Opening source…")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setCentralWidget(root)
        self._layout_ready = True
        self.change_market_view(0)
        self.set_layout()
        QtGui.QShortcut(QtGui.QKeySequence("Space"), self, activated=self.play.click)
        QtGui.QShortcut(QtGui.QKeySequence("Escape"), self, activated=self.showNormal)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(33)
        self.clear()
        if start_worker:
            self.worker.start()

    def set_layout(self, *_):
        if self._layout_pending or not self._layout_ready:
            return
        self._layout_pending = True
        QtCore.QTimer.singleShot(0, self.apply_layout)

    def apply_layout(self):
        self._layout_pending = False
        mode = self.layout_mode.currentData()
        portrait = mode == "portrait" or (mode == "auto" and self.height() > self.width() and self.height() >= 1150)
        if portrait != self._portrait_layout:
            self._portrait_layout = portrait
            self.split.setOrientation(QtCore.Qt.Orientation.Vertical if portrait else QtCore.Qt.Orientation.Horizontal)
            extent = self.height() if portrait else self.width()
            share = .44 if portrait else .30
            self.split.setSizes([int(extent*share), int(extent*(1-share))])
        margins = (0, 12, 0, 0) if portrait else (12, 0, 0, 0)
        self.panels.layout().setContentsMargins(*margins)
        chart_orientation = (QtCore.Qt.Orientation.Horizontal if not portrait and self.market_scroll.viewport().width() >= 700
                             else QtCore.Qt.Orientation.Vertical)
        if self.charts.orientation() != chart_orientation:
            self.charts.setOrientation(chart_orientation)
            self.charts.setSizes([500, 500])
        self.panels.layout().invalidate()
        self.panels.layout().activate()
        self.panels.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_layout_ready", False):
            self.set_layout()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Resize and getattr(self, "_layout_ready", False):
            self.set_layout()
        return super().eventFilter(watched, event)

    def send(self, name, value=None):
        if not self.worker.command(name, value):
            self.status.setText("Controls busy — please retry")

    def set_layer(self, name, value):
        setattr(self.view, name, value)
        self.view.update()

    def select_prediction(self, mid):
        self.view.prediction_ball = mid
        self.view.update()

    def change_market_view(self, index):
        self.view.show_prediction = index == 0
        self.view.update()
        for i in range(self.tabs.count()):
            policy = (QtWidgets.QSizePolicy.Policy.Preferred if i == index else
                      QtWidgets.QSizePolicy.Policy.Ignored)
            self.tabs.widget(i).setSizePolicy(policy, policy)
        self.tabs.updateGeometry()
        self.set_layout()

    def toggle_pause(self, paused):
        self.send("pause", paused)
        self.play.setText("Play" if paused else "Pause")

    def reset(self):
        self.send("reset")
        self.clear()
        self.play.setChecked(False)
        self.toggle_pause(False)

    def open_movie(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open movie", "", "Movies (*.mov *.MOV *.mp4 *.mkv);;All files (*)")
        if path:
            self.change_source("movie", path)

    def change_source(self, kind, value):
        if not self.worker.is_alive():
            # Source-open errors are recoverable through the same UI.
            self.worker = Worker(self.config, kind, value)
            self.worker.start()
        else:
            self.send("source", (kind, value))
        self.clear()
        self.play.setChecked(False)
        self.toggle_pause(False)

    def seek_to(self):
        if self.last_payload and self.last_payload["kind"] == "movie":
            target = self.seek.value()/10000*self.last_payload["duration"]
            self.send("seek", target)
            self.clear()
            self.play.setChecked(False)
            self.toggle_pause(False)

    def fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def clear(self):
        self.last_payload = None
        self.view.image = None
        self.view.update()
        self.source_label.setText("Source changing · temporal history cleared")
        self.seek.setEnabled(False)
        for mid in range(5):
            for col, text in enumerate([f"● {mid}", "—", "—", "—", "lost", "0"]):
                self.ticker.setItem(mid, col, QtWidgets.QTableWidgetItem(text))
        for curve in self.curves:
            curve.setData([], [])
        self.candles.set_data([], COLORS[0], self.config.candle_seconds)
        self.trial.clear()

    def poll(self):
        try:
            payload = self.worker.output.get_nowait()
        except Empty:
            return
        if "error" in payload:
            self.status.setText(payload["error"])
            self.play.setChecked(True)
            self.play.setText("Play")
            return
        if "clear" in payload:
            self.clear()
            return
        if "eof" in payload and "state" not in payload:
            self.status.setText("End of movie · source clock stopped · Reset to replay")
            return
        self.last_payload = payload
        state = payload["state"]
        self.view.set_frame(payload["image"], state)
        label = "SYNTHETIC TEST" if payload["kind"] == "synthetic" else payload["kind"].upper()
        self.source_label.setText(f"{label}   /   {state['source']}")
        self.seek.setEnabled(payload["kind"] == "movie" and payload["duration"] > 0)
        if not self.seek.isSliderDown() and payload["duration"]:
            self.seek.setValue(int(state["timestamp"]/payload["duration"]*10000))
        self.status.setText(f"SOURCE {state['timestamp']:.3f}s   ·   ANALYSIS {payload['analysis_ms']:.1f}ms   ·   "
                            f"SKIPPED {payload['dropped']}   ·   CAMERA REPLACED {payload.get('camera_dropped', 0)}   ·   DISPLAY REPLACED {payload['display_dropped']}"
                            + (f"   ·   PLAYBACK RESYNCS {payload['playback_resyncs']}" if payload.get("playback_resyncs") else "")
                            + ("   ·   END OF MOVIE" if payload.get("eof") else ""))
        self.refresh_panels()

    def refresh_panels(self, *_):
        if not self.last_payload:
            return
        state = self.last_payload["state"]
        now = state["timestamp"]
        self.trial.update_state(state)
        interval = self.config.candle_seconds
        for mid, history in state["histories"].items():
            last = history[-1] if history else None
            cs = state["candles"][mid]
            count = cs[-1]["count"] if cs and cs[-1]["start"] <= now < cs[-1]["start"]+interval else 0
            values = [f"● {mid}", f"{last['index']:.2f}" if last else "—",
                      f"{last['normalised'][1]:.3f}" if last else "—",
                      f"{now-last['timestamp']:.2f}s" if last else "—", state["states"][mid], str(count)]
            for col, value in enumerate(values):
                item = self.ticker.item(mid, col)
                item.setText(value)
                item.setForeground(QtGui.QColor(COLORS[mid] if col in (0, 1) else "#a2afbf"))
            self.curves[mid].setData([s["timestamp"] for s in history], [s["index"] for s in history])
        mid = self.candle_ball.currentIndex()
        self.candles.set_data(state["candles"][mid], COLORS[mid], interval)
        self.empty_candles.setVisible(not state["candles"][mid])
        if not state["candles"][mid]:
            self.empty_candles.setPos(max(15, now-15), self.config.index_base+self.config.index_gain*.5)
            self.ohlc.setYRange(self.config.index_base, self.config.index_base+self.config.index_gain, padding=.1)
        else:
            self.ohlc.enableAutoRange(axis="y", enable=True)
        left, right = max(0, now-30), max(30, now+1)
        self.history.setXRange(left, right, padding=0)
        self.ohlc.setXRange(left, right, padding=0)

    def shutdown(self):
        self.timer.stop()
        self.worker.stopping.set()
        if self.worker.is_alive():
            self.worker.join(timeout=2)

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
