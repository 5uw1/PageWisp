from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from app.viewer import BORDER


def page_point(viewer, x, y):
    """Label-local pixel position of a point given in PDF points."""
    z = viewer.zoom
    return QPoint(int(x * z) + BORDER, int(y * z) + BORDER)


def find_char(viewer, page, text, start=0):
    chars, _ = viewer.doc.get_text_layout(page)
    return "".join(c[4] for c in chars).index(text, start)


def char_point(viewer, page, index, side="mid"):
    """Point inside character `index`: near its left edge, right edge or middle."""
    chars, _ = viewer.doc.get_text_layout(page)
    x0, y0, x1, y1 = chars[index][:4]
    fx = {"L": 0.15, "R": 0.85, "mid": 0.5}[side]
    return page_point(viewer, x0 + (x1 - x0) * fx, (y0 + y1) / 2)


def drag(viewer, page, start, end, end_page=None):
    """Press on `page` at `start`, move to `end` (on `end_page`, default same), release."""
    lbl = viewer.labels[page]
    target = viewer.labels[page if end_page is None else end_page]
    end_local = lbl.mapFromGlobal(target.mapToGlobal(end))
    QTest.mousePress(lbl, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(lbl, end_local)
    QTest.mouseRelease(lbl, Qt.LeftButton, Qt.NoModifier, end_local)


def click(viewer, page, pos):
    QTest.mouseClick(viewer.labels[page], Qt.LeftButton, Qt.NoModifier, pos)


def double_click(viewer, page, pos):
    QTest.mouseDClick(viewer.labels[page], Qt.LeftButton, Qt.NoModifier, pos)
