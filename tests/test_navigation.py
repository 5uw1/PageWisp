import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


@pytest.fixture
def viewer(open_pdf, text_pdf):
    return open_pdf(text_pdf)


def test_welcome_screen_before_opening(window):
    assert window.stack.currentWidget() is window.welcome
    assert not window.dock.isVisible()
    assert not window.act_zoom_in.isEnabled()


def test_opening_shows_document(window, viewer):
    assert window.stack.currentWidget() is viewer
    assert window.dock.isVisible()
    assert window.page_count_label.text().strip() == "/ 8"
    assert window.thumbnail_list.count() == 8
    assert window.outline_tree.topLevelItemCount() == 2


@pytest.mark.parametrize("keys, expected", [
    ([Qt.Key_Right], 2),
    ([Qt.Key_Right, Qt.Key_Right], 3),
    ([Qt.Key_Right, Qt.Key_Right, Qt.Key_Left], 2),
    ([Qt.Key_Left], 1),  # clamped at the first page
])
def test_arrow_keys_change_page(viewer, qtbot, keys, expected):
    for key in keys:
        QTest.keyClick(viewer, key)
        qtbot.wait(80)
    qtbot.waitUntil(lambda: viewer.current_page + 1 == expected)


def test_first_and_last_page(window, viewer, qtbot):
    QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
    qtbot.waitUntil(lambda: viewer.current_page == 7)
    QTest.keyClick(window, Qt.Key_Home, Qt.ControlModifier)
    qtbot.waitUntil(lambda: viewer.current_page == 0)


def test_go_to_page(window, viewer, qtbot):
    QTest.keyClick(window, Qt.Key_G, Qt.ControlModifier)
    assert window.page_spin.hasFocus()
    QTest.keyClicks(window.page_spin, "5")
    QTest.keyClick(window.page_spin, Qt.Key_Return)
    qtbot.waitUntil(lambda: viewer.current_page == 4)
    assert window.page_spin.value() == 5


def test_toolbar_prev_next(window, viewer, qtbot):
    window.act_next.trigger()
    qtbot.waitUntil(lambda: viewer.current_page == 1)
    window.act_prev.trigger()
    qtbot.waitUntil(lambda: viewer.current_page == 0)


def test_space_scrolls_one_screen(viewer):
    bar = viewer.verticalScrollBar()
    QTest.keyClick(viewer, Qt.Key_Space)
    assert bar.value() == viewer.viewport().height() - 40
    QTest.keyClick(viewer, Qt.Key_Space, Qt.ShiftModifier)
    assert bar.value() == 0


def test_outline_click_navigates(window, viewer, qtbot):
    chapter2 = window.outline_tree.topLevelItem(1)
    window.outline_tree.itemClicked.emit(chapter2, 0)
    qtbot.waitUntil(lambda: viewer.current_page == 3)


def test_thumbnail_click_navigates(window, viewer, qtbot):
    window.thumbnail_list.setCurrentRow(6)
    qtbot.waitUntil(lambda: viewer.current_page == 6)


def test_lazy_rendering_unloads_far_pages(viewer):
    rendered = [lbl.index for lbl in viewer.labels if lbl.has_image]
    assert 0 in rendered
    assert 7 not in rendered
