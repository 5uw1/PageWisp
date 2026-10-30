import os
import tempfile

from PySide6.QtCore import Qt, QRegularExpression, QSettings, QSize, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDockWidget, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSpinBox,
    QStackedWidget, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from . import icons
from .pdf_document import PdfDocument
from .sidebar import OutlineTree, ThumbnailList
from .theme import DARK, LIGHT, stylesheet
from .version import VERSION
from .viewer import PageViewer

SCREEN_SCALE = 96 / 72  # 100% == 96 dpi, PDF points are 72 dpi
ZOOM_PRESETS = (50, 75, 100, 125, 150, 200, 300, 400)
FIT_ITEMS = ["Fit width", "Fit height", "Fit page"]  # order matches _on_zoom_preset
MIN_ZOOM_PCT = 10
MAX_ZOOM_PCT = 400
MAX_RECENT = 6
ICON_SIZE = 20


class SearchEdit(QLineEdit):
    next_requested = Signal()
    prev_requested = Signal()
    closed = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                self.prev_requested.emit()
            else:
                self.next_requested.emit()
            return
        if event.key() == Qt.Key_Escape:
            self.closed.emit()
            return
        super().keyPressEvent(event)


class WelcomeView(QWidget):
    open_requested = Signal()
    file_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignCenter)
        self._layout.setSpacing(14)

        self.icon_label = QLabel(alignment=Qt.AlignCenter)
        self.title = QLabel("Open a PDF", alignment=Qt.AlignCenter)
        self.title.setObjectName("welcomeTitle")
        self.open_button = QPushButton("  Open")
        self.open_button.setObjectName("primary")
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.clicked.connect(self.open_requested)
        self.hint = QLabel("Ctrl+O   ·   drop a file", alignment=Qt.AlignCenter)
        self.hint.setObjectName("muted")

        for w in (self.icon_label, self.title, self.open_button, self.hint):
            self._layout.addWidget(w, alignment=Qt.AlignHCenter)

        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(0)
        self._layout.addSpacing(10)
        self._layout.addLayout(self.recent_box)

    def refresh(self, colors, recent):
        self.icon_label.setPixmap(icons.pixmap("file", colors["muted"], 72))
        self.open_button.setIcon(icons.icon("folder", colors["on_accent"]))
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for path in recent:
            btn = QPushButton(os.path.basename(path))
            btn.setObjectName("recent")
            btn.setToolTip(path)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumWidth(260)
            btn.clicked.connect(lambda _=False, p=path: self.file_requested.emit(p))
            self.recent_box.addWidget(btn, alignment=Qt.AlignHCenter)


