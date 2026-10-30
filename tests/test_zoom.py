import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.main_window import SCREEN_SCALE
from app.viewer import MARGIN


@pytest.fixture
def viewer(open_pdf, text_pdf):
    return open_pdf(text_pdf)


def pct(window):
    return window.zoom_combo.currentText()


def test_opens_in_auto_fit_width(window, viewer):
    assert viewer.fit_mode == "width"
    assert window.act_fit_width.isChecked()
    assert abs(viewer.labels[0].width() - (viewer.viewport().width() - 2 * MARGIN - 4)) <= 1


def test_auto_fit_width_follows_window_resize(window, viewer, qtbot):
    before = viewer.zoom
    window.resize(1400, 760)
    qtbot.waitUntil(lambda: viewer.zoom > before)
    assert viewer.fit_mode == "width"


def test_auto_fit_follows_sidebar_toggle(window, viewer, qtbot):
    before = viewer.zoom
    QTest.keyClick(window, Qt.Key_B, Qt.ControlModifier)
    qtbot.waitUntil(lambda: viewer.zoom > before)


@pytest.mark.parametrize("zoom_action", ["zoom_in", "zoom_out", "wheel", "typed", "preset"])
def test_manual_zoom_turns_auto_fit_off(window, viewer, qtbot, zoom_action):
    if zoom_action == "zoom_in":
        QTest.keyClick(window, Qt.Key_Equal, Qt.ControlModifier)
    elif zoom_action == "zoom_out":
        QTest.keyClick(window, Qt.Key_Minus, Qt.ControlModifier)
    elif zoom_action == "wheel":
        ev = QWheelEvent(QPointF(50, 50), QPointF(50, 50), QPoint(0, 0), QPoint(0, 120),
                         Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(viewer.viewport(), ev)
    elif zoom_action == "typed":
        window.zoom_combo.setEditText("150")
        window._on_zoom_typed()
    else:
        window.zoom_combo.activated.emit(window.zoom_combo.findText("200%"))
    assert viewer.fit_mode is None
    assert not window.act_fit_width.isChecked()

    zoom = viewer.zoom
    window.resize(1400, 760)
    qtbot.wait(300)
    assert viewer.zoom == zoom  # resize keeps a manual zoom


def test_ctrl_0_restores_auto_fit_width(window, viewer):
    QTest.keyClick(window, Qt.Key_Equal, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_0, Qt.ControlModifier)
    assert viewer.fit_mode == "width" and window.act_fit_width.isChecked()


def test_clicking_active_fit_button_keeps_it_on(window, viewer):
    window.act_fit_width.trigger()
    assert viewer.fit_mode == "width" and window.act_fit_width.isChecked()


def test_fit_height(window, viewer, qtbot):
    QTest.keyClick(window, Qt.Key_8, Qt.ControlModifier)
    assert viewer.fit_mode == "height" and window.act_fit_height.isChecked()
    assert not window.act_fit_width.isChecked()

    def fills_height():
        expected = viewer.viewport().height() - 2 * MARGIN - 4
        return abs(viewer.labels[0].height() - expected) <= 1

    assert fills_height()
    window.resize(1100, 950)
    qtbot.waitUntil(fills_height)


def test_fit_page(window, viewer):
    QTest.keyClick(window, Qt.Key_9, Qt.ControlModifier)
    assert viewer.fit_mode == "page" and window.act_fit_page.isChecked()
    lbl = viewer.labels[0]
    assert lbl.height() <= viewer.viewport().height() - 2 * MARGIN
    assert lbl.width() <= viewer.viewport().width() - 2 * MARGIN


def test_actual_size(window, viewer):
    QTest.keyClick(window, Qt.Key_1, Qt.ControlModifier)
    assert viewer.zoom == pytest.approx(SCREEN_SCALE)
    assert pct(window) == "100%"


@pytest.mark.parametrize("typed, shown", [
    ("137", "137%"),
    ("85%", "85%"),
    ("62.5", "62.5%"),
    ("62,5", "62.5%"),
    ("999", "400%"),  # clamped to max
    ("3", "10%"),     # clamped to min, and not autocompleted to "300%"
])
def test_type_exact_zoom(window, viewer, typed, shown):
    QTest.keyClick(window, Qt.Key_L, Qt.ControlModifier)
    assert window.zoom_combo.lineEdit().hasFocus()
    QTest.keyClicks(window.zoom_combo.lineEdit(), typed)
    QTest.keyClick(window.zoom_combo.lineEdit(), Qt.Key_Return)
    assert pct(window) == shown
    assert viewer.hasFocus()


def test_invalid_zoom_text_reverts(window, viewer):
    window.zoom_combo.setEditText("")
    window._on_zoom_typed()
    assert pct(window) == "100%" or pct(window).endswith("%")
    assert viewer.fit_mode == "width"


def test_validator_rejects_letters(window, viewer):
    edit = window.zoom_combo.lineEdit()
    edit.selectAll()
    QTest.keyClicks(edit, "abc")
    assert "abc" not in edit.text()


@pytest.mark.parametrize("preset", ["50%", "125%", "400%"])
def test_zoom_presets(window, viewer, preset):
    window.zoom_combo.activated.emit(window.zoom_combo.findText(preset))
    assert pct(window) == preset


def test_resize_keeps_page_images(window, viewer, qtbot):
    """Resizing in fit mode must not blank pages (the old flicker bug)."""
    shown = [lbl for lbl in viewer.labels if lbl.has_image]
    assert shown
    for width in range(1080, 900, -30):
        window.resize(width, 760)
        QApplication.processEvents()
        assert all(lbl.pixmap() is not None and not lbl.pixmap().isNull() for lbl in shown)
    qtbot.waitUntil(lambda: not viewer._resizing and viewer.labels[0].rendered)
