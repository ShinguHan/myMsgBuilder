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
    return _parse_body_recursive(body_io)

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

        # A mapping from format code to (type_str, value_parser_lambda)
        # This approach is more scalable and readable than a large if/elif/else block.
        type_map = {
            0b000000: ('L', lambda: [_parse_body_recursive(body_io) for _ in range(length)]),
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
            
            # Flatten nested lists for 'L' type
            if item_type == 'L':
                value = [item for sublist in parsed_value for item in sublist]
            # Simplify single-item arrays to a single value
            elif isinstance(parsed_value, list) and len(parsed_value) == 1:
                value = parsed_value[0]
            else:
                value = parsed_value
        else:
            # Skip unhandled types to allow parsing of the rest of the message
            body_io.read(length)

        if value is not None:
            items.append(SecsItem(type=item_type, value=value))

    except (IndexError, struct.error) as e:
        # Gracefully handle malformed data without crashing.
        print(f"Parsing warning: Encountered malformed data. {e}")
    
    return items

