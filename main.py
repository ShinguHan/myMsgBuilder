# main.py
import sys
import asyncio
import qasync

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.main_window import MainWindow

# ✅ [버그 수정] 불필요한 색상 결정 로직을 제거하고, 전달받은 color를 그대로 사용합니다.
async def status_update_callback(window: MainWindow, device_id: str, status: str, color: str):
    """Orchestrator가 UI 업데이트를 위해 호출할 콜백. UI의 Signal을 emit합니다."""
    window.agent_status_updated.emit(device_id, status, color)

async def main():
    """애플리케이션의 메인 비동기 로직."""
    
    window = None 
    
    # ✅ [버그 수정] callback_wrapper가 3개의 인자(dev_id, msg, color)를 받도록 수정합니다.
    async def callback_wrapper(dev_id, msg, color):
        if window:
            # ✅ [버그 수정] status_update_callback에 color 인자를 전달합니다.
            asyncio.create_task(status_update_callback(window, dev_id, msg, color))

    # 1. Orchestrator 인스턴스 생성
    orchestrator = Orchestrator(status_callback=callback_wrapper)

    # 2. 장비 설정 파일 로드
    device_configs = orchestrator.load_device_configs('./secs_simulator/engine/devices.json')

    # 3. 메인 윈도우 생성 및 Orchestrator와 연결
    window = MainWindow(orchestrator)
    window.show()

    # qasync 이벤트 루프가 계속 실행되도록 Future를 반환
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    app = QApplication(sys.argv)

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