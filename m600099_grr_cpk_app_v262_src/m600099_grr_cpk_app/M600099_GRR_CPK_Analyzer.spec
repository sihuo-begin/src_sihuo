# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip', 'easyocr', 'easyocr.easyocr', 'easyocr.config', 'easyocr.detection', 'easyocr.recognition', 'easyocr.utils', 'scipy', 'scipy.stats', 'sklearn', 'openpyxl', 'openpyxl.cell', 'openpyxl.styles', 'openpyxl.utils', 'pptx', 'pptx.util', 'pptx.enum', 'PIL', 'PIL.Image', 'pandas', 'numpy', 'xlrd']
hiddenimports += collect_submodules('easyocr')
hiddenimports += collect_submodules('PIL')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Production_Related/B15/src_sihuo/m600099_grr_cpk_app_v262_src/m600099_grr_cpk_app/utils/__init__.py', 'utils'), ('C:/Production_Related/B15/src_sihuo/m600099_grr_cpk_app_v262_src/m600099_grr_cpk_app/utils/config.py', 'utils'), ('C:/Production_Related/B15/src_sihuo/m600099_grr_cpk_app_v262_src/m600099_grr_cpk_app/report/GR_R_Template.xlsx', 'report'), ('C:/Production_Related/B15/src_sihuo/m600099_grr_cpk_app_v262_src/m600099_grr_cpk_app/report/AR_R_Template.xlsx', 'report')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib.tests', 'numpy.tests', 'pandas.tests', 'scipy.tests', 'PIL.tests'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='M600099_GRR_CPK_Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='M600099_GRR_CPK_Analyzer',
)
