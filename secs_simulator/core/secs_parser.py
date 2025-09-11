import struct
import io
from typing import List

from .models import SecsItem

def parse_body(body_bytes: bytes) -> List[SecsItem]:
    """
    Parses a SECS-II message body from bytes into a list of SecsItem objects.
    This is the public entry point for the parser.
    """
    body_io = io.BytesIO(body_bytes)
    items: List[SecsItem] = []
    # ✅ [개선] 메시지 바디 전체를 파싱할 때까지 아이템을 순차적으로 읽도록 루프를 추가합니다.
    while body_io.tell() < len(body_bytes):
        items.extend(_parse_body_recursive(body_io))
    return items

def _parse_body_recursive(body_io: io.BytesIO) -> List[SecsItem]:
    """
    Recursively parses a binary stream to create a structure of SecsItem objects.
    Refactored from myLogMaster's universal_parser.py to use SecsItem dataclass.
    """
    items: List[SecsItem] = []
    try:
        format_code_byte = body_io.read(1)
        if not format_code_byte:
            return items
        
        format_char = format_code_byte[0]
        num_length_bytes = format_char & 0b00000011

        length_bytes = body_io.read(num_length_bytes)
        length = int.from_bytes(length_bytes, 'big')

        data_format_code = format_char >> 2
        
        item_type = "Unknown"
        value = None

        type_map = {
            # ✅ [개선] L타입 파싱 시 재귀 호출 결과를 바로 리스트로 만들어 중첩 구조를 보존합니다.
            0b000000: ('L', lambda: [item for _ in range(length) for item in _parse_body_recursive(body_io)]),
            0b010000: ('A', lambda: body_io.read(length).decode('ascii', errors='replace')),
            0b001000: ('B', lambda: body_io.read(length)),
            0b001001: ('BOOL', lambda: [struct.unpack('>?', body_io.read(1))[0] for _ in range(length)]),
            0b011001: ('I1', lambda: [struct.unpack('>b', body_io.read(1))[0] for _ in range(length)]),
            0b011010: ('I2', lambda: [struct.unpack('>h', body_io.read(2))[0] for _ in range(length // 2)]),
            0b011100: ('I4', lambda: [struct.unpack('>i', body_io.read(4))[0] for _ in range(length // 4)]),
            0b101001: ('U1', lambda: [struct.unpack('>B', body_io.read(1))[0] for _ in range(length)]),
            0b101010: ('U2', lambda: [struct.unpack('>H', body_io.read(2))[0] for _ in range(length // 2)]),
            0b101011: ('U4', lambda: [struct.unpack('>I', body_io.read(4))[0] for _ in range(length // 4)]),
            0b100001: ('F8', lambda: [struct.unpack('>d', body_io.read(8))[0] for _ in range(length // 8)]),
            0b100100: ('F4', lambda: [struct.unpack('>f', body_io.read(4))[0] for _ in range(length // 4)]),
        }

        if data_format_code in type_map:
            item_type, parser = type_map[data_format_code]
            parsed_value = parser()
            
            # ✅ [개선] L타입에 대한 별도 처리 및 단일 아이템 리스트 단순화 로직을 제거하여
            # 모든 데이터 구조가 원본 그대로 유지되도록 합니다.
            value = parsed_value
        else:
            body_io.read(length)

        if value is not None:
            items.append(SecsItem(type=item_type, value=value))

    except (IndexError, struct.error) as e:
        print(f"Parsing warning: Encountered malformed data. {e}")
    
    return items