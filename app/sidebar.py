from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QListView, QTreeWidget, QTreeWidgetItem

from .pdf_document import PdfDocument

THUMB_WIDTH = 120


class ThumbnailWorker(QThread):
    thumbnail_ready = Signal(int, QImage)

    def __init__(self, path, count, width=THUMB_WIDTH):
        super().__init__()
        self.path = path
        self.count = count
        self.width = width
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        doc = PdfDocument(self.path)
        try:
            for i in range(self.count):
                if self._stop:
                    return
                w, _ = doc.page_size(i)
                zoom = self.width / w if w else 0.2
                img = doc.render_page(i, zoom)
                if self._stop:
                    return
                self.thumbnail_ready.emit(i, img)
        finally:
            doc.close()


class ThumbnailList(QListWidget):
    page_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.IconMode)
        self.setFlow(QListView.TopToBottom)
        self.setWrapping(False)
        self.setMovement(QListView.Static)
        self.setSpacing(4)
        self.setIconSize(QSize(THUMB_WIDTH, int(THUMB_WIDTH * 1.4)))
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(False)
        self.worker = None
        self.currentRowChanged.connect(self._on_row_changed)

    def load(self, path, page_count):
        self.stop_worker()
        self.clear()
        for i in range(page_count):
            item = QListWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignHCenter)
            item.setSizeHint(QSize(THUMB_WIDTH + 24, int(THUMB_WIDTH * 1.4) + 36))
            self.addItem(item)
        self.worker = ThumbnailWorker(path, page_count)
        self.worker.thumbnail_ready.connect(self._set_thumb)
        self.worker.start()

    def clear_all(self):
        self.stop_worker()
        self.clear()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        self.worker = None

    def _set_thumb(self, index, image):
        item = self.item(index)
        if item:
            item.setIcon(QIcon(QPixmap.fromImage(image)))

    def _on_row_changed(self, row):
        if row >= 0:
            self.page_selected.emit(row)

    def set_current_page(self, index):
        if self.currentRow() == index:
            return
        self.blockSignals(True)
        self.setCurrentRow(index)
        self.blockSignals(False)


class OutlineTree(QTreeWidget):
    page_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.itemClicked.connect(self._on_click)

    def load(self, toc):
        self.clear()
        stack = [(0, self.invisibleRootItem())]
        for level, title, page in toc:
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.UserRole, max(0, page - 1))
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            parent.addChild(item)
            stack.append((level, item))
        self.expandToDepth(0)

    def _on_click(self, item, _col):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self.page_selected.emit(page)
