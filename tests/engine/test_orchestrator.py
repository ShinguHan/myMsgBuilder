import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from secs_simulator.engine.orchestrator import Orchestrator
import asyncio


# 이 파일의 모든 테스트를 pytest-asyncio가 비동기 모드로 실행하도록 설정합니다.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_device_agents():
    """
    Orchestrator가 사용할 가짜 DeviceAgent 클래스와 인턴스들을 생성하는 Fixture.
    테스트 실행 전에 미리 준비되어 테스트 함수에 '주입'됩니다.
    """
    # DeviceAgent 클래스 자체를 모킹합니다.
    # 이제 'DeviceAgent(...)'를 호출하면 실제 클래스 대신 이 Mock이 사용됩니다.
    with patch('secs_simulator.engine.orchestrator.DeviceAgent', new_callable=MagicMock) as MockAgentClass:
        # 가짜 Agent 인스턴스들을 미리 만들어 둡니다.
        mock_cv01 = AsyncMock()
        mock_stk01 = AsyncMock()

        # Orchestrator가 'CV_01'을 찾을 때와 'STK_01'을 찾을 때
        # 각각 다른 가짜 인스턴스를 반환하도록 설정합니다.
        # side_effect는 호출될 때마다 다른 결과를 내도록 할 수 있습니다.
        def agent_factory(device_id, *args, **kwargs):
            if device_id == "CV_01":
                return mock_cv01
            elif device_id == "STK_01":
                return mock_stk01
            return AsyncMock()

        MockAgentClass.side_effect = agent_factory

        # 테스트 코드에서 검증을 위해 가짜 인스턴스들에 접근할 수 있도록 딕셔너리를 반환합니다.
        yield {
            "CV_01": mock_cv01,
            "STK_01": mock_stk01
        }


async def test_orchestrator_runs_simple_scenario(mock_device_agents):
    """
    Orchestrator가 간단한 시나리오를 읽고,
    올바른 순서로 Agent들의 메소드를 호출하는지 테스트합니다.
    """
    # 1. 테스트용 시나리오 정의 (Orchestrator의 실제 동작에 맞게 수정)
    scenario_data = {
        'name': 'Simple Test',
        'steps': [
            {
                'device_id': 'CV_01',
                'message': {'s': 1, 'f': 13, 'body': ['A', 'TEST']}
            },
            {
                # 'delay_after_ms' -> 'delay', 100ms -> 0.1s
                'delay': 0.1
            },
            {
                'device_id': 'STK_01',
                'message': {'s': 2, 'f': 1, 'body': []}
            }
        ]
    }

    # 2. Orchestrator 생성 및 시나리오 실행
    # status_callback은 이 테스트의 관심사가 아니므로 가짜(AsyncMock)로 넘겨줍니다.
    orchestrator = Orchestrator(status_callback=AsyncMock())
    # patch된 load_device_configs를 모의 호출하기 위해 빈 설정을 로드합니다.
    orchestrator._agents = { "CV_01": mock_device_agents["CV_01"], "STK_01": mock_device_agents["STK_01"] }

    orchestrator.run_scenario(scenario_data)

    # run_scenario는 백그라운드 태스크를 생성하므로, 완료될 때까지 잠시 기다려줍니다.
    await asyncio.sleep(0.2) # 시나리오의 delay(0.1s)보다 긴 시간

    # 3. 검증
    cv_agent = mock_device_agents['CV_01']
    stk_agent = mock_device_agents['STK_01']

    # CV_01의 send_message가 올바른 인자와 함께 호출되었는지 확인
    # w_bit 제거, body_obj -> body로 수정
    cv_agent.send_message.assert_awaited_once_with(
        s=1, f=13, body=['A', 'TEST']
    )

    # STK_01의 send_message가 올바른 인자와 함께 호출되었는지 확인
    # w_bit 제거, body_obj -> body로 수정
    stk_agent.send_message.assert_awaited_once_with(
        s=2, f=1, body=[]
    )