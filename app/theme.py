DARK = dict(
    bg="#1e1f22", surface="#2b2d31", viewer="#141517", text="#e3e5e8", muted="#8b919a",
    hover="#33353b", pressed="#3f4249", accent="#5b9bff", border="#303338", danger="#f26d78",
    on_accent="#0b1220",
)
LIGHT = dict(
    bg="#f6f7f9", surface="#ffffff", viewer="#e6e8ec", text="#1f2328", muted="#6b7280",
    hover="#e9ebef", pressed="#dde0e6", accent="#2563eb", border="#d9dce2", danger="#d92d3a",
    on_accent="#ffffff",
)


def stylesheet(c, combo_arrow=""):
    return f"""
QComboBox::down-arrow {{ image: url("{combo_arrow}"); width: 12px; height: 12px; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QWidget {{ color: {c['text']}; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
           padding: 4px 6px; }}

QToolBar {{ background: {c['bg']}; border: none; border-bottom: 1px solid {c['border']};
           padding: 4px 8px; spacing: 2px; }}
QToolBar::separator {{ background: {c['border']}; width: 1px; margin: 6px 8px; }}
QToolButton {{ background: transparent; border: none; border-radius: 6px; padding: 6px; }}
QToolButton:hover {{ background: {c['hover']}; }}
QToolButton:pressed, QToolButton:checked {{ background: {c['pressed']}; }}
QToolButton:disabled {{ color: {c['muted']}; }}
QToolButton::menu-indicator {{ image: none; }}
QComboBox {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 6px;
    padding: 3px 6px; selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QComboBox:focus {{ border-color: {c['accent']}; }}
QComboBox:disabled {{ color: {c['muted']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']};
    selection-background-color: {c['hover']}; selection-color: {c['text']}; outline: none;
    padding: 4px; }}

QSpinBox, QLineEdit {{ background: {c['surface']}; border: 1px solid {c['border']};
    border-radius: 6px; padding: 4px 6px; selection-background-color: {c['accent']};
    selection-color: {c['on_accent']}; }}
QSpinBox:focus, QLineEdit:focus {{ border-color: {c['accent']}; }}
QSpinBox:disabled {{ color: {c['muted']}; }}
QLineEdit[noResults="true"] {{ border-color: {c['danger']}; }}
QLabel#muted {{ color: {c['muted']}; }}

#searchBar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}

QScrollArea {{ border: none; background: {c['viewer']}; }}
#pageContainer {{ background: {c['viewer']}; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['pressed']}; min-height: 32px; border-radius: 4px;
    margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['pressed']}; min-width: 32px; border-radius: 4px;
    margin: 2px; }}
QScrollBar::handle:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QDockWidget {{ border: none; }}
QTabWidget::pane {{ border: none; border-top: 1px solid {c['border']}; }}
QTabBar {{ background: {c['bg']}; }}
QTabBar::tab {{ background: transparent; padding: 8px 18px; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ background: {c['hover']}; }}
QTabBar::tab:selected {{ border-bottom: 2px solid {c['accent']}; }}

QListWidget, QTreeWidget {{ background: {c['bg']}; border: none; outline: none; }}
QListWidget::item {{ border-radius: 8px; padding: 6px; color: {c['muted']}; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QListWidget::item:selected {{ background: {c['pressed']}; color: {c['text']}; }}
QTreeWidget::item {{ padding: 4px 2px; border-radius: 4px; }}
QTreeWidget::item:hover {{ background: {c['hover']}; }}
QTreeWidget::item:selected {{ background: {c['pressed']}; color: {c['text']}; }}

QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px;
        padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {c['hover']}; }}
QMenu::item:disabled {{ color: {c['muted']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}

QPushButton {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px;
              padding: 7px 14px; }}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton#primary {{ background: {c['accent']}; color: {c['on_accent']}; border: none;
                      font-weight: 600; padding: 9px 20px; }}
QPushButton#primary:hover {{ background: {c['accent']}; }}
QPushButton#recent {{ background: transparent; border: none; text-align: left; padding: 5px 10px;
                     color: {c['muted']}; }}
QPushButton#recent:hover {{ background: {c['hover']}; color: {c['text']}; }}

QLabel#welcomeTitle {{ font-size: 20px; font-weight: 600; }}
QLabel#kbd {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 4px;
             padding: 2px 6px; font-family: Consolas, monospace; }}
"""
