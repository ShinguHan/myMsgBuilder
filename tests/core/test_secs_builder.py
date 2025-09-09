import pytest
from secs_simulator.core.models import SecsItem
from secs_simulator.core.secs_builder import build_secs_body

# 테스트할 데이터: (테스트 이름, 입력 SecsItem 리스트, 예상 결과 바이트) 튜플의 리스트
SECS_BODY_TEST_CASES = [
    (
        "Simple_ASCII",
        [SecsItem(type='A', value='TEST')],
        b'\x41\x04TEST'
    ),
    (
        "Simple_U4_Integer",
        [SecsItem(type='U4', value=256)],
        # 포맷 바이트를 0xac -> 0xad로 수정
        b'\xad\x04\x00\x00\x01\x00'
    ),
    (
        "Empty_List",
        [SecsItem(type='L', value=[])],
        b'\x01\x00'
    ),
    (
        "Nested_List_with_Multiple_Types",
        [
            SecsItem(type='L', value=[
                SecsItem(type='A', value='ITEM1'),
                SecsItem(type='U2', value=100),
                SecsItem(type='L', value=[
                    SecsItem(type='B', value=b'\x01\x02')
                ])
            ])
        ],
        # 표준에 맞게 리스트 길이를 아이템 개수(3)로,
        # 내부 리스트 길이도 아이템 개수(1)로 수정
        b'\x01\x03' +                      # L, 3 items
        b'\x41\x05ITEM1' +                 # A, len 5, 'ITEM1'
        b'\xa9\x02\x00\x64' +              # U2, len 2, 100
        b'\x01\x01' +                      # L, 1 item
        b'\x21\x02\x01\x02'                # B, len 2, 0x01, 0x02
    ),
]

@pytest.mark.parametrize("test_name, body_list, expected_bytes", SECS_BODY_TEST_CASES)
def test_build_secs_body_with_various_types(test_name, body_list, expected_bytes):
    """ 다양한 SECS Body 구조가 정확한 바이너리로 변환되는지 테스트합니다. """
    actual_bytes = build_secs_body(body_list)
    assert actual_bytes == expected_bytes

def test_build_body_with_invalid_type_raises_error():
    """ 지원하지 않는 데이터 타입을 사용했을 때 ValueError가 발생하는지 테스트합니다. """
    invalid_body = [SecsItem(type='INVALID_TYPE', value='some_value')]
    
    with pytest.raises(ValueError) as excinfo:
        build_secs_body(invalid_body)
    
    assert "Unknown SECS data type" in str(excinfo.value)

