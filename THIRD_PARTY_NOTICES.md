# Third-party notices and credits

PageWisp is built on the work of these open-source projects. Thank you to everyone who maintains them.

## Shipped with PageWisp

These components are included in the Windows release (`PageWisp-<version>-windows.zip`).

| Component | Used for | License |
|---|---|---|
| [PyMuPDF](https://github.com/pymupdf/pymupdf) by Artifex | Python bindings to MuPDF: rendering, text, search, links | AGPL-3.0 (or Artifex commercial) |
| [MuPDF](https://mupdf.com/) by Artifex, bundled inside PyMuPDF | The PDF engine itself | AGPL-3.0 (or Artifex commercial) |
| [Qt 6](https://www.qt.io/) by The Qt Company | User interface toolkit | LGPL-3.0 |
| [PySide6 / Qt for Python](https://pyside.org) and Shiboken6 | Python bindings to Qt | LGPL-3.0 |
| [Python](https://www.python.org/) (CPython runtime) | Runs the application | PSF License 2.0 |
| [PyInstaller](https://pyinstaller.org) bootloader | Starts the packaged app | GPL-2.0-or-later with the PyInstaller bootloader exception, which allows distributing apps under any license |
| [Lucide](https://lucide.dev/) icons | Toolbar and interface icons | ISC; some icons derive from [Feather](https://feathericons.com/) (MIT). Full text in [licenses/LUCIDE.txt](licenses/LUCIDE.txt) |
| Microsoft Visual C++ runtime (`VCRUNTIME140*.dll`, `MSVCP140*.dll`) | Required by Python and Qt on Windows | Microsoft Visual C++ Redistributable license |

MuPDF itself bundles further open-source libraries (font, image and compression libraries such as
FreeType, HarfBuzz, libjpeg, OpenJPEG, JBIG2Dec, lcms2 and zlib). Their notices ship with MuPDF; see
the [MuPDF source](https://git.ghostscript.com/?p=mupdf.git) (`thirdparty/` directory).

### License notes

- **AGPL-3.0:** because PyMuPDF and MuPDF are AGPL-licensed, PageWisp is released under the
  AGPL-3.0 too. Its complete source is at <https://github.com/5uw1/PageWisp>.
- **LGPL-3.0 (Qt, PySide6):** the Windows build ships the Qt and PySide6 libraries as separate,
  unmodified DLL/PYD files in the `_internal` folder, so they can be replaced with other compatible
  versions. Their source is available from [Qt](https://download.qt.io/official_releases/qt/) and
  [Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/).
- The exact versions in each release are listed in its SBOM
  (`PageWisp-<version>-sbom.cdx.json`, CycloneDX format, attached to the GitHub Release).

## Used to build and test (not shipped)

| Tool | Used for | License |
|---|---|---|
| [uv](https://github.com/astral-sh/uv) | Python and dependency management | MIT or Apache-2.0 |
| [PyInstaller](https://pyinstaller.org) and [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | Packaging the Windows app | GPL-2.0-or-later with exception; Apache-2.0 / GPL-2.0 |
| [pytest](https://pytest.org) | Test runner | MIT |
| [pytest-qt](https://github.com/pytest-dev/pytest-qt) | Driving the Qt interface in tests | MIT |
| [Ruff](https://github.com/astral-sh/ruff) | Linting | MIT |
| [Bandit](https://github.com/PyCQA/bandit) | Security linting | Apache-2.0 |
| [pip-audit](https://github.com/pypa/pip-audit) | Dependency vulnerability scanning | Apache-2.0 |
| [GitHub Actions](https://github.com/features/actions) | Continuous integration and releases | n/a |
