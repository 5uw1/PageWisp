import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymupdf
import pytest
from PySide6.QtCore import QSettings

from app.main_window import MainWindow

THAI_FONT = r"C:\Windows\Fonts\tahoma.ttf"


@pytest.fixture(scope="session")
def text_pdf(tmp_path_factory):
    """8 pages of body text, "Findme" once per page, and a 3-entry outline."""
    path = tmp_path_factory.mktemp("pdfs") / "text.pdf"
    doc = pymupdf.open()
    for i in range(8):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f"Sample document - Page {i + 1}", fontsize=24)
        page.insert_text((72, 150), "Findme keyword appears here.", fontsize=14)
        for j in range(20):
            page.insert_text((72, 230 + j * 20), f"Body line {j + 1} of page {i + 1}.", fontsize=11)
    doc.set_toc([[1, "Chapter 1", 1], [2, "Section 1.1", 2], [1, "Chapter 2", 4]])
    doc.save(path)
    return path


@pytest.fixture(scope="session")
def selection_pdf(tmp_path_factory):
    path = tmp_path_factory.mktemp("pdfs") / "selection.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Hello brown fox", fontsize=14)
    page.insert_text((72, 130), "second line here", fontsize=14)
    if os.path.exists(THAI_FONT):
        page.insert_text((72, 170), "สวัสดีครับ ทดสอบ", fontsize=16,
                         fontname="tahoma", fontfile=THAI_FONT)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72, 100), "Next page text", fontsize=14)
    doc.save(path)
    return path


@pytest.fixture(scope="session")
def links_pdf(tmp_path_factory):
    """Page 1 has an internal link (to page 4), a web link and a launch-file link."""
    path = tmp_path_factory.mktemp("pdfs") / "links.pdf"
    doc = pymupdf.open()
    for i in range(5):
        doc.new_page(width=595, height=842).insert_text((72, 100), f"Page {i + 1}", fontsize=20)
    p0 = doc[0]
    p0.insert_text((72, 150), "Go to chapter on page 4", fontsize=14)
    p0.insert_link({"kind": pymupdf.LINK_GOTO, "from": pymupdf.Rect(70, 136, 260, 154),
                    "page": 3, "to": pymupdf.Point(0, 300)})
    p0.insert_text((72, 190), "Visit example.com", fontsize=14)
    p0.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(70, 176, 200, 194),
                    "uri": "https://example.com/"})
    p0.insert_text((72, 230), "Run file link", fontsize=14)
    p0.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(70, 216, 200, 234),
                    "uri": "file:///C:/Windows/notepad.exe"})
    doc.save(path)
    return path


@pytest.fixture
def settings(tmp_path):
    """Isolated settings file so tests never touch the real user settings."""
    return QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)


@pytest.fixture
def window(qtbot, settings):
    w = MainWindow(settings=settings)
    w.resize(1100, 760)
    w.show()
    qtbot.addWidget(w)
    w.activateWindow()
    qtbot.waitUntil(w.isActiveWindow, timeout=2000)
    yield w
    w.thumbnail_list.stop_worker()


@pytest.fixture
def open_pdf(window, qtbot):
    """Open a PDF and wait until the first page is rendered at its fitted zoom."""
    def _open(path):
        window.open_file(str(path))
        viewer = window.viewer
        qtbot.waitUntil(lambda: viewer.labels and viewer.labels[0].rendered, timeout=3000)
        qtbot.wait(150)
        return viewer
    return _open
