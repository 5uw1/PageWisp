import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.version import VERSION


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PageWisp")
    app.setApplicationVersion(VERSION)

    window = MainWindow()
    window.show()

    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        window.open_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
