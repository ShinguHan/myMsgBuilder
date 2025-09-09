import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from secs_simulator.engine.device_agent import DeviceAgent

# 이 파일의 모든 테스트를 pytest-asyncio가 비동기 모드로 실행하도록 설정합니다.
pytestmark = pytest.mark.asyncio


async def test_device_agent_start_calls_start_server_correctly():
    """
    DeviceAgent.start()가 asyncio.start_server를
    올바른 host와 port로 호출하는지 테스트합니다.
    """
    # 1. 테스트 대상 객체 생성
    # 상태 변경 시 호출될 콜백은 테스트에 필요 없으므로 가짜(AsyncMock)로 대체합니다.
    mock_callback = AsyncMock()
    agent = DeviceAgent(
        device_id="test_device",
        host="localhost",
        port=5000,
        status_callback=mock_callback
    )

    # 2. 'asyncio.start_server'를 AsyncMock으로 교체(patch)합니다.
    #    'with' 블록 안에서만 교체되며, 끝나면 원래대로 돌아옵니다.
    with patch('asyncio.start_server', new_callable=AsyncMock) as mock_start_server:
        # 3. 테스트할 메소드 실행
        await agent.start()

        # 4. 검증:
        # - start_server가 await와 함께 정확히 한 번 호출되었는지 확인합니다.
        mock_start_server.assert_awaited_once()

        # - 호출될 때 사용된 인자(host, port)가 올바른지 확인합니다.
        call_args, call_kwargs = mock_start_server.call_args
        # 키워드 인자(kwargs) 대신 위치 인자(args)를 확인하도록 수정
        assert call_args[1] == 'localhost' # 두 번째 위치 인자가 host
        assert call_args[2] == 5000      # 세 번째 위치 인자가 port

        # - 상태 콜백이 "Listening" 메시지와 함께 호출되었는지 확인합니다.
        mock_callback.assert_awaited_with("test_device", "Listening on localhost:5000")

