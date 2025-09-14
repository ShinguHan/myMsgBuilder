# log_converter.spec

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['log_converter.py'],
    pathex=[],
    binaries=[],
    datas=[
        # log_converter.py가 필요로 하는 설정 파일들을 추가합니다.
        # 실행 파일 내부의 루트('.')에 위치시킵니다.
        ('profile.json', '.'),
        ('message_key_rules.json', '.')
    ],
    hiddenimports=[
        'pandas' # log_importer -> universal_parser가 내부적으로 pandas를 사용할 수 있으므로 추가
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='log_converter',  # 실행 파일 이름
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,         # ⭐ 콘솔(CLI) 프로그램이므로 반드시 True로 설정!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='log_converter',
)