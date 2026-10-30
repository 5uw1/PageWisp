import time
import unicodedata

from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QKeySequence
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QApplication, QMenu

MARGIN = 12
SPACING = 8
BORDER = 1
DRAG_THRESHOLD = 4
SELECTION_COLOR = QColor(51, 144, 255, 90)
MIN_ZOOM = 0.1 * 96 / 72  # 10% at 96 dpi
MAX_ZOOM = 4.0 * 96 / 72  # 400% at 96 dpi


def _same_row(a, b):
    overlap = min(a[3], b[3]) - max(a[1], b[1])
    return overlap > 0.5 * min(a[3] - a[1], b[3] - b[1])


def _group_by_line(chars):
    groups = []
    for c in chars:
        if groups and groups[-1][-1][5] == c[5]:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups


def _bbox(chars):
    return (min(c[0] for c in chars), min(c[1] for c in chars),
            max(c[2] for c in chars), max(c[3] for c in chars))


def _rect_distance(rect, px, py):
    dx = max(rect[0] - px, 0, px - rect[2])
    dy = max(rect[1] - py, 0, py - rect[3])
    return dx * dx + dy * dy


def _is_word_char(c):
    return not c.isspace() and unicodedata.category(c)[0] != "P"


class PageLabel(QLabel):
    def __init__(self, viewer, index, width, height):
        super().__init__()
        self.viewer = viewer
        self.index = index
        self.rendered = False
        self.has_image = False
        self.sel_rects = []
        self.setScaledContents(True)
        self.setFixedSize(int(width), int(height))
        self.setStyleSheet("background-color: white; border: 1px solid #cccccc;")
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.IBeamCursor)
        self.setMouseTracking(True)  # for link hover cursor

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.sel_rects:
            painter = QPainter(self)
            z = self.viewer.zoom
            for x0, y0, x1, y1 in self.sel_rects:
                painter.fillRect(
                    QRectF(x0 * z + BORDER, y0 * z + BORDER, (x1 - x0) * z, (y1 - y0) * z),
                    SELECTION_COLOR,
                )
            painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.viewer.selection_press(self, event.position().toPoint())
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.viewer.selection_double_click(self, event.position().toPoint())
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.viewer.selection_move(event.globalPosition().toPoint())
        else:
            self.viewer.hover(self, event.position().toPoint())
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.viewer.selection_release(self, event.position().toPoint())
        else:
            super().mouseReleaseEvent(event)


