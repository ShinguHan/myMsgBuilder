# main.spec

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 1. UI 스타일시트 파일 추가
        ('secs_simulator/ui/styles/apple_style.qss', 'secs_simulator/ui/styles'),
        
        # 2. engine 설정 파일 추가
        ('secs_simulator/engine/devices.json', 'secs_simulator/engine'),
        
        # 3. resources 폴더 전체 추가 (messages, scenarios 폴더 포함)
        # 'resources' 폴더 안의 모든 내용을 실행 파일 내부의 'resources' 폴더에 복사합니다.
        ('resources', 'resources'),
        
        # 4. [보완] 루트 경로의 JSON 설정 파일들 추가
        # 로그 변환기(log_converter)가 사용하는 규칙 및 프로파일입니다.
        ('message_key_rules.json', '.'),
        ('profile.json', '.')
    ],
    hiddenimports=[
        'qasync',  # PyInstaller가 qasync를 놓칠 수 있으므로 명시적으로 추가
        'pandas'   # requirements.txt에 pandas가 있으므로 포함시킵니다.
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
    [], # a.binaries, a.zipfiles, a.datas는 아래에서 한 번에 처리
    exclude_binaries=True,
    name='SECS_Simulator',    # 실행 파일 이름
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # GUI 애플리케이션이므로 False 유지
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='path/to/your/icon.ico' # 아이콘 파일이 있다면 주석을 풀고 경로를 지정하세요.
)

# COLLECT는 최종적으로 dist 폴더에 어떤 파일들을 모을지 결정합니다.
# EXE 객체와 Analysis 객체의 결과물을 모두 합쳐줍니다.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SECS_Simulator',
)