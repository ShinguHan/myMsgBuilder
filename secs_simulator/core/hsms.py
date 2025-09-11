import asyncio
import struct
from enum import IntEnum
from typing import Optional

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
    """Manages the lifecycle and communication for a single HSMS connection."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.peername = writer.get_extra_info('peername')
        self.is_selected = False
        self._system_bytes_counter = 0
        print(f"HSMS: New connection from {self.peername}")

    async def handle_connection(self) -> None:
        """The main loop for reading and processing incoming HSMS messages."""
        try:
            while True:
                length_bytes = await self.reader.readexactly(4)
                message_length = int.from_bytes(length_bytes, 'big')
                message_payload = await self.reader.readexactly(message_length)
                await self._process_message(message_payload)
        except asyncio.IncompleteReadError:
            print(f"HSMS: Connection closed by peer {self.peername}")
        except Exception as e:
            print(f"HSMS: An error occurred on connection {self.peername}: {e}")
        finally:
            if not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()

    async def _process_message(self, payload: bytes) -> None:
        """Parses the message header and routes to the appropriate handler."""
        header = payload[:10]
        body = payload[10:]
        
        _, stype, s, f, ptype, system_bytes = struct.unpack('>HBBHHI', header)
        w_bit = bool(s & 0x80)
        s &= 0x7F # Unset W-bit to get the real stream number
        msg_type = HsmsMessageType(stype)

        print(f"HSMS RECV ({self.peername}): Type={msg_type.name} S{s}F{f} W={w_bit} SysBytes={system_bytes}")

        handler_map = {
            HsmsMessageType.SELECT_REQ: self._handle_select_req,
            HsmsMessageType.DATA_MESSAGE: self._handle_data_message,
            # Other handlers can be added here
        }

        handler = handler_map.get(msg_type)
        if handler:
            await handler(s, f, w_bit, system_bytes, body)
        else:
            print(f"HSMS: No handler for message type {msg_type.name}")

    async def _handle_select_req(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Handles a Select.req and responds with Select.rsp."""
        print("HSMS: Responding to Select.req with Select.rsp")
        # Status 0 = Selected, 1 = Already Selected, 2 = Not Ready
        await self.send_hsms_message(HsmsMessageType.SELECT_RSP, system_bytes)
        self.is_selected = True

    async def _handle_data_message(self, s: int, f: int, w: bool, system_bytes: int, body: bytes) -> None:
        """Handles an incoming data message."""
        parsed = parse_body(body)
        print(f"HSMS: Parsed data message body: {parsed}")
        
        # For now, just send a basic S1F0 Abort acknowledgement for any S1F* message.
        if s == 1:
            await self.send_secs_message(1, 0, system_bytes)

    async def send_secs_message(self, s: int, f: int, system_bytes: int, body_obj: Optional[list] = None) -> None:
        """Constructs and sends a SECS-II data message."""
        body_bytes = build_secs_body(body_obj or [])
        await self.send_hsms_message(HsmsMessageType.DATA_MESSAGE, system_bytes, s, f, body=body_bytes)

    # ✅ [버그 수정] System Bytes 카운터를 관리하는 메서드 추가
    def get_next_system_bytes(self) -> int:
        """다음에 사용할 System Bytes 값을 반환하고 카운터를 1 증가시킵니다."""
        self._system_bytes_counter += 1
        return self._system_bytes_counter

    async def send_hsms_message(
        self, msg_type: HsmsMessageType, system_bytes: int, 
        s: int = 0, f: int = 0, w_bit: bool = False, body: bytes = b''
    ) -> None:
        """Constructs and sends a full HSMS message."""
        if w_bit: s |= 0x80

        header = struct.pack('>HBBHHI', 0, msg_type.value, s, f, 0, system_bytes)
        payload = header + body
        length_bytes = len(payload).to_bytes(4, 'big')
        
        self.writer.write(length_bytes + payload)
        await self.writer.drain()
        print(f"HSMS SENT ({self.peername}): Type={msg_type.name} S{s&0x7F}F{f} W={w_bit} SysBytes={system_bytes}")
