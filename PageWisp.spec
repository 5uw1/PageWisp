# -*- mode: python ; coding: utf-8 -*-

excluded_qt_modules = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtNetwork",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtTest",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtUiTools",
    "PySide6.QtXml",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("LICENSE", "."), ("THIRD_PARTY_NOTICES.md", "."), ("licenses", "licenses")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_qt_modules,
    noarchive=False,
    optimize=0,
)

# hook-PySide6 bundles these regardless of the excludes above (they are not
# real load-time dependencies of Qt6Core/Gui/Widgets - verified via pefile
# import table inspection). Drop them to keep the build lightweight.
_unused_binary_markers = (
    "opengl32sw.dll",
    "qt6quick.dll",
    "qt6qml.dll",
    "qt6qmlmodels.dll",
    "qt6qmlmeta.dll",
    "qt6qmlworkerscript.dll",
    "qt6virtualkeyboard.dll",
    "qt6pdf.dll",
    "qt6network.dll",
    "qt6opengl.dll",
    "plugins\\networkinformation\\",
    "plugins\\platforminputcontexts\\",
    "plugins/networkinformation/",
    "plugins/platforminputcontexts/",
)
a.binaries = [
    b for b in a.binaries
    if not any(marker in b[0].lower() for marker in _unused_binary_markers)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PageWisp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PageWisp",
)
