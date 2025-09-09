import struct
from typing import List, Dict, Any

# A mapping from SECS-II type identifiers to their binary format codes.
# Using a dictionary improves readability and maintainability.
TYPE_CODES: Dict[str, int] = {
    'L':    0b000000, 'A':    0b010000, 'B':    0b001000,
    'BOOL': 0b001001, 'I1':   0b011001, 'I2':   0b011010,
    'I4':   0b011100, 'U1':   0b101001, 'U2':   0b101010,
    'U4':   0b101011, 'F4':   0b100100, 'F8':   0b100001,
}

def build_message_body(data_obj: List[Dict[str, Any]]) -> bytes:
    """
    Builds a SECS-II message body from a list of Python dictionaries.
    e.g., [{'type': 'L', 'value': [{'type': 'A', 'value': 'TEST'}]}]
    """
    if not isinstance(data_obj, list):
        raise TypeError("SECS message body must be a list of items.")

    body_parts = [_build_item(item['type'], item['value']) for item in data_obj]
    return b''.join(body_parts)

def _build_item(item_type: str, item_value: Any) -> bytes:
    """Builds a single SECS-II item (format byte, length bytes, value bytes)."""
    item_type_upper = item_type.upper()
    if item_type_upper not in TYPE_CODES:
        raise ValueError(f"Unsupported SECS data type: {item_type}")

    # 1. Encode the value first to determine its length.
    if item_type_upper == 'L':
        value_bytes = build_message_body(item_value)
        length = len(item_value)  # For lists, length is the number of elements.
    elif item_type_upper == 'A':
        value_bytes = str(item_value).encode('ascii')
        length = len(value_bytes)
    elif item_type_upper == 'B':
        value_bytes = bytes(item_value)
        length = len(value_bytes)
    else: # Numeric and boolean types
        # Using a map for format strings and sizes for cleaner code.
        format_map = {
            'BOOL': ('>?', 1), 'I1': ('>b', 1), 'I2': ('>h', 2), 'I4': ('>i', 4),
            'U1': ('>B', 1), 'U2': ('>H', 2), 'U4': ('>I', 4),
            'F4': ('>f', 4), 'F8': ('>d', 8),
        }
        format_str, size = format_map[item_type_upper]
        value_bytes = struct.pack(format_str, item_value)
        length = size

    # 2. Determine the number of bytes needed to represent the length.
    try:
        # A more Pythonic way to handle length bytes using bit_length.
        num_length_bytes = (length.bit_length() + 7) // 8
        if num_length_bytes == 0 and length == 0: num_length_bytes = 1
        if num_length_bytes > 3: raise ValueError
        length_bytes = length.to_bytes(num_length_bytes, 'big')
    except ValueError:
        raise ValueError(f"Item length {length} exceeds the maximum of 16,777,215 bytes.")

    # 3. Construct the format byte.
    # Bits 8-3 are the type code, Bits 2-1 are the number of length bytes.
    format_byte = (TYPE_CODES[item_type_upper] << 2) | num_length_bytes
    
    return format_byte.to_bytes(1, 'big') + length_bytes + value_bytes

