import asyncio
import logging
from typing import Callable, Awaitable, Optional
from enum import Enum
import time

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
                 connection_mode: str = "Passive",
                 t3: int = 10, t5: int = 10, t6: int = 5, t7: int = 10): # 타임아웃 파라미터 추가
        self.device_id = device_id
        self.host = host
        self.port = port
        self.status_callback = status_callback
        self.connection_mode = connection_mode

        # HSMS 타임아웃 설정
        self.t3_timeout = t3
        self.t5_timeout = t5
        self.t6_timeout = t6
        self.t7_timeout = t7
        
        # 연결 관리
        self._server: Optional[asyncio.AbstractServer] = None
        self._connection: Optional[HsmsConnection] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_lock = asyncio.Lock()
        
        # 태스크 관리
        self._main_task: Optional[asyncio.Task] = None
        self._command_processor_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._t5_timer_task: Optional[asyncio.Task] = None # T5 타이머 태스크 추가
        
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
                await self._update_status(f"Connecting to {self.host}:{self.port}...", "yellow")
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.t7_timeout # connection_timeout을 t7_timeout으로 변경
                )
                
                async with self._connection_lock:
                    await self._establish_connection(reader, writer)
                    if self._connection:
                        await self._initiate_hsms_handshake()
                
                if self._connection:
                    await self._connection.wait_for_disconnect()
                    
            except asyncio.TimeoutError:
                await self._update_status(f"Connection Timeout (T7)", "red") # 타임아웃 메시지 명확화
            except ConnectionRefusedError:
                await self._update_status("Connection refused", "red")
            except Exception as e:
                await self._update_status(f"Connection error: {e}", "red")
            
            if not self._shutdown_event.is_set():
                await self._update_status(f"Reconnecting in {self.reconnect_delay}s...", "orange")
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.reconnect_delay)
                except asyncio.TimeoutError:
                    pass

    async def _establish_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """연결 설정"""
        try:
            peername = writer.get_extra_info('peername')
            await self._update_status(f"Connected to {peername[0]}:{peername[1]}. Waiting for Select...", "orange")

            self._connection_state = ConnectionState.CONNECTED
            self._connection_ready.clear()
            
            self._connection = HsmsConnection(
                reader, writer,
                message_callback=self._on_message_received,
                state_change_callback=self._on_connection_state_change
            )
            
            # 하트비트 및 T5 타이머 시작
            if self._heartbeat_task: self._heartbeat_task.cancel()
            if self._t5_timer_task: self._t5_timer_task.cancel() # 기존 T5 타이머 정리
            
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._t5_timer_task = asyncio.create_task(self._t5_timer_loop()) # T5 타이머 시작
            
            asyncio.create_task(self._connection.handle_connection())
            
        except Exception as e:
            self.logger.error(f"Connection establishment failed: {e}")
            await self._cleanup_connection()

    async def _t5_timer_loop(self):
        """T5 유휴 연결 타이머 루프"""
        try:
            while not self._shutdown_event.is_set() and self._connection:
                await asyncio.sleep(1) # 1초마다 확인
                if self._connection:
                    idle_time = time.monotonic() - self._connection.last_message_time
                    if idle_time > self.t5_timeout:
                        self.logger.warning(f"T5 timeout ({self.t5_timeout}s) exceeded. Disconnecting.")
                        await self._update_status(f"Idle Timeout (T5)", "red")
                        await self._cleanup_connection()
                        break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in T5 timer loop: {e}")

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
        """주기적 연결 상태 확인 (T6 기반)"""
        try:
            # T6 타임아웃의 절반 주기로 Linktest 전송
            linktest_interval = self.t6_timeout / 2
            while not self._shutdown_event.is_set() and self._connection:
                await asyncio.sleep(linktest_interval)
                
                if self._connection and self._connection.is_selected:
                    try:
                        system_bytes = self._get_next_system_bytes()
                        # Linktest 응답을 T6 시간 내에 기다림
                        future = self._connection.send_hsms_message(
                            msg_type=HsmsMessageType.LINKTEST_REQ,
                            system_bytes=system_bytes
                        )
                        await asyncio.wait_for(future, timeout=self.t6_timeout)
                        self.logger.debug("Heartbeat sent and reply received")
                    except asyncio.TimeoutError:
                        self.logger.error("Linktest (T6) timeout. Disconnecting.")
                        await self._update_status("Linktest Timeout (T6)", "red")
                        await self._cleanup_connection()
                        break
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
                          body: Optional[list] = None) -> int:
        """
        [수정됨] 메시지를 즉시 전송하고, 응답을 기다리지 않고 system_bytes를 반환합니다.
        """
        if not await self._wait_for_ready(timeout=5.0):
            # 연결이 준비되지 않으면 -1과 같은 실패 값을 반환할 수 있습니다.
            return -1
            
        system_bytes = self._get_next_system_bytes()
        
        # w_bit가 True일 때만 응답을 기다리기 위한 Future를 생성합니다.
        if w_bit:
            self._pending_replies[system_bytes] = asyncio.Future()
        
        # 메시지 전송 명령을 큐에 넣습니다.
        command = {
            "action": "send",
            "s": s, "f": f, "w_bit": w_bit,
            "body": body or [],
            "system_bytes": system_bytes
        }
        await self._command_queue.put(command)
        
        # 응답을 기다리지 않고, 요청에 사용된 system_bytes를 즉시 반환합니다.
        return system_bytes

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

    async def wait_for_message(self, s: int, f: int, timeout: float = 10.0, 
                               reply_to_system_bytes: Optional[int] = None) -> Optional[dict]:
        """
        [수정됨] 특정 메시지 또는 특정 요청에 대한 응답을 기다립니다.
        """
        # --- 특정 요청(system_bytes)에 대한 응답을 기다리는 경우 ---
        if reply_to_system_bytes is not None:
            await self._update_status(f"Waiting for reply to SB={reply_to_system_bytes}", "yellow")
            future = self._pending_replies.get(reply_to_system_bytes)
            if not future:
                await self._update_status(f"Error: No pending reply found for SB={reply_to_system_bytes}", "red")
                return None
            
            try:
                # 해당 future가 완료될 때까지 기다립니다.
                response = await asyncio.wait_for(future, timeout=timeout)
                # 완료 후에는 딕셔너리에서 제거합니다.
                self._pending_replies.pop(reply_to_system_bytes, None)
                return response
            except asyncio.TimeoutError:
                self._pending_replies.pop(reply_to_system_bytes, None)
                await self._update_status(f"Timeout waiting for reply to SB={reply_to_system_bytes}", "red")
                return None

        # --- 일반 메시지(S/F)를 기다리는 경우 (기존 로직) ---
        await self._update_status(f"Waiting for S{s}F{f}", "yellow")
        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await self._incoming_message_queue.get()
                    if msg.get('s') == s and msg.get('f') == f:
                        return msg
                    else:
                        await self._incoming_message_queue.put(msg)
                        await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            await self._update_status(f"Timeout waiting for S{s}F{f}", "red")
            return None

    async def _update_status(self, status: str, color: str = "default"):
        """상태 업데이트"""
        # 1. 색상에 기반하여 로그 레벨을 결정합니다.
        log_level = logging.INFO
        if color == "red":
            log_level = logging.ERROR
        elif color in ["yellow", "orange"]:
            log_level = logging.WARNING
        
        # 2. 결정된 레벨로 로그를 기록합니다.
        self.logger.log(log_level, status)
        
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