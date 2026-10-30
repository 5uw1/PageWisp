import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from helpers import double_click, char_point, find_char


@pytest.fixture
def viewer(open_pdf, text_pdf):
    return open_pdf(text_pdf)


def search(window, qtbot, text):
    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)
    QTest.keyClicks(window.search_edit, text)
    qtbot.waitUntil(lambda: window.search_count.text() != "", timeout=2000)


def test_ctrl_f_opens_search(window, viewer):
    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)
    assert window.search_bar.isVisible()
    assert window.search_edit.hasFocus()


def test_search_as_you_type(window, viewer, qtbot):
    search(window, qtbot, "Findme")
    assert window.search_count.text() == "1/8"
    assert viewer.current_match == (0, 0)
    assert sorted(viewer.search_matches) == list(range(8))


def test_enter_and_shift_enter_cycle_matches(window, viewer, qtbot):
    search(window, qtbot, "Findme")
    QTest.keyClick(window.search_edit, Qt.Key_Return)
    assert window.search_count.text() == "2/8"
    qtbot.waitUntil(lambda: viewer.current_page == 1)
    QTest.keyClick(window.search_edit, Qt.Key_Return, Qt.ShiftModifier)
    assert window.search_count.text() == "1/8"
    QTest.keyClick(window.search_edit, Qt.Key_Return, Qt.ShiftModifier)
    assert window.search_count.text() == "8/8"  # wraps around


def test_f3_next_match(window, viewer, qtbot):
    search(window, qtbot, "Findme")
    QTest.keyClick(window, Qt.Key_F3)
    assert window.search_count.text() == "2/8"
    QTest.keyClick(window, Qt.Key_F3, Qt.ShiftModifier)
    assert window.search_count.text() == "1/8"


def test_no_results(window, viewer, qtbot):
    search(window, qtbot, "zzzz")
    assert window.search_count.text() == "0"
    assert window.search_edit.property("noResults") is True


def test_escape_closes_and_clears(window, viewer, qtbot):
    search(window, qtbot, "Findme")
    QTest.keyClick(window.search_edit, Qt.Key_Escape)
    assert not window.search_bar.isVisible()
    assert viewer.search_matches == {}
    assert viewer.current_match is None


def test_ctrl_f_prefills_selected_text(window, viewer):
    double_click(viewer, 0, char_point(viewer, 0, find_char(viewer, 0, "keyword") + 2))
    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)
    assert window.search_edit.text() == "keyword"
