import asyncio
import struct
import logging
from enum import IntEnum
from typing import Optional, Callable, Awaitable

from .secs_parser import parse_body
from .secs_builder import build_secs_body

class HsmsMessageType(IntEnum):
    """SEMI E37 HSMS Message Types."""
    DATA_MESSAGE = 0
    SELECT_REQ = 1
    SELECT_RSP = 2
    DESELECT_REQ = 3
    DESELECT_RSP = 4
    LINKTEST_REQ = 5
    LINKTEST_RSP = 6
    REJECT_REQ = 7
    SEPARATE_REQ = 9

class HsmsConnection:
    """개선된 HSMS 연결 관리 클래스"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 message_callback: Callable[[dict], Awaitable],
                 state_change_callback: Optional[Callable[[str], Awaitable]] = None):
        self.reader = reader
        self.writer = writer
        self.peername = writer.get_extra_info('peername')
        self.is_selected = False
        self._system_bytes_counter = 0
        self._message_callback = message_callback
        self._state_change_callback = state_change_callback
        self._disconnect_event = asyncio.Event()
        self._send_lock = asyncio.Lock()  # 동시 전송 방지
        
        self.logger = logging.getLogger(f"HSMS-{self.peername}")
        self.logger.info(f"New HSMS connection established")

    def get_next_system_bytes(self) -> int:
        """다음에 사용할 System Bytes 값을 반환하고 카운터를 1 증가시킵니다."""
        self._system_bytes_counter = (self._system_bytes_counter + 1) & 0xFFFFFFFF
        return self._system_bytes_counter

    async def handle_connection(self) -> None:
        """메시지 수신 및 처리 메인 루프"""
        try:
            while not self.writer.is_closing():
                try:
                    # 메시지 길이 읽기 (4바이트)
                    length_bytes = await self.reader.readexactly(4)
                    if not length_bytes:
                        break
                        
                    message_length = int.from_bytes(length_bytes, 'big')
                    
                    # 메시지 길이 검증
                    if message_length < 10 or message_length > 0xFFFFFF:
                        self.logger.error(f"Invalid message length: {message_length}")
                        break
                    
                    # 메시지 페이로드 읽기
                    message_payload = await self.reader.readexactly(message_length)
                    if len(message_payload) != message_length:
                        self.logger.error("Incomplete message received")
                        break
                    
                    await self._process_message(message_payload)
                    
                except asyncio.IncompleteReadError as e:
                    if e.partial:
                        self.logger.warning(f"Partial data received: {len(e.partial)} bytes")
                    else:
                        self.logger.info("Connection closed by peer (clean disconnect)")
                    break
                except ConnectionResetError:
                    self.logger.info("Connection reset by peer")
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error in message handling: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Critical error in connection handler: {e}")
        finally:
            await self._cleanup_connection()

    async def _cleanup_connection(self):
        """연결 정리"""
        self.logger.info("Cleaning up connection")
        self.is_selected = False
        self._disconnect_event.set()
        
        if self._state_change_callback:
            try:
                await self._state_change_callback("DISCONNECTED")
            except Exception as e:
                self.logger.error(f"State change callback error: {e}")
        
        if not self.writer.is_closing():
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error closing writer: {e}")

    async def wait_for_disconnect(self):
        """연결 종료 대기"""
        await self._disconnect_event.wait()
   

    async def _handle_select_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Select.req 처리 및 Select.rsp 응답"""
        self.logger.info("Received Select.req, sending Select.rsp")
        # ✅ [수정] Select.rsp 성공(0)을 나타내는 1바이트 Body를 추가합니다.
        response_body = struct.pack('B', 0)
        await self.send_hsms_message(
            HsmsMessageType.SELECT_RSP,
            system_bytes,
            body=response_body
        )
        self.is_selected = True
        if self._state_change_callback:
            await self._state_change_callback("SELECTED")

    async def _handle_select_rsp(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Select.rsp 처리 (Active 클라이언트용)"""
        # ✅ [수정] Select.rsp의 성공 여부는 Body의 첫 바이트로 판단합니다 (0=성공).
        status = body[0] if body else 2  # Body가 없으면 통신 오류(2)로 간주

        if status == 0:
            self.logger.info("Received successful Select.rsp, connection selected")
            self.is_selected = True
            if self._state_change_callback:
                await self._state_change_callback("SELECTED")
        else:
            self.logger.error(f"Select.rsp failed with status code {status}")
            if self._state_change_callback:
                await self._state_change_callback("DISCONNECTED")
            await self._cleanup_connection()

    async def _handle_deselect_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Deselect.req 처리"""
        self.logger.info("Received Deselect.req, sending Deselect.rsp")
        await self.send_hsms_message(HsmsMessageType.DESELECT_RSP, system_bytes)
        self.is_selected = False
        if self._state_change_callback:
            await self._state_change_callback("DESELECTED")

    async def _handle_linktest_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Linktest.req 처리 및 Linktest.rsp 응답"""
        self.logger.debug("Received Linktest.req, sending Linktest.rsp")
        await self.send_hsms_message(HsmsMessageType.LINKTEST_RSP, system_bytes)

    async def _handle_linktest_rsp(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Linktest.rsp 처리"""
        self.logger.debug("Received Linktest.rsp")

    async def _handle_separate_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Separate.req 처리 및 연결 종료"""
        self.logger.info("Received Separate.req, closing connection")
        await self._cleanup_connection()

    async def _handle_reject_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Reject.req 처리"""
        reason = body[0] if body else 0
        self.logger.warning(f"Received Reject.req with reason: {reason}")

    async def _handle_data_message(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """데이터 메시지 처리 및 콜백 호출"""
        if not self.is_selected:
            self.logger.warning(f"Received data message S{s}F{f} but not selected, sending reject")
            await self._send_reject(system_bytes, 4)  # Connection not ready
            return
            
        try:
            parsed_body = parse_body(body) if body else []
            
            message = {
                's': s, 'f': f, 'w_bit': w,
                'system_bytes': system_bytes,
                'body': parsed_body
            }
            
            self.logger.debug(f"Parsed data message S{s}F{f}, forwarding to agent")
            await self._message_callback(message)
            
        except Exception as e:
            self.logger.error(f"Error parsing message body: {e}")
            if w:  # W-bit이 설정된 경우 에러 응답 전송
                await self._send_abort(system_bytes)

    async def _send_reject(self, system_bytes: int, reason: int):
        """Reject 메시지 전송"""
        body = struct.pack('B', reason)
        await self.send_hsms_message(
            HsmsMessageType.REJECT_REQ, 
            system_bytes, 
            body=body
        )

    async def _send_abort(self, system_bytes: int):
        """Abort 메시지 전송 (S9F13)"""
        try:
            await self.send_secs_message(9, 13, False, system_bytes, [])
        except Exception as e:
            self.logger.error(f"Failed to send abort: {e}")

    async def send_secs_message(self, s: int, f: int, w_bit: bool, 
                               system_bytes: int, body_obj: Optional[list] = None) -> None:
        """SECS-II 데이터 메시지 구성 및 전송"""
        if not self.is_selected and not (s == 9 and f in [1, 5, 9, 11, 13]):  # 에러 메시지 예외
            raise RuntimeError("Connection not selected")
            
        try:
            body_bytes = build_secs_body(body_obj or [])
            await self.send_hsms_message(
                HsmsMessageType.DATA_MESSAGE, 
                system_bytes, 
                s, f, w_bit=w_bit, 
                body=body_bytes
            )
        except Exception as e:
            self.logger.error(f"Failed to send SECS message S{s}F{f}: {e}")
            raise

    def is_alive(self) -> bool:
        """연결 상태 확인"""
        return (not self.writer.is_closing() and 
                not self._disconnect_event.is_set())
    
    async def _process_message(self, payload: bytes) -> None:
        """[최종 수정] HSMS 메시지 파싱 및 라우팅"""
        if len(payload) < 10:
            self.logger.error("Message too short for HSMS header")
            return
            
        try:
            header = payload[:10]
            body = payload[10:]
            
            # 표준 10바이트 헤더: SessionID(H), s_byte(B), f_byte(B), ptype(B), stype(B), system(I)
            # unpack 포맷을 표준에 맞게 >HBBHHI 에서 >HBBBB I 로 변경해야 하나,
            # 현재 구조를 유지하며 ptype과 stype을 한 필드에서 분리합니다.
            session_id, s_with_w_bit, f, ptype_stype_field, system_bytes = struct.unpack('>HBBHI', header)
            
            w_bit = bool(s_with_w_bit & 0x80)
            s = s_with_w_bit & 0x7F 
            
            # SType 값을 명확히 추출 (상위 8비트는 PType, 하위 8비트는 SType)
            stype = ptype_stype_field & 0xFF

            try:
                msg_type = HsmsMessageType(stype) if stype != 0 else HsmsMessageType.DATA_MESSAGE
            except ValueError:
                self.logger.error(f"Unknown SType in header: {stype}")
                await self._send_reject(system_bytes, 3) # Type not supported
                return

            self.logger.debug(f"RECV: Type={msg_type.name} S{s}F{f} W={w_bit} SB={system_bytes}")

            handler_map = {
                HsmsMessageType.DATA_MESSAGE: self._handle_data_message,
                HsmsMessageType.SELECT_REQ: self._handle_select_req,
                HsmsMessageType.SELECT_RSP: self._handle_select_rsp,
                HsmsMessageType.LINKTEST_REQ: self._handle_linktest_req,
                HsmsMessageType.LINKTEST_RSP: self._handle_linktest_rsp,
                HsmsMessageType.SEPARATE_REQ: self._handle_separate_req,
                HsmsMessageType.REJECT_REQ: self._handle_reject_req,
                HsmsMessageType.DESELECT_REQ: self._handle_deselect_req,
            }

            handler = handler_map.get(msg_type)
            if handler:
                await handler(s, f, w_bit, system_bytes, body)
            else:
                self.logger.warning(f"No handler for message type {msg_type.name}")
                await self._send_reject(system_bytes, 3)
                
        except struct.error as e:
            self.logger.error(f"Invalid message format during unpack: {e}")
        except Exception as e:
            self.logger.error(f"Critical error in _process_message: {e}")


    async def send_hsms_message(
        self, msg_type: HsmsMessageType, system_bytes: int, 
        s: int = 0, f: int = 0, w_bit: bool = False, body: bytes = b''
    ) -> None:
        """[최종 수정] HSMS 메시지 구성 및 전송"""
        if self.writer.is_closing():
            raise RuntimeError("Connection is closing")

        async with self._send_lock:
            try:
                s_with_w_bit = s | 0x80 if w_bit else s
                
                ptype = 0
                stype = msg_type.value if msg_type != HsmsMessageType.DATA_MESSAGE else 0
                
                # 제어 메시지일 경우 S와 F는 0으로 설정
                if msg_type != HsmsMessageType.DATA_MESSAGE:
                    s_with_w_bit = 0
                    f = 0

                # PType과 SType을 2바이트 필드로 조합
                ptype_stype_field = (ptype << 8) | stype

                header = struct.pack('>HBBHI', 0, s_with_w_bit, f, ptype_stype_field, system_bytes)
                payload = header + body
                length_bytes = len(payload).to_bytes(4, 'big')
                
                self.writer.write(length_bytes + payload)
                await self.writer.drain()
                
                self.logger.debug(f"SENT: Type={msg_type.name} S{s}F{f} W={w_bit} SB={system_bytes}")
                
            except Exception as e:
                self.logger.error(f"Failed to send HSMS message: {e}")
                raise