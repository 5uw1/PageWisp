import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from conftest import THAI_FONT
from helpers import char_point, click, double_click, drag, find_char, page_point


@pytest.fixture
def viewer(open_pdf, selection_pdf):
    return open_pdf(selection_pdf)


def test_select_single_letter(viewer):
    b = find_char(viewer, 0, "brown")
    drag(viewer, 0, char_point(viewer, 0, b, "L"), char_point(viewer, 0, b, "R"))
    assert viewer.selected_text() == "b"


def test_select_part_of_word(viewer):
    b = find_char(viewer, 0, "brown")
    drag(viewer, 0, char_point(viewer, 0, b + 1, "L"), char_point(viewer, 0, b + 3, "R"))
    assert viewer.selected_text() == "row"


def test_backwards_drag(viewer):
    b = find_char(viewer, 0, "brown")
    drag(viewer, 0, char_point(viewer, 0, b + 3, "R"), char_point(viewer, 0, b + 1, "L"))
    assert viewer.selected_text() == "row"


def test_select_across_lines(viewer):
    start = char_point(viewer, 0, find_char(viewer, 0, "fox"), "L")
    end = char_point(viewer, 0, find_char(viewer, 0, "sec"), "R")
    drag(viewer, 0, start, end)
    assert viewer.selected_text() == "fox\ns"


def test_select_across_pages(viewer):
    start = char_point(viewer, 0, find_char(viewer, 0, "here"), "L")
    end = char_point(viewer, 1, find_char(viewer, 1, "Next") + 3, "R")
    drag(viewer, 0, start, end, end_page=1)
    text = viewer.selected_text()
    assert text.startswith("here")
    assert text.endswith("\n\nNext")


def test_selection_paints_highlight_rects(viewer):
    b = find_char(viewer, 0, "brown")
    drag(viewer, 0, char_point(viewer, 0, b, "L"), char_point(viewer, 0, b + 4, "R"))
    assert len(viewer.labels[0].sel_rects) == 1
    assert viewer.labels[1].sel_rects == []


def test_double_click_selects_word(viewer):
    double_click(viewer, 0, char_point(viewer, 0, find_char(viewer, 0, "line") + 1))
    assert viewer.selected_text() == "line"


def test_triple_click_selects_line(viewer):
    pos = char_point(viewer, 0, find_char(viewer, 0, "line") + 1)
    double_click(viewer, 0, pos)
    QTest.mousePress(viewer.labels[0], Qt.LeftButton, Qt.NoModifier, pos)
    QTest.mouseRelease(viewer.labels[0], Qt.LeftButton, Qt.NoModifier, pos)
    assert viewer.selected_text() == "second line here"


def test_double_click_on_blank_area_selects_nothing(viewer):
    double_click(viewer, 0, page_point(viewer, 400, 600))
    assert not viewer.has_selection()


def test_plain_click_clears_selection(viewer, qtbot):
    pos = char_point(viewer, 0, find_char(viewer, 0, "brown"))
    double_click(viewer, 0, pos)
    assert viewer.has_selection()
    qtbot.wait(QApplication.doubleClickInterval() + 50)  # so the click isn't a triple-click
    click(viewer, 0, pos)
    assert not viewer.has_selection()


def test_ctrl_c_copies_selection(viewer):
    double_click(viewer, 0, char_point(viewer, 0, find_char(viewer, 0, "brown")))
    QApplication.clipboard().clear()
    QTest.keyClick(viewer, Qt.Key_C, Qt.ControlModifier)
    assert QApplication.clipboard().text() == "brown"


@pytest.mark.skipif(not os.path.exists(THAI_FONT), reason="needs Tahoma for Thai text")
class TestThai:
    def test_single_character(self, viewer):
        i = find_char(viewer, 0, "ส")
        drag(viewer, 0, char_point(viewer, 0, i, "L"), char_point(viewer, 0, i, "R"))
        assert viewer.selected_text() == "ส"

    def test_double_click_selects_up_to_space(self, viewer):
        double_click(viewer, 0, char_point(viewer, 0, find_char(viewer, 0, "ท")))
        assert viewer.selected_text() == "ทดสอบ"
