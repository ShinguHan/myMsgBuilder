import asyncio
from typing import Callable, Awaitable, Optional

from secs_simulator.core.hsms import HsmsConnection

class DeviceAgent:
    """
    하나의 가상 설비를 나타내는 독립적인 에이전트 클래스.
    Passive(서버) 또는 Active(클라이언트) 모드로 동작합니다.
    """

    def __init__(self, device_id: str, host: str, port: int, status_callback: Callable[[str, str, str], Awaitable], connection_mode: str = "Passive"):
        self.device_id = device_id
        self.host = host
        self.port = port
        self.status_callback = status_callback
        self.connection_mode = connection_mode

        self._server: Optional[asyncio.AbstractServer] = None
        self._connection: Optional[HsmsConnection] = None
        self._command_queue = asyncio.Queue()
        self._main_task: Optional[asyncio.Task] = None
        self._incoming_message_queue = asyncio.Queue()
        self._system_bytes_counter = 0

    def _get_next_system_bytes(self) -> int:
        self._system_bytes_counter = (self._system_bytes_counter + 1) & 0xFFFFFFFF
        return self._system_bytes_counter

    async def start(self) -> None:
        if self._main_task and not self._main_task.done():
            print(f"Agent '{self.device_id}' is already running or starting.")
            return

        # Passive와 Active 모드 분기 처리
        if self.connection_mode == "Passive":
            self._main_task = asyncio.create_task(self._run_server())
        elif self.connection_mode == "Active":
            self._main_task = asyncio.create_task(self._run_client())
        else:
            await self._update_status(f"Error: Unknown mode '{self.connection_mode}'", "red")

    async def _run_server(self):
        """Passive 모드: HSMS 서버를 시작하고 클라이언트 연결을 기다립니다."""
        try:
            self._server = await asyncio.start_server(
                self._on_client_connected, self.host, self.port
            )
            addr = self._server.sockets[0].getsockname()
            await self._update_status(f"Listening on {addr[0]}:{addr[1]}", "orange")
            
            # command_processor를 여기서 함께 실행
            await self._command_processor()

        except OSError as e:
            await self._update_status(f"Error: Port {self.port} in use.", "red")
        except asyncio.CancelledError:
            await self._update_status("Server task cancelled.")
        finally:
            if self._server:
                self._server.close()
                await self._server.wait_closed()

    async def _run_client(self):
        """Active 모드: 지정된 서버에 주기적으로 연결을 시도합니다."""
        retry_delay = 5  # 재시도 간격 (초)
        try:
            command_processor_task = asyncio.create_task(self._command_processor())
            while True:
                try:
                    await self._update_status(f"Connecting to {self.host}:{self.port}...", "yellow")
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                    await self._on_client_connected(reader, writer)
                    # 연결이 정상적으로 종료되면, 다시 연결을 시도합니다.
                    await self._update_status(f"Disconnected. Retrying in {retry_delay}s...", "orange")

                except ConnectionRefusedError:
                    await self._update_status(f"Connection refused. Retrying...", "red")
                except asyncio.TimeoutError:
                     await self._update_status(f"Connection timeout. Retrying...", "red")
                except asyncio.CancelledError:
                    # start()나 stop()에 의해 태스크가 취소되면 루프를 종료합니다.
                    break
                except Exception as e:
                    await self._update_status(f"Client Error: {e}", "red")

                await asyncio.sleep(retry_delay)

        except asyncio.CancelledError:
            await self._update_status("Client task cancelled.")
        finally:
             if 'command_processor_task' in locals() and not command_processor_task.done():
                command_processor_task.cancel()


    async def stop(self) -> None:
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
        
        if self._connection and not self._connection.writer.is_closing():
            # 연결을 명시적으로 닫아 handle_connection 루프를 종료시킵니다.
            self._connection.writer.close()
            await self._connection.writer.wait_closed()

        self._server = None
        self._connection = None
        await self._update_status("Stopped", "gray")

    async def send_message(self, s: int, f: int, w_bit: bool = False, body: Optional[list] = None) -> int:
        system_bytes = self._get_next_system_bytes()
        command = {"action": "send", "s": s, "f": f, "w_bit": w_bit, "body": body or [], "system_bytes": system_bytes}
        await self._command_queue.put(command)
        return system_bytes

    async def _update_status(self, status: str, color: str = "default") -> None:
        final_color = color
        if color == "default":
            final_color = "gray"
            if "Listening" in status or "Connecting" in status: final_color = "orange"
            elif "Connected" in status or "Sent" in status or "Received" in status: final_color = "green"
            elif "Waiting" in status: final_color = "yellow"
            elif "Error" in status or "Timeout" in status or "refused" in status: final_color = "red"
        
        await self.status_callback(self.device_id, status, final_color)
        
    async def _on_message_received(self, message: dict) -> None:
        await self._incoming_message_queue.put(message)
        s, f = message.get('s', '?'), message.get('f', '?')
        await self._update_status(f"Received S{s}F{f}", "green")

    async def _on_client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peername = writer.get_extra_info('peername')
        await self._update_status(f"Connected to {peername[0]}:{peername[1]}", "green")
        self._connection = HsmsConnection(reader, writer, message_callback=self._on_message_received)
        try:
            await self._connection.handle_connection()
        finally:
            self._connection = None
            if self.connection_mode == "Passive":
                 await self._update_status(f"Listening on {self.host}:{self.port}", "orange")

    async def wait_for_message(self, s: int, f: int, timeout: float, system_bytes: int) -> Optional[dict]:
        await self._update_status(f"Waiting for S{s}F{f} (Reply to SB={system_bytes})", "yellow")
        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await self._incoming_message_queue.get()
                    if msg.get('s') == s and msg.get('f') == f and msg.get('system_bytes') == system_bytes:
                        return msg
                    else:
                        unmatched_s, unmatched_f, unmatched_sb = msg.get('s', '?'), msg.get('f', '?'), msg.get('system_bytes', '?')
                        print(f"  - Ignored unmatched message S{unmatched_s}F{unmatched_f} SB={unmatched_sb} while waiting.")
        except TimeoutError:
            await self._update_status(f"Timeout waiting for S{s}F{f} (Reply to SB={system_bytes})", "red")
            return None

    async def _command_processor(self) -> None:
        try:
            while True:
                command = await self._command_queue.get()
                
                if command['action'] == 'send':
                    if self._connection and self._connection.is_selected:
                        await self._connection.send_secs_message(
                            s=command['s'],
                            f=command['f'],
                            w_bit=command.get('w_bit', False),
                            system_bytes=command['system_bytes'],
                            body_obj=command['body']
                        )
                        await self._update_status(f"Sent S{command['s']}F{command['f']} (SB={command['system_bytes']})", "green")
                    else:
                        await self._update_status("Cannot send: Not connected.", "red")
                
                self._command_queue.task_done()
        except asyncio.CancelledError:
            print(f"Command processor for {self.device_id} cancelled.")