class PageViewer(QScrollArea):
    page_changed = Signal(int)
    zoom_changed = Signal(float)
    page_step = Signal(int)
    external_link = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignHCenter)
        self.setFrameShape(QScrollArea.NoFrame)

        self.current_page = 0
        self.invert = False

        self.container = QWidget()
        self.container.setObjectName("pageContainer")
        self.vlayout = QVBoxLayout(self.container)
        self.vlayout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        self.vlayout.setSpacing(SPACING)
        self.setWidget(self.container)

        self.doc = None
        self.zoom = 1.0
        self.fit_mode = "width"  # "width" / "height" / "page" re-fit on resize; None = manual
        self.labels = []
        self.page_sizes_pt = []

        self.search_matches = {}
        self.current_match = None

        self._sel_anchor = None  # (page, word_index) where the drag started
        self._sel_range = None  # normalized ((page, word), (page, word))
        self._sel_press_pos = None
        self._sel_active = False
        self._last_double_click = None  # (time, container pos) for triple-click detection
        self._press_link = None
        self._history = []  # (page, y in points) positions to return to after following links
        self.setFocusPolicy(Qt.StrongFocus)

        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(60)
        self._update_timer.timeout.connect(self.update_visible_pages)

        self._resizing = False
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._finish_resize)

        self.verticalScrollBar().valueChanged.connect(self._schedule_update)

    def load(self, doc):
        self.doc = doc
        self.page_sizes_pt = [doc.page_size(i) for i in range(doc.page_count)]
        self.search_matches = {}
        self.current_match = None
        self._sel_anchor = self._sel_range = None
        self._history = []
        self._rebuild_labels()

    def clear_document(self):
        self._update_timer.stop()
        self._resize_timer.stop()
        self._resizing = False
        self.doc = None
        self.page_sizes_pt = []
        self.search_matches = {}
        self.current_match = None
        self._sel_anchor = self._sel_range = None
        self._rebuild_labels()

    def _rebuild_labels(self):
        for lbl in self.labels:
            self.vlayout.removeWidget(lbl)
            lbl.deleteLater()
        self.labels = []
        for i, (w, h) in enumerate(self.page_sizes_pt):
            lbl = PageLabel(self, i, w * self.zoom, h * self.zoom)
            self.vlayout.addWidget(lbl, alignment=Qt.AlignHCenter)
            self.labels.append(lbl)
        QTimer.singleShot(0, self, self.update_visible_pages)

    def set_zoom(self, zoom, fit_mode=None):
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        old_zoom = self.zoom
        self.zoom = zoom
        self.fit_mode = fit_mode
        # Keep the old images (stretched by setScaledContents) until the
        # sharp re-render lands, so zooming/resizing doesn't flash blank pages.
        for lbl, (w, h) in zip(self.labels, self.page_sizes_pt, strict=True):
            lbl.setFixedSize(int(w * zoom), int(h * zoom))
            lbl.rendered = False
        if old_zoom > 0 and abs(zoom - old_zoom) > 1e-6:
            bar = self.verticalScrollBar()
            target = int(bar.value() * zoom / old_zoom)
            QTimer.singleShot(0, bar, lambda: bar.setValue(target))
        QTimer.singleShot(0, self, self.update_visible_pages)
        self.zoom_changed.emit(zoom)

    def set_invert(self, enabled):
        self.invert = enabled
        for lbl in self.labels:
            lbl.rendered = False
        self.update_visible_pages()

    def fit_page(self, keep_page=True):
        self._fit_to_view("page", keep_page)

    def fit_height(self, keep_page=True):
        self._fit_to_view("height", keep_page)

    def _fit_to_view(self, mode, keep_page):
        if not self.page_sizes_pt:
            return
        w0, h0 = self.page_sizes_pt[self.current_page]
        vw = self.viewport().width() - 2 * MARGIN - 4
        vh = self.viewport().height() - 2 * MARGIN - 4
        if w0 <= 0 or h0 <= 0:
            return
        page = self.current_page
        self.set_zoom(vh / h0 if mode == "height" else min(vw / w0, vh / h0), fit_mode=mode)
        if keep_page:
            QTimer.singleShot(50, self, lambda: self.goto_page(page))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            dy = event.angleDelta().y()
            if dy:
                self.set_zoom(self.zoom * (1.1 ** (dy / 120)))
            event.accept()
            return
        super().wheelEvent(event)

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.15)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.15)

    def fit_width(self):
        if not self.page_sizes_pt:
            return
        vw = self.viewport().width() - 2 * MARGIN - 4
        w0 = self.page_sizes_pt[0][0]
        if w0 > 0:
            self.set_zoom(vw / w0, fit_mode="width")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode:
            self._resizing = True
            self._resize_timer.start()
            if self.fit_mode == "width":
                self.fit_width()
            else:
                self._fit_to_view(self.fit_mode, keep_page=False)

    def _finish_resize(self):
        self._resizing = False
        self.update_visible_pages()

    def _schedule_update(self):
        self._update_timer.start()

    def update_visible_pages(self):
        if not self.doc or not self.labels or self._resizing:
            return
        top =self.verticalScrollBar().value()
        bottom = top + self.viewport().height()
        buffer = max(self.viewport().height(), 400)
        current = 0
        for lbl in self.labels:
            y = lbl.y()
            h = lbl.height()
            visible = (y + h >= top - buffer) and (y <= bottom + buffer)
            if visible and not lbl.rendered:
                self._render_label(lbl)
            elif not visible and lbl.has_image:
                lbl.clear()
                lbl.has_image = False
                lbl.rendered = False
            if y <= top + 10:
                current = lbl.index
        self.current_page = current
        self.page_changed.emit(current)

    def _render_label(self, lbl):
        img = self.doc.render_page(lbl.index, self.zoom)
        if self.invert:
            img.invertPixels()
        pm = QPixmap.fromImage(img)
        matches = self.search_matches.get(lbl.index)
        if matches:
            pm = pm.copy()
            painter = QPainter(pm)
            for mi, rect in enumerate(matches):
                r = QRectF(
                    rect.x0 * self.zoom,
                    rect.y0 * self.zoom,
                    (rect.x1 - rect.x0) * self.zoom,
                    (rect.y1 - rect.y0) * self.zoom,
                )
                is_current = self.current_match == (lbl.index, mi)
                color = QColor(255, 140, 0, 160) if is_current else QColor(255, 255, 0, 100)
                painter.fillRect(r, color)
            painter.end()
        lbl.setPixmap(pm)
        lbl.rendered = True
        lbl.has_image = True

    def invalidate_page(self, index):
        if 0 <= index < len(self.labels):
            self.labels[index].rendered = False

    # ---------- text selection ----------

    def selection_press(self, lbl, pos):
        self.setFocus()
        cpos = lbl.mapTo(self.container, pos)
        if self._is_triple_click(cpos):
            self._last_double_click = None
            self._select_line_at(lbl, pos)
            return
        self._set_selection(None)
        self._sel_active = False
        self._sel_press_pos = cpos
        self._press_link = self.link_at(lbl, pos)
        caret =self._caret_at(lbl.index, self._to_page_pt(lbl, pos))
        self._sel_anchor = None if caret is None else (lbl.index, caret)

    def selection_release(self, lbl, pos):
        link, self._press_link = self._press_link, None
        if link and not self._sel_active and self.link_at(lbl, pos) == link:
            self.follow_link(link)

    # ---------- links ----------

    def link_at(self, lbl, pos):
        if not self.doc:
            return None
        px, py = self._to_page_pt(lbl, pos)
        for rect, kind, target in self.doc.get_links(lbl.index):
            if rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]:
                return kind, target
        return None

    def hover(self, lbl, pos):
        link = self.link_at(lbl, pos)
        lbl.setCursor(Qt.PointingHandCursor if link else Qt.IBeamCursor)
        if not link:
            lbl.setToolTip("")
        elif link[0] == "uri":
            lbl.setToolTip(link[1])
        else:
            lbl.setToolTip(f"Go to page {link[1][0] + 1}")

    def follow_link(self, link):
        kind, target = link
        if kind == "uri":
            self.external_link.emit(target)
            return
        page = self.current_page
        if 0 <= page < len(self.labels):
            offset = (self.verticalScrollBar().value() - self.labels[page].y()) / self.zoom
            self._history.append((page, offset))
        self.goto_point(target[0], target[1], margin=20)

    def goto_point(self, page, y, margin=0):
        if 0 <= page < len(self.labels):
            value = self.labels[page].y() + int(y * self.zoom) - margin
            self.verticalScrollBar().setValue(max(0, value))

    def go_back(self):
        if self._history:
            self.goto_point(*self._history.pop())

    def mousePressEvent(self, event):
        if event.button() == Qt.BackButton:
            self.go_back()
            return
        super().mousePressEvent(event)

    def selection_double_click(self, lbl, pos):
        self._last_double_click = (time.monotonic(), lbl.mapTo(self.container, pos))
        idx = self._char_at(lbl, pos)
        if idx is None:
            return
        chars, _ = self.doc.get_text_layout(lbl.index)
        line = chars[idx][5]

        def same_word(i):
            return chars[i][5] == line and _is_word_char(chars[i][4])

        if not same_word(idx):
            self._select_span(lbl.index, idx, idx + 1)
            return
        start, end = idx, idx + 1
        while start > 0 and same_word(start - 1):
            start -= 1
        while end < len(chars) and same_word(end):
            end += 1
        self._select_span(lbl.index, start, end)

    def _select_span(self, page, start, end):
        self._sel_anchor = (page, start)
        self._sel_active = False
        self._set_selection(((page, start), (page, end)))

    def _is_triple_click(self, cpos):
        if not self._last_double_click:
            return False
        t, p = self._last_double_click
        return (time.monotonic() - t < QApplication.doubleClickInterval() / 1000
                and (cpos - p).manhattanLength() < DRAG_THRESHOLD * 2)

    def _select_line_at(self, lbl, pos):
        idx = self._char_at(lbl, pos)
        if idx is None:
            return
        chars, lines = self.doc.get_text_layout(lbl.index)
        line = lines[chars[idx][5]]
        self._select_span(lbl.index, line[4], line[5])

    def _char_at(self, lbl, pos, slack=3):
        """Index of the character under pos (within `slack` points), else None."""
        px, py = self._to_page_pt(lbl, pos)
        idx = self._nearest_char(lbl.index, (px, py))
        if idx is None:
            return None
        x0, y0, x1, y1 = self.doc.get_text_layout(lbl.index)[0][idx][:4]
        if x0 - slack <= px <= x1 + slack and y0 - slack <= py <= y1 + slack:
            return idx
        return None

    def selection_move(self, global_pos):
        if self._sel_anchor is None:
            return
        cpos = self.container.mapFromGlobal(global_pos)
        if not self._sel_active:
            if (cpos - self._sel_press_pos).manhattanLength() < DRAG_THRESHOLD:
                return
            self._sel_active = True

        vp_y = self.viewport().mapFromGlobal(global_pos).y()
        bar = self.verticalScrollBar()
        if vp_y < 0:
            bar.setValue(bar.value() - 24)
        elif vp_y > self.viewport().height():
            bar.setValue(bar.value() + 24)

        lbl = self._label_at(cpos)
        if lbl is None:
            return
        caret = self._caret_at(lbl.index, self._to_page_pt(lbl, cpos - lbl.pos()))
        if caret is None:
            return
        a, b = sorted([self._sel_anchor, (lbl.index, caret)])
        self._set_selection((a, b) if a != b else None)

    def _label_at(self, cpos):
        if not self.labels:
            return None
        for lbl in self.labels:
            if lbl.y() <= cpos.y() < lbl.y() + lbl.height():
                return lbl
        return min(self.labels, key=lambda lb: abs(lb.y() + lb.height() / 2 - cpos.y()))

    def _to_page_pt(self, lbl, pos):
        return ((pos.x() - BORDER) / self.zoom, (pos.y() - BORDER) / self.zoom)

    def _nearest_char(self, page, pt):
        chars, lines = self.doc.get_text_layout(page)
        if not lines:
            return None
        px, py = pt
        line = min(lines, key=lambda ln: _rect_distance(ln, px, py))
        return min(range(line[4], line[5]), key=lambda i: _rect_distance(chars[i], px, py))

    def _caret_at(self, page, pt):
        """Caret position (insertion index) nearest to pt: before or after the closest char."""
        idx = self._nearest_char(page, pt)
        if idx is None:
            return None
        x0, _, x1, _ = self.doc.get_text_layout(page)[0][idx][:4]
        return idx + 1 if pt[0] > (x0 + x1) / 2 else idx

    def _selected_chars(self, page):
        rng = self._sel_range
        if rng is None or not (rng[0][0] <= page <= rng[1][0]):
            return []
        chars, _ = self.doc.get_text_layout(page)
        start = rng[0][1] if page == rng[0][0] else 0
        end = rng[1][1] if page == rng[1][0] else len(chars)
        return chars[start:end]

    def _set_selection(self, rng):
        old = self._sel_range
        if rng == old:
            return
        self._sel_range = rng
        pages = set()
        for r in (old, rng):
            if r:
                pages.update(range(r[0][0], r[1][0] + 1))
        for p in pages:
            lbl = self.labels[p]
            lbl.sel_rects = [_bbox(g) for g in _group_by_line(self._selected_chars(p))]
            lbl.update()

    def has_selection(self):
        return self._sel_range is not None

    def selected_text(self):
        if not self._sel_range:
            return ""
        pages = []
        for p in range(self._sel_range[0][0], self._sel_range[1][0] + 1):
            text, prev = "", None
            for group in _group_by_line(self._selected_chars(p)):
                box = _bbox(group)
                if prev is not None:
                    # PDF "lines" sharing a visual row are joined with a space.
                    text = text.rstrip() + (" " if _same_row(prev, box) else "\n")
                text += "".join(c[4] for c in group)
                prev = box
            pages.append(text.strip())
        return "\n\n".join(pages)

    def copy_selection(self):
        text = self.selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
            return
        key, mods = event.key(), event.modifiers()
        if key == Qt.Key_Space:
            bar = self.verticalScrollBar()
            step = self.viewport().height() - 40
            bar.setValue(bar.value() + (-step if mods & Qt.ShiftModifier else step))
            return
        if (key in (Qt.Key_Left, Qt.Key_Right) and not mods
                and self.horizontalScrollBar().maximum() == 0):
            self.page_step.emit(-1 if key == Qt.Key_Left else 1)
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act = menu.addAction("Copy")
        act.setEnabled(self.has_selection())
        act.triggered.connect(self.copy_selection)
        menu.exec(event.globalPos())

    def goto_page(self, index):
        if 0 <= index < len(self.labels):
            self.verticalScrollBar().setValue(self.labels[index].y())

    def goto_rect(self, index, rect):
        if 0 <= index < len(self.labels):
            y = self.labels[index].y() + int(rect.y0 * self.zoom) - 60
            self.verticalScrollBar().setValue(max(0, y))
