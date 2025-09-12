# log_importer.py
import json
import struct
from typing import List, Dict, Any

# 🤩 프로젝트의 자체 핵심 파서를 직접 사용합니다!
from secs_simulator.core.secs_parser import parse_body
from secs_simulator.core.models import SecsItem

# universal_parser는 이제 CSV를 읽는 역할만 충실히 수행합니다.
from secs_simulator.parsers.universal_parser import parse_log_with_profile

def convert_secs_item_to_dict(item: SecsItem) -> Dict[str, Any]:
    """SecsItem 객체를 JSON으로 직렬화 가능한 딕셔너리로 변환합니다."""
    if item.type == 'L':
        return {
            "type": "L",
            "value": [convert_secs_item_to_dict(sub_item) for sub_item in item.value]
        }
    if item.type == 'B' and isinstance(item.value, bytes):
         return {"type": "B", "value": item.value.hex().upper()}
    return {"type": item.type, "value": item.value}


def get_messages_from_log(log_filepath: str, profile_path: str) -> List[Dict[str, Any]]:
    """
    로그 파일을 읽고, 신뢰성 높은 내부 파서를 사용하여 시뮬레이터가 사용할 수 있는
    표준 dict 리스트 형식으로 변환합니다.
    """
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
    except Exception as e:
        print(f"Error loading profile file '{profile_path}': {e}")
        return []

    parsed_log_entries = parse_log_with_profile(log_filepath, profile)
    
    processed_messages = []
    for entry in parsed_log_entries:
        if entry.get("MethodID") != "SecsProtocolLogger.logMessage":
            continue

        raw_full_hex = entry.get('BinaryData', '')
        # 헤더(10) + Body 최소길이를 고려하여 20자 이상인 경우만 처리
        if not raw_full_hex or len(raw_full_hex) < 20: # 10 bytes * 2 hex chars/byte
            continue
            
        full_binary = bytes.fromhex(raw_full_hex)
        
        # 🎯 [수정] 헤더 길이를 10바이트로 수정하고, unpack 포맷을 로그 파일에 맞게 변경했습니다.
        header_bytes = full_binary[0:10]
        
        try:
            # 포맷: SessionID(H), S+W(B), F(B), PType(H), SystemBytes(4s)
            # 총 2 + 1 + 1 + 2 + 4 = 10 바이트
            _session_id, s_with_w_bit, f, _ptype, system_bytes_raw = struct.unpack('>HBBH4s', header_bytes)
            
            # 4s로 읽은 System Bytes를 정수로 변환합니다.
            system_bytes = int.from_bytes(system_bytes_raw, 'big')

        except struct.error as e:
            print(f"Skipping malformed 10-byte header: {e}")
            continue

        w_bit = bool(s_with_w_bit & 0x80)
        s = s_with_w_bit & 0x7F

        # 헤더(10바이트) 이후의 모든 데이터를 Body로 간주합니다.
        body_bytes = full_binary[10:]
        
        parsed_body_items = parse_body(body_bytes)
        body_for_json = [convert_secs_item_to_dict(item) for item in parsed_body_items]

        processed_messages.append({
            "s": s,
            "f": f,
            "w_bit": w_bit,
            "system_bytes": system_bytes,
            "message": {
                "s": s,
                "f": f,
                "w_bit": w_bit,
                "body": body_for_json
            }
        })
        
    return processed_messages