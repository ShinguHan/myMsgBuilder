import pytest
from secs_simulator.core.models import SecsItem
from secs_simulator.core.secs_builder import build_secs_body

# 테스트할 데이터: (테스트 이름, 입력 SecsItem 리스트, 예상 결과 바이트) 튜플의 리스트
# pytest.mark.parametrize를 사용하여 이 데이터들을 하나의 테스트 함수로 검증합니다.
SECS_BODY_TEST_CASES = [
    (
        "Simple_ASCII",
        [SecsItem(type='A', value='TEST')],
        b'\x41\x04TEST'  # 포맷: A, 길이: 4, 값: 'TEST'
    ),
    (
        "Simple_U4_Integer",
        [SecsItem(type='U4', value=256)],
        b'\xac\x04\x00\x00\x01\x00' # 포맷: U4, 길이: 4, 값: 256 (big-endian)
    ),
    (
        "Empty_List",
        [SecsItem(type='L', value=[])],
        b'\x01\x00' # 포맷: L, 길이: 0
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
        # L[3] (A'ITEM1', U2'100', L[1] (B'\x01\x02'))
        b'\x01\x11' +                      # L, 전체 길이 17
        b'\x41\x05ITEM1' +                 # A, 길이 5, 'ITEM1'
        b'\xa9\x02\x00\x64' +              # U2, 길이 2, 100
        b'\x01\x06' +                      # L, 길이 6
        b'\x21\x02\x01\x02'                # B, 길이 2, 0x01, 0x02
    ),
]

@pytest.mark.parametrize("test_name, body_list, expected_bytes", SECS_BODY_TEST_CASES)
def test_build_secs_body_with_various_types(test_name, body_list, expected_bytes):
    """
    다양한 SECS Body 구조가 정확한 바이너리로 변환되는지 테스트합니다.
    하나의 함수로 여러 케이스를 검증하여 매우 효율적입니다.
    """
    actual_bytes = build_secs_body(body_list)
    assert actual_bytes == expected_bytes

def test_build_body_with_invalid_type_raises_error():
    """
    지원하지 않는 데이터 타입을 사용했을 때 ValueError가 발생하는지 테스트합니다.
    """
    invalid_body = [SecsItem(type='INVALID_TYPE', value='some_value')]
    
    with pytest.raises(ValueError) as excinfo:
        build_secs_body(invalid_body)
    
    # 예외 메시지에 'Unknown'이라는 단어가 포함되어 있는지 확인합니다.
    assert "Unknown SECS data type" in str(excinfo.value)
