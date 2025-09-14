import struct
from typing import List, Union # Union 추가
from .models import SecsItem

# SECS-II 데이터 타입 코드 (6-bit)
TYPE_CODES = {
    'L':    0b000000, 'A':    0b010000, 'B':    0b001000,
    'BOOL': 0b001001, 'I1':   0b011001, 'I2':   0b011010,
    'I4':   0b011100, 'U1':   0b101001, 'U2':   0b101010,
    'U4':   0b101011, 'F4':   0b100100, 'F8':   0b100001,
}

# ✅ [추가] 딕셔너리를 SecsItem 객체로 변환하는 똑똑한 헬퍼 함수
def _to_secs_item(item_data: Union[dict, SecsItem]) -> SecsItem:
    """
    딕셔너리 또는 SecsItem을 받아 항상 SecsItem 객체를 반환합니다.
    재귀적으로 동작하여 중첩된 리스트도 모두 변환합니다.
    """
    if isinstance(item_data, SecsItem):
        return item_data  # 이미 올바른 타입이면 그대로 반환

    item_type = item_data.get('type')
    item_value = item_data.get('value')
    
    if item_type == 'L' and isinstance(item_value, list):
        # 리스트 안의 모든 항목들을 재귀적으로 변환
        value = [_to_secs_item(sub_item) for sub_item in item_value]
    else:
        value = item_value
        
    return SecsItem(type=item_type, value=value)

# ✅ [수정] build_secs_body 함수가 변환 로직을 사용하도록 수정
def build_secs_body(items: List[Union[dict, SecsItem]]) -> bytes:
    """
    SecsItem 객체 또는 dict 객체 리스트로부터
    SECS-II 메시지 Body의 바이너리를 생성합니다.
    """
    if not isinstance(items, list):
        raise TypeError("SECS message body must be a list of SecsItem or dict objects.")

    # [핵심 수정] 본격적인 빌드 전, 모든 항목을 SecsItem 객체로 변환합니다.
    secs_items = [_to_secs_item(item) for item in items]

    # 각 SecsItem을 바이너리로 변환하여 합칩니다.
    body_parts = [_build_item(item) for item in secs_items]
    return b''.join(body_parts)

def _build_item(item: SecsItem) -> bytes:
    """단일 SecsItem을 포맷, 길이, 값을 포함한 바이너리로 변환합니다."""
    item_type = item.type.upper()
    if item_type not in TYPE_CODES:
        raise ValueError(f"Unknown SECS data type: {item.type}")

    # 1. 값을 먼저 인코딩하여 길이를 결정합니다.
    if item_type == 'L':
        value_bytes = build_secs_body(item.value)
        length = len(item.value)
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
        
        # ✅ [핵심 수정] 숫자 타입의 값이 리스트일 경우와 단일 값일 경우를 모두 처리합니다.
        
        # B 타입은 raw bytes일 수 있으므로 먼저 처리합니다.
        if item_type == 'B' and isinstance(item.value, bytes):
             value_bytes = item.value
        else:
            # 값이 리스트가 아니면, 처리를 위해 임시 리스트로 만듭니다.
            values_to_pack = item.value if isinstance(item.value, list) else [item.value]
            
            try:
                # 리스트의 각 항목을 순회하며 pack하고, 그 결과 바이너리를 모두 합칩니다.
                value_bytes = b''.join([struct.pack(format_map[item_type], v) for v in values_to_pack])
            except TypeError as e:
                # 에러 발생 시 더 상세한 정보를 제공합니다.
                raise TypeError(
                    f"Type mismatch for SECS type '{item_type}'. "
                    f"Expected numbers, but got: {values_to_pack}. Original error: {e}"
                ) from e

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

