import asyncio
import logging
from typing import Callable, Awaitable, Optional
from enum import Enum

from secs_simulator.core.hsms import HsmsConnection, HsmsMessageType

class ConnectionState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING" 
    CONNECTED = "CONNECTED"
    SELECTED = "SELECTED"
    ERROR = "ERROR"

class DeviceAgent:
    """
    개선된 가상 설비 에이전트 클래스.
    Passive(서버) 또는 Active(클라이언트) 모드로 동작합니다.
    """

    def __init__(self, device_id: str, host: str, port: int, 
                 status_callback: Callable[[str, str, str], Awaitable], 
                 connection_mode: str = "Passive"):
        self.device_id = device_id
        self.host = host
        self.port = port
        self.status_callback = status_callback
        self.connection_mode = connection_mode

        # 연결 관리
        self._server: Optional[asyncio.AbstractServer] = None
        self._connection: Optional[HsmsConnection] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_lock = asyncio.Lock()
        
        # 태스크 관리
        self._main_task: Optional[asyncio.Task] = None
        self._command_processor_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # 메시지 관리
        self._command_queue = asyncio.Queue()
        self._incoming_message_queue = asyncio.Queue()
        self._pending_replies = {}  # system_bytes -> Future
        self._system_bytes_counter = 0
        
        # 동기화
        self._connection_ready = asyncio.Event()
        self._shutdown_event = asyncio.Event()
        
        # 설정
        self.reconnect_delay = 5
        self.connection_timeout = 10
        self.heartbeat_interval = 30
        
        self.logger = logging.getLogger(f"DeviceAgent-{device_id}")

    def _get_next_system_bytes(self) -> int:
        self._system_bytes_counter = (self._system_bytes_counter + 1) & 0xFFFFFFFF
        return self._system_bytes_counter

    async def start(self) -> None:
        """에이전트 시작"""
        if self._main_task and not self._main_task.done():
            await self._update_status("Already running", "yellow")
            return

        self._shutdown_event.clear()
        
        # 명령 프로세서 시작
        self._command_processor_task = asyncio.create_task(self._command_processor())
        
        # 연결 모드에 따라 시작
        if self.connection_mode == "Passive":
            self._main_task = asyncio.create_task(self._run_server())
        elif self.connection_mode == "Active":
            self._main_task = asyncio.create_task(self._run_client())
        else:
            await self._update_status(f"Invalid mode: {self.connection_mode}", "red")

    async def _run_server(self):
        """서버(Passive) 모드 실행"""
        try:
            # 올바른 서버 시작 방식
            self._server = await asyncio.start_server(
                self._handle_client_connection, 
                self.host, 
                self.port
            )
            
            addr = self._server.sockets[0].getsockname()
            # ✅ [수정] 'Listening' 상태도 주황색으로 명확히 표시
            await self._update_status(f"Listening on {addr[0]}:{addr[1]}", "orange")

            # 서버 종료 대기
            await self._server.serve_forever()
            
        except OSError as e:
            if e.errno == 98:  # Address already in use
                await self._update_status(f"Port {self.port} already in use", "red")
            else:
                await self._update_status(f"Server error: {e}", "red")
        except asyncio.CancelledError:
            self.logger.info("Server task cancelled")
        finally:
            await self._cleanup_server()

    async def _handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """클라이언트 연결 처리 (서버 모드)"""
        peername = writer.get_extra_info('peername')
        
        async with self._connection_lock:
            # 이미 연결이 있으면 새 연결 거부
            if self._connection is not None:
                self.logger.warning(f"Rejecting connection from {peername}, already connected")
                writer.close()
                await writer.wait_closed()
                return
            
            await self._establish_connection(reader, writer)

    async def _run_client(self):
        """클라이언트(Active) 모드 실행"""
        while not self._shutdown_event.is_set():
            try:
                # ✅ [수정] 'Connecting' 상태도 노란색으로 명확히 표시
                await self._update_status(f"Connecting to {self.host}:{self.port}...", "yellow")

                # 연결 시도 (타임아웃 적용)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.connection_timeout
                )
                
                async with self._connection_lock:
                    await self._establish_connection(reader, writer)
                    
                    # Active 모드에서는 Select.req 전송
                    if self._connection:
                        await self._initiate_hsms_handshake()
                
                # 연결 유지 대기
                if self._connection:
                    await self._connection.wait_for_disconnect()
                
            except asyncio.TimeoutError:
                await self._update_status("Connection timeout", "red")
            except ConnectionRefusedError:
                await self._update_status("Connection refused", "red")
            except Exception as e:
                await self._update_status(f"Connection error: {e}", "red")
            
            # 재연결 대기
            if not self._shutdown_event.is_set():
                await self._update_status(f"Reconnecting in {self.reconnect_delay}s...", "orange")
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=self.reconnect_delay
                    )
                except asyncio.TimeoutError:
                    pass  # 재연결 시도

    async def _establish_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """연결 설정"""
        try:
            peername = writer.get_extra_info('peername')
            # ✅ [수정] HSMS 규약상 연결 직후는 'SELECTED'가 아니므로, 더 명확한 상태 메시지를 표시합니다.
            await self._update_status(f"Connected to {peername[0]}:{peername[1]}. Waiting for Select...", "orange")

            self._connection_state = ConnectionState.CONNECTED
            self._connection_ready.clear()
            
            self._connection = HsmsConnection(
                reader, writer,
                message_callback=self._on_message_received,
                state_change_callback=self._on_connection_state_change
            )
            
            # 하트비트 시작
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # ✅ [핵심 수정] 메시지 수신 루프를 await로 기다리지 않고,
            # 백그라운드 태스크로 실행하여 프로그램 흐름이 계속 진행되도록 합니다.
            asyncio.create_task(self._connection.handle_connection())
            
        except Exception as e:
            self.logger.error(f"Connection establishment failed: {e}")
            await self._cleanup_connection()

    async def _initiate_hsms_handshake(self):
        """HSMS 핸드셰이크 시작 (Active 모드)"""
        await asyncio.sleep(0.1)  # 연결 안정화 대기
        
        if self._connection and not self._connection.writer.is_closing():
            try:
                await self._update_status("Sending Select.req...", "yellow")
                system_bytes = self._get_next_system_bytes()
                await self._connection.send_hsms_message(
                    msg_type=HsmsMessageType.SELECT_REQ,
                    system_bytes=system_bytes
                )
            except Exception as e:
                await self._update_status(f"Handshake failed: {e}", "red")
                await self._cleanup_connection()

    async def _heartbeat_loop(self):
        """주기적 연결 상태 확인"""
        try:
            while not self._shutdown_event.is_set() and self._connection:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self._connection and self._connection.is_selected:
                    try:
                        system_bytes = self._get_next_system_bytes()
                        await self._connection.send_hsms_message(
                            msg_type=HsmsMessageType.LINKTEST_REQ,
                            system_bytes=system_bytes
                        )
                        self.logger.debug("Heartbeat sent")
                    except Exception as e:
                        self.logger.error(f"Heartbeat failed: {e}")
                        await self._cleanup_connection()
                        break
        except asyncio.CancelledError:
            pass

    async def _on_connection_state_change(self, state: str):
        """연결 상태 변경 콜백"""
        if state == "SELECTED":
            self._connection_state = ConnectionState.SELECTED
            await self._update_status("HSMS Selected (Ready)", "green")
            self._connection_ready.set()
        elif state == "DISCONNECTED":
            self._connection_state = ConnectionState.DISCONNECTED
            self._connection_ready.clear()
            await self._cleanup_connection()

    async def _on_message_received(self, message: dict):
        """[수정됨] 메시지 수신 콜백 (로깅 및 처리 흐름 개선)"""
        system_bytes = message.get('system_bytes')
        s, f = message.get('s', '?'), message.get('f', '?')
        w_bit = message.get('w_bit', False)
        
        # ✅ 1. 모든 수신 메시지를 먼저 로그로 남깁니다.
        await self._update_status(f"Received S{s}F{f}", "green")

        # ✅ 2. 이 메시지가 내가 보낸 요청에 대한 '응답'인지 확인합니다.
        if system_bytes in self._pending_replies:
            future = self._pending_replies.pop(system_bytes)
            if not future.cancelled():
                future.set_result(message)
            # 응답 메시지는 여기서 처리가 완료되므로, 함수를 종료합니다.
            return
        
        # ✅ 3. 응답이 아니라면, 나에게 응답을 요구하는 새로운 '요청'인지 확인합니다.
        if w_bit:
            reply_s = s
            reply_f = f + 1
            reply_body = [{'type': 'B', 'value': 0}] # Acknowledge OK

            command = {
                "action": "send",
                "s": reply_s, "f": reply_f, "w_bit": False,
                "body": reply_body,
                "system_bytes": system_bytes
            }
            await self._command_queue.put(command)

        # ✅ 4. 시나리오의 'wait' 스텝 등에서 사용할 수 있도록, 수신된 요청을 큐에 넣습니다.
        # (w_bit=False인 단방향 메시지도 여기에 포함됩니다)
        await self._incoming_message_queue.put(message)

    async def stop(self) -> None:
        """에이전트 중지"""
        self._shutdown_event.set()
        
        # 모든 태스크 정리
        tasks_to_cancel = [
            self._main_task,
            self._command_processor_task,
            self._heartbeat_task
        ]
        
        for task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
        
        # 연결 정리
        await self._cleanup_connection()
        await self._cleanup_server()
        
        await self._update_status("Stopped", "gray")

    async def _cleanup_connection(self):
        """연결 정리"""
        if self._connection:
            try:
                if not self._connection.writer.is_closing():
                    self._connection.writer.close()
                    await self._connection.writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error cleaning up connection: {e}")
            finally:
                self._connection = None
                self._connection_ready.clear()
                
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _cleanup_server(self):
        """서버 정리"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def send_message(self, s: int, f: int, w_bit: bool = False, 
                          body: Optional[list] = None, timeout: float = 10.0) -> Optional[dict]:
        """메시지 전송 (응답 대기 포함)"""
        if not await self._wait_for_ready(timeout=5.0):
            return None
            
        system_bytes = self._get_next_system_bytes()
        
        # 응답 대기가 필요한 경우 Future 생성
        response_future = None
        if w_bit:
            response_future = asyncio.Future()
            self._pending_replies[system_bytes] = response_future
        
        # 메시지 전송
        command = {
            "action": "send",
            "s": s, "f": f, "w_bit": w_bit,
            "body": body or [],
            "system_bytes": system_bytes
        }
        await self._command_queue.put(command)
        
        # 응답 대기
        if response_future:
            try:
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                self._pending_replies.pop(system_bytes, None)
                await self._update_status(f"Timeout waiting for S{s}F{f+1} response", "red")
                return None
        
        return {"system_bytes": system_bytes}

    async def _wait_for_ready(self, timeout: float = 5.0) -> bool:
        """연결 준비 상태 대기"""
        try:
            await asyncio.wait_for(self._connection_ready.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            await self._update_status("Connection not ready", "red")
            return False

    async def _command_processor(self):
        """명령 처리 루프"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    command = await asyncio.wait_for(
                        self._command_queue.get(),
                        timeout=1.0
                    )
                    await self._process_command(command)
                    self._command_queue.task_done()
                except asyncio.TimeoutError:
                    continue  # 주기적으로 종료 신호 확인
        except asyncio.CancelledError:
            self.logger.info("Command processor cancelled")

    async def _process_command(self, command: dict):
        """개별 명령 처리"""
        if command['action'] != 'send':
            return
            
        if not self._connection or not self._connection.is_selected:
            await self._update_status("Cannot send: Not connected/selected", "red")
            return
            
        try:
            await self._connection.send_secs_message(
                s=command['s'],
                f=command['f'],
                w_bit=command['w_bit'],
                system_bytes=command['system_bytes'],
                body_obj=command['body']
            )
            await self._update_status(
                f"Sent S{command['s']}F{command['f']} (SB={command['system_bytes']})", 
                "green"
            )
        except Exception as e:
            await self._update_status(f"Send failed: {e}", "red")

    async def wait_for_message(self, s: int, f: int, timeout: float = 10.0) -> Optional[dict]:
        """특정 메시지 대기"""
        await self._update_status(f"Waiting for S{s}F{f}", "yellow")
        
        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await self._incoming_message_queue.get()
                    if msg.get('s') == s and msg.get('f') == f:
                        return msg
                    else:
                        # 다시 큐에 넣기 (다른 대기자를 위해)
                        await self._incoming_message_queue.put(msg)
                        await asyncio.sleep(0.01)  # CPU 사용량 방지
        except asyncio.TimeoutError:
            await self._update_status(f"Timeout waiting for S{s}F{f}", "red")
            return None

    async def _update_status(self, status: str, color: str = "default"):
        """상태 업데이트"""
        final_color = color
        if color == "default":
            final_color = "gray"
            if "Listening" in status or "Connecting" in status: 
                final_color = "orange"
            elif "Connected" in status or "Sent" in status or "Received" in status or "Selected" in status: 
                final_color = "green"
            elif "Waiting" in status: 
                final_color = "yellow"
            elif "Error" in status or "Timeout" in status or "refused" in status: 
                final_color = "red"
        
        try:
            await self.status_callback(self.device_id, status, final_color)
        except Exception as e:
            self.logger.error(f"Status callback failed: {e}")

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return (self._connection is not None and 
                not self._connection.writer.is_closing() and
                self._connection.is_selected)