import asyncio
from typing import Callable, Awaitable, Optional

from secs_simulator.core.hsms import HsmsConnection

class DeviceAgent:
    """
    하나의 가상 설비를 나타내는 독립적인 에이전트 클래스.
    자체 HSMS 서버를 구동하며 외부 명령에 따라 동작합니다.
    """

    def __init__(self, device_id: str, host: str, port: int, status_callback: Callable[[str, str, str], Awaitable]):
        self.device_id = device_id
        self.host = host
        self.port = port
        self.status_callback = status_callback

        self._server: Optional[asyncio.AbstractServer] = None
        self._connection: Optional[HsmsConnection] = None
        self._command_queue = asyncio.Queue()
        self._main_task: Optional[asyncio.Task] = None
        self._incoming_message_queue = asyncio.Queue()
        
        # ✅ [핵심 수정] System Bytes 카운터를 Connection이 아닌 Agent가 직접 관리합니다.
        self._system_bytes_counter = 0

    def _get_next_system_bytes(self) -> int:
        """다음에 사용할 System Bytes 값을 반환하고 1 증가시킵니다."""
        self._system_bytes_counter = (self._system_bytes_counter + 1) & 0xFFFFFFFF
        return self._system_bytes_counter

    async def start(self) -> None:
        # ... (기존 코드와 동일) ...
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
        # ... (기존 코드와 동일) ...
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

    async def send_message(self, s: int, f: int, w_bit: bool, body: Optional[list] = None) -> int:
        """
        ✅ [핵심 수정] 메시지 전송 명령을 큐에 넣고, 사용될 System Bytes를 반환합니다.
        """
        system_bytes = self._get_next_system_bytes()
        command = {"action": "send", "s": s, "f": f, "w_bit": w_bit, "body": body or [], "system_bytes": system_bytes}
        await self._command_queue.put(command)
        return system_bytes

    async def _update_status(self, status: str, color: str = "default") -> None:
        # ... (기존 코드와 동일) ...
        final_color = color
        if color == "default":
            final_color = "gray"
            if "Listening" in status:
                final_color = "orange"
            elif "Connected" in status or "Sent" in status or "Received" in status:
                final_color = "green"
            elif "Waiting" in status:
                final_color = "yellow"
            elif "Error" in status or "Timeout" in status:
                final_color = "red"
        
        await self.status_callback(self.device_id, status, final_color)
        
    async def _on_message_received(self, message: dict) -> None:
        # ... (기존 코드와 동일) ...
        await self._incoming_message_queue.put(message)
        s = message.get('s', '?')
        f = message.get('f', '?')
        await self._update_status(f"Received S{s}F{f}")


    async def _on_client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        # ... (기존 코드와 동일) ...
        await self._update_status("Host Connected")
        self._connection = HsmsConnection(reader, writer, message_callback=self._on_message_received)
        try:
            await self._connection.handle_connection()
        finally:
            self._connection = None
            await self._update_status(f"Listening on {self.host}:{self.port}")

    async def wait_for_message(self, s: int, f: int, timeout: float, system_bytes: int) -> Optional[dict]:
        """
        ✅ [핵심 수정] S/F뿐만 아니라 System Bytes까지 일치하는 메시지를 기다립니다.
        """
        await self._update_status(f"Waiting for S{s}F{f} (Reply to SB={system_bytes})", "yellow")
        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await self._incoming_message_queue.get()
                    if msg.get('s') == s and msg.get('f') == f and msg.get('system_bytes') == system_bytes:
                        return msg
                    else:
                        # 관련 없는 메시지는 무시하고 계속 다음 메시지를 확인합니다.
                        unmatched_s = msg.get('s', '?')
                        unmatched_f = msg.get('f', '?')
                        unmatched_sb = msg.get('system_bytes', '?')
                        print(f"  - Ignored unmatched message S{unmatched_s}F{unmatched_f} SB={unmatched_sb} while waiting.")
        except TimeoutError:
            await self._update_status(f"Timeout waiting for S{s}F{f} (Reply to SB={system_bytes})", "red")
            return None

    async def _command_processor(self) -> None:
        """
        ✅ [핵심 수정] 큐에 들어온 명령의 system_bytes를 사용하여 메시지를 전송합니다.
        """
        while True:
            command = None
            try:
                command = await self._command_queue.get()
                
                if command['action'] == 'send':
                    if self._connection and self._connection.is_selected:
                        await self._connection.send_secs_message(
                            s=command['s'],
                            f=command['f'],
                            w_bit=command['w_bit'],
                            system_bytes=command['system_bytes'],
                            body_obj=command['body']
                        )
                        await self._update_status(f"Sent S{command['s']}F{command['f']} (SB={command['system_bytes']})")
                    else:
                        await self._update_status("Cannot send: Not connected or not selected.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._update_status(f"Error in command processor: {e}")
            finally:
                if command:
                    self._command_queue.task_done()