class ShortcutsDialog(QDialog):
    def __init__(self, parent, rows):
        super().__init__(parent)
        self.setWindowTitle(f"PageWisp {VERSION} — Shortcuts")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        grid = QGridLayout(self)
        grid.setContentsMargins(20, 16, 20, 16)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        half = (len(rows) + 1) // 2
        for i, (label, keys) in enumerate(rows):
            col = 0 if i < half else 3
            row = i if i < half else i - half
            grid.addWidget(QLabel(label), row, col)
            keys_row = QHBoxLayout()
            keys_row.setSpacing(4)
            for k in keys:
                kbd = QLabel(k)
                kbd.setObjectName("kbd")
                keys_row.addWidget(kbd)
            keys_row.addStretch()
            holder = QWidget()
            holder.setLayout(keys_row)
            grid.addWidget(holder, row, col + 1)
        grid.setColumnMinimumWidth(2, 24)


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle("PageWisp")
        self.resize(1100, 800)
        self.setAcceptDrops(True)

        self.settings = settings if settings is not None else QSettings("PageWisp", "PageWisp")
        self.dark = self.settings.value("dark", True, type=bool)
        self.colors = DARK if self.dark else LIGHT

        self.doc = None
        self.match_list = []
        self.current_match_idx = -1
        self._icon_targets = []  # (setter, icon name) re-colored on theme change
        self._help_actions = []

        self.viewer = PageViewer()
        self.viewer.page_changed.connect(self._on_page_changed)
        self.viewer.zoom_changed.connect(self._on_zoom_changed)
        self.viewer.external_link.connect(self.open_external_link)
        self.viewer.page_step.connect(self._step_page)

        self.welcome = WelcomeView()
        self.welcome.open_requested.connect(self.open_file_dialog)
        self.welcome.file_requested.connect(self.open_file)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.viewer)

        self._build_actions()
        self._build_sidebar()
        self._build_toolbar()
        self._build_search_bar()

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.search_bar)
        lay.addWidget(self.stack)
        self.setCentralWidget(central)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.run_search)

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self._sidebar_wanted = self.settings.value("sidebar", True, type=bool)
        self.act_sidebar.setChecked(self._sidebar_wanted)
        self._update_sidebar()

        self.apply_theme()
        self._set_document_actions_enabled(False)
        self.stack.setCurrentWidget(self.welcome)

    # ---------- actions ----------

    def _act(self, icon_name, text, shortcuts=(), slot=None, *, checkable=False, hint=""):  # noqa: PLR0913
        act = QAction(text, self)
        act.setCheckable(checkable)
        keys = [QKeySequence(s) for s in shortcuts]
        tip = text
        if keys:
            act.setShortcuts(keys)
            tip += f"  ({keys[0].toString(QKeySequence.NativeText)})"
            self._help_actions.append(act)
        elif hint:
            tip += f"  ({hint})"
        act.setToolTip(tip)
        if slot:
            if checkable:
                act.toggled.connect(slot)
            else:
                act.triggered.connect(lambda *_: slot())
        self.addAction(act)
        if icon_name:
            self._icon_targets.append((act.setIcon, icon_name))
        return act

    def _build_actions(self):
        v = self.viewer
        self.act_open = self._act("folder", "Open", ["Ctrl+O"], self.open_file_dialog)
        self.act_sidebar = self._act("sidebar", "Sidebar", ["Ctrl+B"], checkable=True)
        self.act_sidebar.triggered.connect(self._on_sidebar_toggled)
        self.act_prev = self._act("left", "Previous page", slot=self.prev_page, hint="←")
        self.act_next = self._act("right", "Next page", slot=self.next_page, hint="→")
        self.act_first = self._act(None, "First page", ["Ctrl+Home"], lambda: v.goto_page(0))
        self.act_last = self._act(None, "Last page", ["Ctrl+End"],
                                  lambda: v.goto_page(len(v.labels) - 1))
        self.act_goto = self._act(None, "Go to page", ["Ctrl+G"], self.focus_page_edit)
        self.act_back = self._act(None, "Back (after link)", ["Alt+Left"], v.go_back)
        self.act_zoom_out = self._act("zoom_out", "Zoom out", ["Ctrl+-"], v.zoom_out)
        self.act_zoom_in = self._act("zoom_in", "Zoom in", ["Ctrl++", "Ctrl+="], v.zoom_in)
        # Checkable only to show that auto-fit is active; any manual zoom unchecks it.
        self.act_fit_width = self._act("fit_width", "Auto-fit width", ["Ctrl+0"], checkable=True)
        self.act_fit_width.triggered.connect(lambda *_: v.fit_width())
        self.act_fit_height = self._act("fit_height", "Auto-fit height", ["Ctrl+8"], checkable=True)
        self.act_fit_height.triggered.connect(lambda *_: v.fit_height())
        self.act_fit_page = self._act(None, "Auto-fit page", ["Ctrl+9"], checkable=True)
        self.act_fit_page.triggered.connect(lambda *_: v.fit_page())
        self.act_actual = self._act(None, "Actual size", ["Ctrl+1"],
                                    lambda: v.set_zoom(SCREEN_SCALE))
        self.act_zoom_edit = self._act(None, "Type zoom %", ["Ctrl+L"], self.focus_zoom_edit)
        self.act_find = self._act("search", "Find", ["Ctrl+F"], self.show_search_bar)
        self.act_find_next = self._act("down", "Next match", ["F3"], self.search_next)
        self.act_find_prev = self._act("up", "Previous match", ["Shift+F3"], self.search_prev)
        self.act_find_close = self._act("close", "Close", slot=self.hide_search_bar, hint="Esc")
        self.act_invert = self._act("contrast", "Invert colors", ["Ctrl+I"], v.set_invert,
                                    checkable=True)
        self.act_theme = self._act(None, "Light / dark theme", ["Ctrl+D"], self.toggle_theme)
        self.act_fullscreen = self._act(None, "Full screen", ["F11"], self.toggle_fullscreen)
        self.act_help = self._act("help", "Shortcuts", ["F1"], self.show_shortcuts)

    def _refresh_icons(self):
        c = self.colors
        for setter, name in self._icon_targets:
            setter(icons.icon(name, c["text"], c["muted"]))
        self.act_theme.setIcon(icons.icon("sun" if self.dark else "moon", c["text"], c["muted"]))
        self.search_icon.setPixmap(icons.pixmap("search", c["muted"], 16))

    # ---------- UI construction ----------

    def _build_sidebar(self):
        self.thumbnail_list = ThumbnailList()
        self.thumbnail_list.page_selected.connect(self.viewer.goto_page)

        self.outline_tree = OutlineTree()
        self.outline_tree.page_selected.connect(self.viewer.goto_page)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self.thumbnail_list, "")
        tabs.addTab(self.outline_tree, "")
        tabs.setTabToolTip(0, "Pages")
        tabs.setTabToolTip(1, "Outline")
        tabs.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self._icon_targets.append((lambda ic: tabs.setTabIcon(0, ic), "grid"))
        self._icon_targets.append((lambda ic: tabs.setTabIcon(1, ic), "list"))

        self.dock = QDockWidget(self)
        self.dock.setWidget(tabs)
        self.dock.setTitleBarWidget(QWidget())
        self.dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock.setMinimumWidth(170)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

    def _on_sidebar_toggled(self, on):
        self._sidebar_wanted = on
        self.dock.setVisible(on)

    def _update_sidebar(self):
        self.dock.setVisible(self.doc is not None and self._sidebar_wanted)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setContextMenuPolicy(Qt.PreventContextMenu)
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.addToolBar(tb)
        self.toolbar = tb

        tb.addAction(self.act_open)
        tb.addAction(self.act_sidebar)
        tb.addSeparator()

        tb.addAction(self.act_prev)
        self.page_spin = QSpinBox()
        self.page_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.page_spin.setAlignment(Qt.AlignCenter)
        self.page_spin.setFixedWidth(48)
        self.page_spin.setToolTip("Go to page  (Ctrl+G)")
        self.page_spin.setRange(1, 1)
        self.page_spin.editingFinished.connect(self._on_page_spin_finished)
        tb.addWidget(self.page_spin)
        self.page_count_label = QLabel(" / 0 ")
        self.page_count_label.setObjectName("muted")
        tb.addWidget(self.page_count_label)
        tb.addAction(self.act_next)
        tb.addSeparator()

        tb.addAction(self.act_zoom_out)
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setInsertPolicy(QComboBox.NoInsert)
        self.zoom_combo.setCompleter(None)  # don't autocomplete "3" into "300%"
        self.zoom_combo.setFixedWidth(84)
        self.zoom_combo.setToolTip("Zoom — type a percent and press Enter  (Ctrl+L)")
        self.zoom_combo.addItems(FIT_ITEMS + [f"{p}%" for p in ZOOM_PRESETS])
        self.zoom_combo.lineEdit().setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\s*\d{0,3}([.,]\d?)?\s*%?\s*|Fit.*"))
        )
        self.zoom_combo.activated.connect(self._on_zoom_preset)
        self.zoom_combo.lineEdit().returnPressed.connect(self._on_zoom_typed)
        tb.addWidget(self.zoom_combo)
        tb.addAction(self.act_zoom_in)
        tb.addAction(self.act_fit_width)
        tb.addAction(self.act_fit_height)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        tb.addAction(self.act_find)
        tb.addAction(self.act_invert)
        tb.addAction(self.act_theme)
        tb.addAction(self.act_help)

    def _build_search_bar(self):
        self.search_bar = QWidget()
        self.search_bar.setObjectName("searchBar")
        layout = QHBoxLayout(self.search_bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        self.search_icon = QLabel()
        layout.addWidget(self.search_icon)

        self.search_edit = SearchEdit()
        self.search_edit.setPlaceholderText("Find")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(360)
        self.search_edit.textChanged.connect(lambda _: self._search_timer.start())
        self.search_edit.next_requested.connect(self.search_next)
        self.search_edit.prev_requested.connect(self.search_prev)
        self.search_edit.closed.connect(self.hide_search_bar)
        layout.addWidget(self.search_edit)

        self.search_count = QLabel("")
        self.search_count.setObjectName("muted")
        self.search_count.setMinimumWidth(56)
        self.search_count.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.search_count)

        for act in (self.act_find_prev, self.act_find_next, self.act_find_close):
            btn = QToolButton()
            btn.setDefaultAction(act)
            btn.setIconSize(QSize(ICON_SIZE - 2, ICON_SIZE - 2))
            layout.addWidget(btn)
        layout.addStretch()
        self.search_bar.hide()

    # ---------- theme ----------

    def apply_theme(self):
        self.colors = DARK if self.dark else LIGHT
        # QSS can only load images from files, so write the themed chevron to temp.
        arrow = os.path.join(tempfile.gettempdir(), f"pagewisp_arrow_{'dark' if self.dark else 'light'}.png")
        icons.pixmap("down", self.colors["muted"], 12).save(arrow)
        self.setStyleSheet(stylesheet(self.colors, arrow.replace("\\", "/")))
        self._refresh_icons()
        self.welcome.refresh(self.colors, self._recent_files())

    def toggle_theme(self):
        self.dark = not self.dark
        self.settings.setValue("dark", self.dark)
        self.apply_theme()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()
        else:
            self.showFullScreen()
            self.toolbar.hide()

    def show_shortcuts(self):
        rows = [
            (a.text(), [s.toString(QKeySequence.NativeText) for s in a.shortcuts()])
            for a in self._help_actions
        ]
        rows += [
            ("Previous / next page", ["←", "→"]),
            ("Scroll one page", ["Space"]),
            ("Zoom", ["Ctrl", "Wheel"]),
            ("Copy selection", ["Ctrl+C"]),
            ("Select word / line", ["Double-click", "Triple-click"]),
            ("Close search / full screen", ["Esc"]),
        ]
        ShortcutsDialog(self, rows).exec()

    # ---------- recent files ----------

    def _recent_files(self):
        recent = self.settings.value("recent", [])
        if isinstance(recent, str):
            recent = [recent]
        return [p for p in (recent or []) if os.path.exists(p)]

    def _add_recent(self, path):
        path = os.path.abspath(path)
        recent = [p for p in self._recent_files() if p != path]
        self.settings.setValue("recent", [path, *recent[:MAX_RECENT - 1]])
        self.welcome.refresh(self.colors, self._recent_files())

    # ---------- document lifecycle ----------

    def _set_document_actions_enabled(self, enabled):
        for act in (self.act_sidebar, self.act_back, self.act_prev, self.act_next, self.act_first,
                    self.act_last, self.act_goto, self.act_zoom_in, self.act_zoom_out,
                    self.act_fit_width, self.act_fit_height, self.act_fit_page, self.act_actual,
                    self.act_zoom_edit, self.act_find, self.act_find_next, self.act_find_prev,
                    self.act_invert):
            act.setEnabled(enabled)
        self.page_spin.setEnabled(enabled)
        self.zoom_combo.setEnabled(enabled)

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF (*.pdf)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        try:
            doc = PdfDocument(path)
        except Exception as exc:
            QMessageBox.critical(self, "Can't open file", str(exc))
            return

        if self.doc:
            self.doc.close()
        self.doc = doc
        self.match_list = []
        self.current_match_idx = -1
        self.search_edit.clear()
        self.search_count.setText("")

        self.viewer.load(self.doc)
        self.thumbnail_list.load(path, self.doc.page_count)
        self.outline_tree.load(self.doc.get_toc())

        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, self.doc.page_count)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_count_label.setText(f" / {self.doc.page_count} ")

        self.setWindowTitle(f"{os.path.basename(path)} — PageWisp")
        self._add_recent(path)
        self._set_document_actions_enabled(True)
        self._update_sidebar()
        self.stack.setCurrentWidget(self.viewer)
        self.viewer.setFocus()

        QTimer.singleShot(0, self.viewer, self.viewer.fit_width)

    # ---------- navigation ----------

    def _clamp_page(self, index):
        return max(0, min(index, len(self.viewer.labels) - 1))

    def _on_page_changed(self, index):
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(index + 1)
        self.page_spin.blockSignals(False)
        self.thumbnail_list.set_current_page(index)

    def _on_page_spin_finished(self):
        target = self.page_spin.value() - 1
        if target != self.viewer.current_page:
            self.viewer.goto_page(target)
        self.viewer.setFocus()

    def _on_zoom_changed(self, zoom):
        pct = round(zoom / SCREEN_SCALE * 100, 1)
        self.zoom_combo.setEditText(f"{pct:g}%")
        self.act_fit_width.setChecked(self.viewer.fit_mode == "width")
        self.act_fit_height.setChecked(self.viewer.fit_mode == "height")
        self.act_fit_page.setChecked(self.viewer.fit_mode == "page")

    def _on_zoom_preset(self, index):
        fits = (self.viewer.fit_width, self.viewer.fit_height, self.viewer.fit_page)
        if index < len(fits):
            fits[index]()
        else:
            self.viewer.set_zoom(ZOOM_PRESETS[index - len(fits)] / 100 * SCREEN_SCALE)
        self.viewer.setFocus()

    def _on_zoom_typed(self):
        text = self.zoom_combo.currentText().strip().rstrip("%").replace(",", ".").strip()
        try:
            pct = float(text)
        except ValueError:
            pct = None
        if pct and pct > 0:
            pct = max(MIN_ZOOM_PCT, min(MAX_ZOOM_PCT, pct))
            self.viewer.set_zoom(pct / 100 * SCREEN_SCALE)
        # Always normalize the box back to the actual zoom (e.g. after clamping/bad input).
        self._on_zoom_changed(self.viewer.zoom)
        self.viewer.setFocus()

    def focus_zoom_edit(self):
        self.zoom_combo.setFocus()
        self.zoom_combo.lineEdit().selectAll()

    def open_external_link(self, url):
        qurl = QUrl(url)
        if qurl.scheme().lower() not in ("http", "https", "mailto"):
            answer = QMessageBox.question(
                self, "Open link?", f"This link may open another program:\n\n{url}"
            )
            if answer != QMessageBox.Yes:
                return
        QDesktopServices.openUrl(qurl)

    def focus_page_edit(self):
        self.page_spin.setFocus()
        self.page_spin.selectAll()

    def _step_page(self, delta):
        self.viewer.goto_page(self._clamp_page(self.viewer.current_page + delta))

    def prev_page(self):
        self._step_page(-1)

    def next_page(self):
        self._step_page(1)

    # ---------- search ----------

    def show_search_bar(self):
        self.search_bar.show()
        selected = self.viewer.selected_text().strip()
        if selected and "\n" not in selected and len(selected) < 80:
            self.search_edit.setText(selected)
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def hide_search_bar(self):
        self._search_timer.stop()
        self.search_bar.hide()
        self._clear_search_highlights()
        self.match_list = []
        self.current_match_idx = -1
        self.search_count.setText("")
        self.viewer.setFocus()

    def _set_no_results(self, flag):
        self.search_edit.setProperty("noResults", flag)
        self.search_edit.style().unpolish(self.search_edit)
        self.search_edit.style().polish(self.search_edit)

    def run_search(self):
        text = self.search_edit.text().strip()
        self._clear_search_highlights()
        self.match_list = []
        self.current_match_idx = -1
        self._set_no_results(False)

        if not text or not self.doc:
            self.search_count.setText("")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for i in range(self.doc.page_count):
                rects = self.doc.search_page(i, text)
                if rects:
                    self.viewer.search_matches[i] = rects
                    for mi in range(len(rects)):
                        self.match_list.append((i, mi))
        finally:
            QApplication.restoreOverrideCursor()

        if self.match_list:
            self._activate_match(0)
        else:
            self.search_count.setText("0")
            self._set_no_results(True)

    def _clear_search_highlights(self):
        affected = list(self.viewer.search_matches.keys())
        self.viewer.search_matches = {}
        self.viewer.current_match = None
        for i in affected:
            self.viewer.invalidate_page(i)
        self.viewer.update_visible_pages()

    def search_next(self):
        if not self.search_bar.isVisible():
            self.show_search_bar()
            return
        if not self.match_list:
            self.run_search()
            return
        self._activate_match(self.current_match_idx + 1)

    def search_prev(self):
        if not self.search_bar.isVisible():
            self.show_search_bar()
            return
        if not self.match_list:
            self.run_search()
            return
        self._activate_match(self.current_match_idx - 1)

    def _activate_match(self, idx):
        if not self.match_list:
            return
        idx %= len(self.match_list)
        prev = self.viewer.current_match
        self.current_match_idx = idx
        page_index, mi = self.match_list[idx]
        self.viewer.current_match = (page_index, mi)

        for p in {page_index} | ({prev[0]} if prev else set()):
            self.viewer.invalidate_page(p)

        rect = self.viewer.search_matches[page_index][mi]
        self.viewer.goto_rect(page_index, rect)
        QTimer.singleShot(0, self.viewer, self.viewer.update_visible_pages)
        self.search_count.setText(f"{idx + 1}/{len(self.match_list)}")

    # ---------- keyboard / drag-drop ----------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.search_bar.isVisible():
                self.hide_search_bar()
                return
            if self.isFullScreen():
                self.toggle_fullscreen()
                return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.open_file(path)
                break

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("sidebar", self._sidebar_wanted)
        self.thumbnail_list.stop_worker()
        if self.doc:
            self.viewer.clear_document()  # stop pending renders before closing the file
            self.doc.close()
            self.doc = None
        super().closeEvent(event)
