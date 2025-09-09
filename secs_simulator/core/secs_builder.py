import struct
from typing import List
from .models import SecsItem

# SECS-II 데이터 타입 코드 (6-bit)
TYPE_CODES = {
    'L':    0b000000, 'A':    0b010000, 'B':    0b001000,
    'BOOL': 0b001001, 'I1':   0b011001, 'I2':   0b011010,
    'I4':   0b011100, 'U1':   0b101001, 'U2':   0b101010,
    'U4':   0b101011, 'F4':   0b100100, 'F8':   0b100001,
}

def build_secs_body(items: List[SecsItem]) -> bytes:
    """
    SecsItem 객체 리스트로부터 SECS-II 메시지 Body의 바이너리를 생성합니다.
    """
    if not isinstance(items, list):
        raise TypeError("SECS message body must be a list of SecsItem objects.")

    # 각 SecsItem을 바이너리로 변환하여 합칩니다.
    body_parts = [_build_item(item) for item in items]
    return b''.join(body_parts)

def _build_item(item: SecsItem) -> bytes:
    """단일 SecsItem을 포맷, 길이, 값을 포함한 바이너리로 변환합니다."""
    item_type = item.type.upper()
    if item_type not in TYPE_CODES:
        raise ValueError(f"Unknown SECS data type: {item.type}")

    # 1. 값을 먼저 인코딩하여 길이를 결정합니다.
    if item_type == 'L':
        # 재귀 호출을 통해 리스트 내부의 아이템들을 바이너리로 변환합니다.
        value_bytes = build_secs_body(item.value)
        length = len(item.value)  # 리스트는 아이템의 개수가 길이가 됩니다.
    elif item_type == 'A':
        value_bytes = str(item.value).encode('ascii')
        length = len(value_bytes)
    else: # 숫자, 바이너리, 불리언 타입
        format_map = {
            'B': '>B', 'BOOL': '>?',
            'I1': '>b', 'I2': '>h', 'I4': '>i',
            'U1': '>B', 'U2': '>H', 'U4': '>I',
            'F4': '>f', 'F8': '>d'
        }
        # B 타입은 bytes가 아닐 경우 단일 바이트로 처리
        if item_type == 'B' and isinstance(item.value, int):
             value_bytes = struct.pack('>B', item.value)
        elif item_type == 'B' and isinstance(item.value, bytes):
             value_bytes = item.value
        else:
             value_bytes = struct.pack(format_map[item_type], item.value)
        length = len(value_bytes)

    # 2. 길이를 나타내는 바이트를 결정합니다 (1~3 바이트).
    if length <= 255:
        length_bytes = length.to_bytes(1, 'big')
        num_length_bytes = 1
    elif length <= 65535:
        length_bytes = length.to_bytes(2, 'big')
        num_length_bytes = 2
    else: # 16777215 (0xFFFFFF)
        length_bytes = length.to_bytes(3, 'big')
        num_length_bytes = 3

    # 3. 포맷 바이트를 생성합니다. (타입 코드 << 2 | 길이 바이트 수)
    format_byte = (TYPE_CODES[item_type] << 2) | num_length_bytes
    
    return format_byte.to_bytes(1, 'big') + length_bytes + value_bytes

