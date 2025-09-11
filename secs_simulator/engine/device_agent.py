import asyncio
from typing import Callable, Awaitable, Dict, Any, Optional

from secs_simulator.core.hsms import HsmsConnection

class DeviceAgent:
    """
    하나의 가상 설비를 나타내는 독립적인 에이전트 클래스.
    자체 HSMS 서버를 구동하며 외부 명령에 따라 동작합니다.
    """

    # ✅ [버그 수정] status_callback의 타입 힌트를 3개의 인자를 받도록 수정합니다.
    def __init__(self, device_id: str, host: str, port: int, status_callback: Callable[[str, str, str], Awaitable]):
        """
        Args:
            device_id (str): 이 장비의 고유 ID (e.g., "CV_01")
            host (str): 서버를 실행할 호스트 주소
            port (int): 서버가 리슨할 포트 번호
            status_callback (Callable): 상태 변경 시 상위 컨트롤러(UI)에 알릴 비동기 콜백
        """
        self.device_id = device_id
        self.host = host
        self.port = port
        self.status_callback = status_callback

        self._server: Optional[asyncio.AbstractServer] = None
        self._connection: Optional[HsmsConnection] = None
        self._command_queue = asyncio.Queue()
        self._main_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """에이전트의 HSMS 서버를 시작하고 명령 처리 루프를 가동합니다."""
        if self._server:
            print(f"Agent '{self.device_id}' is already running.")
            return

        try:
            self._server = await asyncio.start_server(
                self._on_client_connected, self.host, self.port
            )
            self._main_task = asyncio.create_task(self._command_processor())
            await self._update_status(f"Listening on {self.host}:{self.port}")
        except OSError as e:
            await self._update_status(f"Error: Port {self.port} already in use.")
            print(f"Failed to start agent '{self.device_id}': {e}")
        except Exception as e:
            await self._update_status(f"Error: {e}")
            print(f"An unexpected error occurred while starting agent '{self.device_id}': {e}")


    async def stop(self) -> None:
        """에이전트의 서버와 모든 태스크를 안전하게 중지합니다."""
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        if self._connection and not self._connection.writer.is_closing():
            self._connection.writer.close()
            await self._connection.writer.wait_closed()

        self._server = None
        self._connection = None
        await self._update_status("Stopped")

    async def send_message(self, s: int, f: int, body: Optional[list] = None) -> None:
        """
        외부(Orchestrator)에서 호출하는 비동기 API.
        명령 큐에 메시지 전송 요청을 넣습니다.
        """
        command = {"action": "send", "s": s, "f": f, "body": body or []}
        await self._command_queue.put(command)

    async def _update_status(self, status: str) -> None:
        """상태 변경을 상위 관리자에게 비동기적으로 보고하고, 상태에 따라 색상을 결정합니다."""
        # ✅ [버그 수정] 상태 메시지에 따라 색상을 결정하는 로직을 추가합니다.
        color = "gray"
        if "Listening" in status:
            color = "orange"
        elif "Connected" in status or "Sent" in status:
            color = "green"
        elif "Error" in status:
            color = "red"
        
        # ✅ [버그 수정] 콜백에 device_id, status, color 3개의 인자를 모두 전달합니다.
        await self.status_callback(self.device_id, status, color)

    async def _on_client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Host가 접속했을 때 호출되는 콜백 함수."""
        await self._update_status("Host Connected")
        self._connection = HsmsConnection(reader, writer)
        try:
            await self._connection.handle_connection()
        finally:
            self._connection = None
            await self._update_status(f"Listening on {self.host}:{self.port}")

    async def _command_processor(self) -> None:
        """
        명령 큐를 감시하고 명령을 처리하는 메인 루프.
        """
        while True:
            command = None
            try:
                command = await self._command_queue.get()
                
                if command['action'] == 'send':
                    if self._connection and self._connection.is_selected:
                        temp_system_bytes = self._connection.get_next_system_bytes()
                        await self._connection.send_secs_message(
                            s=command['s'],
                            f=command['f'],
                            system_bytes=temp_system_bytes,
                            body_obj=command['body']
                        )
                        await self._update_status(f"Sent S{command['s']}F{command['f']}")
                    else:
                        await self._update_status("Cannot send: Not connected or not selected.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._update_status(f"Error in command processor: {e}")
            finally:
                if command:
                    self._command_queue.task_done()