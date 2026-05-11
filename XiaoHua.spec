# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['xiaohua_main.py'],
    pathex=[],
    binaries=[],
    datas=[('imgs', 'imgs'), ('xiaohua_get_ai_action.txt', '.'), ('xiaohua_screenshot.py', '.'), ('xiaohua_model_do_work.py', '.'), ('config.json', '.'), ('f:\\XiaoHua\\new_venv\\Lib\\site-packages\\pyautogui', 'pyautogui'), ('f:\\XiaoHua\\new_venv\\Lib\\site-packages\\pyscreeze', 'pyscreeze'), ('f:\\XiaoHua\\new_venv\\Lib\\site-packages\\mouseinfo', 'mouseinfo'), ('f:\\XiaoHua\\new_venv\\Lib\\site-packages\\PyTweening', 'PyTweening')],
    hiddenimports=['xiaohua_screenshot', 'xiaohua_model_do_work', 'pyautogui', 'pyscreeze', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageGrab', 'mouseinfo', 'PyTweening'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XiaoHua',
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
    icon=['favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='XiaoHua',
)
