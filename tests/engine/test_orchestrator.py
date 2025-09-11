import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.engine.scenario_manager import ScenarioManager
import asyncio

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_device_agents():
    """Orchestrator가 사용할 가짜 DeviceAgent 클래스와 인스턴스들을 생성하는 Fixture."""
    with patch('secs_simulator.engine.orchestrator.DeviceAgent', new_callable=MagicMock) as MockAgentClass:
        mock_cv01 = AsyncMock()
        mock_stk01 = AsyncMock()

        def agent_factory(device_id, *args, **kwargs):
            if device_id == "CV_01": return mock_cv01
            elif device_id == "STK_01": return mock_stk01
            return AsyncMock()

        MockAgentClass.side_effect = agent_factory
        yield {"CV_01": mock_cv01, "STK_01": mock_stk01}

# ✅ [개선] ScenarioManager를 테스트에서 사용할 수 있도록 Fixture를 추가합니다.
@pytest.fixture
def scenario_manager():
    """테스트용 ScenarioManager 인스턴스를 제공합니다."""
    device_configs = {
        "CV_01": {"host": "127.0.0.1", "port": 5001, "type": "CV"},
        "STK_01": {"host": "127.0.0.1", "port": 5002, "type": "Stocker"}
    }
    return ScenarioManager(device_configs=device_configs, message_library_dir='./resources/messages')

# ✅ [개선] 테스트 케이스를 실제 앱의 데이터 흐름과 유사하게 수정합니다.
async def test_orchestrator_runs_scenario_realistically(mock_device_agents, scenario_manager):
    """
    Orchestrator가 message_id 기반 시나리오를 message body로 변환하여
    올바르게 실행하는지 통합적으로 테스트합니다.
    """
    # 1. 실제 시나리오 파일처럼 'message_id'를 사용하여 시나리오를 정의합니다.
    raw_scenario = {
        'name': 'Realistic Test',
        'steps': [
            {'device_id': 'CV_01', 'message_id': 'S2F41_HostCommand_START', 'delay': 0},
            {'delay': 0.1},
            {'device_id': 'STK_01', 'message_id': 'S5F1_AlarmReport', 'delay': 0}
        ]
    }

    # 2. ScenarioManager를 사용해 시나리오를 Orchestrator가 실행할 수 있는 형태로 가공합니다.
    processed_steps = []
    for step in raw_scenario['steps']:
        if 'message_id' in step:
            dev_type = scenario_manager.get_device_type(step['device_id'])
            msg_body = scenario_manager.get_message_body(dev_type, step['message_id'])
            processed_steps.append({
                "device_id": step['device_id'],
                "message": msg_body,
                "delay": step.get('delay', 0)
            })
        else:
            processed_steps.append(step)
    executable_scenario = {"name": raw_scenario['name'], "steps": processed_steps}

    # 3. Orchestrator를 생성하고 가공된 시나리오를 실행합니다.
    orchestrator = Orchestrator(status_callback=AsyncMock())
    orchestrator._agents = mock_device_agents
    orchestrator.run_scenario(executable_scenario)
    await asyncio.sleep(0.2)

    # 4. 각 Agent의 send_message가 올바른 메시지 본문과 함께 호출되었는지 검증합니다.
    cv_agent = mock_device_agents['CV_01']
    stk_agent = mock_device_agents['STK_01']

    expected_cv_msg = scenario_manager.get_message_body("CV", "S2F41_HostCommand_START")
    cv_agent.send_message.assert_awaited_once_with(
        s=expected_cv_msg['s'], f=expected_cv_msg['f'], body=expected_cv_msg['body']
    )

    expected_stk_msg = scenario_manager.get_message_body("Stocker", "S5F1_AlarmReport")
    stk_agent.send_message.assert_awaited_once_with(
        s=expected_stk_msg['s'], f=expected_stk_msg['f'], body=expected_stk_msg['body']
    )