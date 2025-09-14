# main.py
import sys
import asyncio
import qasync

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.main_window import MainWindow
import logging # logging 모듈 추가
from secs_simulator.ui.log_viewer import QtLogHandler # 새로 만든 핸들러 임포트

async def status_update_callback(window: MainWindow, device_id: str, status: str, color: str):
    """Orchestrator가 UI 업데이트를 위해 호출할 콜백. UI의 Signal을 emit합니다."""
    # window가 종료 과정에서 None이 될 수 있으므로 확인합니다.
    if window:
        window.agent_status_updated.emit(device_id, status, color)

async def main_async(app: QApplication):
    """애플리케이션의 메인 비동기 로직."""
    
    shutdown_future = asyncio.Future()
    window = None 

    async def callback_wrapper(dev_id, msg, color):
        if window:
            asyncio.create_task(status_update_callback(window, dev_id, msg, color))

    # 1. Orchestrator 인스턴스 생성
    orchestrator = Orchestrator(status_callback=callback_wrapper)

    # 2. 장비 설정 파일 로드
    orchestrator.load_device_configs('./secs_simulator/engine/devices.json')

    # 3. 메인 윈도우 생성 및 Orchestrator와 종료 Future 연결
    window = MainWindow(orchestrator, shutdown_future)
     # --- 로깅 설정 ---
    # 1. Qt 핸들러를 생성합니다.
    log_handler = QtLogHandler(window)
    # 2. 핸들러의 log_received 시그널을 MainWindow에 있는 로그 뷰어의 add_log_record 슬롯에 연결합니다.
    log_handler.log_received.connect(window.log_viewer.add_log_record)
    # 3. 모든 로그가 이 핸들러를 사용하도록 기본 로거를 설정합니다.
    logging.basicConfig(level=logging.DEBUG, handlers=[log_handler])

    # --- 로깅 설정 끝 ---
    window.show()

    # 4. 종료 신호를 받을 때까지 대기
    await shutdown_future
    
    # 5. 종료 신호를 받으면, 모든 에이전트를 정지시키는 정리 작업 수행
    print("Shutdown signaled. Stopping all agents...")
    await orchestrator.stop_all_agents()
    print("All agents stopped. Exiting.")
    
    # 6. 모든 비동기 정리가 끝난 후, Qt 애플리케이션을 종료하여 이벤트 루프를 중지시킵니다.
    app.quit()

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
        # main_async를 비동기 태스크로 생성합니다.
        loop.create_task(main_async(app))
        # 이벤트 루프를 계속 실행합니다. app.quit()이 호출되면 중지됩니다.
        loop.run_forever()
    except KeyboardInterrupt:
        print("Keyboard interrupt received, closing loop.")
    finally:
        # 루프가 중지된 후 모든 태스크를 취소하고 정리합니다.
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        
        # 취소된 태스크들이 완료될 때까지 기다립니다.
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        
        loop.close()

