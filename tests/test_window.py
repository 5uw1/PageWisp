"""Theme, persistence, recent files and other window-level behaviour."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.main_window import MainWindow


def test_theme_toggle_persists(window, settings):
    start = window.dark
    QTest.keyClick(window, Qt.Key_D, Qt.ControlModifier)
    assert window.dark is not start
    assert settings.value("dark", type=bool) is not start


def test_invert_colors(window, open_pdf, text_pdf):
    viewer = open_pdf(text_pdf)
    QTest.keyClick(window, Qt.Key_I, Qt.ControlModifier)
    assert viewer.invert and window.act_invert.isChecked()
    QTest.keyClick(window, Qt.Key_I, Qt.ControlModifier)
    assert not viewer.invert


def test_sidebar_preference_persists(qtbot, window, open_pdf, text_pdf, settings):
    open_pdf(text_pdf)
    QTest.keyClick(window, Qt.Key_B, Qt.ControlModifier)
    assert not window.dock.isVisible()
    window.close()
    assert settings.value("sidebar", type=bool) is False

    reopened = MainWindow(settings=settings)
    qtbot.addWidget(reopened)
    assert not reopened.act_sidebar.isChecked()


def test_recent_files(window, open_pdf, text_pdf, links_pdf):
    open_pdf(text_pdf)
    open_pdf(links_pdf)
    recent = window._recent_files()
    assert recent[:2] == [str(links_pdf), str(text_pdf)]
    buttons = [window.welcome.recent_box.itemAt(i).widget().toolTip()
               for i in range(window.welcome.recent_box.count())]
    assert buttons[:2] == recent[:2]


def test_recent_files_skip_missing(window, settings, tmp_path):
    settings.setValue("recent", [str(tmp_path / "gone.pdf")])
    assert window._recent_files() == []


def test_open_invalid_file_shows_error(window, monkeypatch, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    errors = []
    monkeypatch.setattr("app.main_window.QMessageBox.critical",
                        staticmethod(lambda *a, **k: errors.append(a[1])))
    window.open_file(str(bad))
    assert errors == ["Can't open file"]
    assert window.doc is None


def test_shortcut_tooltips(window):
    assert window.act_open.toolTip() == "Open  (Ctrl+O)"
    assert "←" in window.act_prev.toolTip()


@pytest.mark.parametrize("name", ["act_open", "act_find", "act_fit_width", "act_fit_height", "act_help"])
def test_toolbar_actions_have_icons(window, name):
    assert not getattr(window, name).icon().isNull()


def test_close_during_pending_resize_render(window, open_pdf, text_pdf, qtbot):
    """Closing right after a resize must not render pages from the closed document."""
    open_pdf(text_pdf)
    window.resize(1300, 760)
    window.close()
    qtbot.wait(300)  # past the resize debounce; pytest-qt fails on any exception
    assert window.doc is None
