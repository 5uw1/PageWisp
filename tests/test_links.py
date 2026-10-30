import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from app import main_window
from helpers import click, drag, page_point

INTERNAL = (100, 145)
WEB = (100, 185)
FILE = (100, 225)


@pytest.fixture
def opened(monkeypatch):
    """Capture URLs instead of launching a browser/program."""
    urls = []
    monkeypatch.setattr(main_window.QDesktopServices, "openUrl",
                        staticmethod(lambda url: urls.append(url.toString())))
    return urls


@pytest.fixture
def viewer(open_pdf, links_pdf):
    return open_pdf(links_pdf)


def test_hover_shows_hand_and_tooltip(viewer):
    lbl = viewer.labels[0]
    viewer.hover(lbl, page_point(viewer, *INTERNAL))
    assert lbl.cursor().shape() == Qt.PointingHandCursor
    assert lbl.toolTip() == "Go to page 4"
    viewer.hover(lbl, page_point(viewer, *WEB))
    assert lbl.toolTip() == "https://example.com/"
    viewer.hover(lbl, page_point(viewer, 400, 500))
    assert lbl.cursor().shape() == Qt.IBeamCursor
    assert lbl.toolTip() == ""


def test_internal_link_and_back(window, viewer, qtbot):
    click(viewer, 0, page_point(viewer, *INTERNAL))
    qtbot.waitUntil(lambda: viewer.current_page == 3)
    window.act_back.trigger()
    qtbot.waitUntil(lambda: viewer.current_page == 0)


def test_mouse_back_button(viewer, qtbot):
    click(viewer, 0, page_point(viewer, *INTERNAL))
    qtbot.waitUntil(lambda: viewer.current_page == 3)
    pos = QPointF(20, 20)
    for kind in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
        ev = QMouseEvent(kind, pos, viewer.viewport().mapToGlobal(pos), Qt.BackButton,
                         Qt.NoButton, Qt.NoModifier)
        QApplication.sendEvent(viewer.viewport(), ev)
    qtbot.waitUntil(lambda: viewer.current_page == 0)


def test_web_link_opens_without_prompt(viewer, opened, monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("web links must not prompt")
    monkeypatch.setattr(main_window.QMessageBox, "question", staticmethod(fail))
    click(viewer, 0, page_point(viewer, *WEB))
    assert opened == ["https://example.com/"]


@pytest.mark.parametrize("answer, expect_open", [(QMessageBox.No, False), (QMessageBox.Yes, True)])
def test_file_link_asks_first(viewer, opened, monkeypatch, answer, expect_open):
    asked = []
    monkeypatch.setattr(main_window.QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(a[2]) or answer))
    click(viewer, 0, page_point(viewer, *FILE))
    assert len(asked) == 1 and "notepad.exe" in asked[0]
    assert opened == (["file:///C:/Windows/notepad.exe"] if expect_open else [])


def test_dragging_over_link_selects_instead_of_following(viewer, opened, qtbot):
    drag(viewer, 0, page_point(viewer, 80, 145), page_point(viewer, 200, 145))
    qtbot.wait(100)
    assert viewer.current_page == 0
    assert viewer.has_selection()
    assert opened == []
