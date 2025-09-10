# main.py
import sys
import asyncio
import qasync

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.main_window import MainWindow

async def status_update_callback(window: MainWindow, device_id: str, status: str):
    """Orchestrator가 UI 업데이트를 위해 호출할 콜백. UI의 Signal을 emit합니다."""
    # 상태 메시지에 따라 색상을 결정하는 간단한 로직
    color = "gray"
    if "Listening" in status: color = "orange"
    elif "Connected" in status or "Sent" in status: color = "green"
    elif "Error" in status: color = "red"
    
    window.agent_status_updated.emit(device_id, status, color)

async def main():
    """애플리케이션의 메인 비동기 로직."""
    
    # MainWindow 인스턴스를 먼저 생성해야 콜백에서 참조 가능
    window = None 
    
    async def callback_wrapper(dev_id, msg):
        # window 객체가 생성된 후에만 콜백이 동작하도록 보장
        if window:
            # 비동기 콜백을 asyncio 루프에서 안전하게 실행
            asyncio.create_task(status_update_callback(window, dev_id, msg))

    # 1. Orchestrator 인스턴스 생성
    orchestrator = Orchestrator(status_callback=callback_wrapper)

    # 2. 장비 설정 파일 로드
    device_configs = orchestrator.load_device_configs('./secs_simulator/engine/devices.json')

    # ✅ 3. 메인 윈도우 생성 및 Orchestrator와 연결 (이 부분을 수정합니다)
    window = MainWindow(orchestrator)
    window.show()

    # qasync 이벤트 루프가 계속 실행되도록 Future를 반환
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ✅ 스타일시트 파일을 읽어 앱 전체에 적용합니다.
    try:
        qss_file = QFile("./secs_simulator/ui/styles/apple_style.qss")
        if qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(qss_file)
            app.setStyleSheet(stream.readAll())
    except Exception as e:
        print(f"Could not load stylesheet: {e}")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.close()