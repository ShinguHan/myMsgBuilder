import asyncio
import json
from typing import Callable, Awaitable, Dict, Any, List

from secs_simulator.engine.device_agent import DeviceAgent

class Orchestrator:
    """
    여러 DeviceAgent를 관리하고 시나리오에 따라 제어하는 지휘자 클래스.
    시뮬레이션의 전체 흐름을 통제하는 중앙 컨트롤 타워입니다.
    """

    def __init__(self, status_callback: Callable[[str, str], Awaitable]):
        """
        Args:
            status_callback (Callable): UI로 에이전트의 상태를 전달하기 위한 비동기 콜백.
        """
        self._agents: Dict[str, DeviceAgent] = {}
        self._device_configs: Dict[str, Any] = {}
        self._status_callback = status_callback
        self._scenario_task: asyncio.Task | None = None
        self.is_running = False

    def load_device_configs(self, config_path: str) -> List[str]:
        """
        설정 파일로부터 장비 구성을 로드하고 DeviceAgent 인스턴스를 생성합니다.
        
        Returns:
            List[str]: 로드된 장비 ID 목록
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._device_configs = json.load(f)

            for device_id, settings in self._device_configs.items():
                agent = DeviceAgent(
                    device_id=device_id,
                    host=settings['host'],
                    port=settings['port'],
                    status_callback=self._status_callback # UI로 직접 상태 전달
                )
                self._agents[device_id] = agent
            
            print(f"Loaded {len(self._agents)} agents from '{config_path}'")
            return list(self._agents.keys())
        except FileNotFoundError:
            print(f"Error: Device config file not found at '{config_path}'")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{config_path}'")
        except Exception as e:
            print(f"An unexpected error occurred while loading device configs: {e}")
        return []

    def get_device_configs(self) -> Dict[str, Any]:
        """로드된 장비 설정의 복사본을 반환합니다."""
        return self._device_configs.copy()

    async def start_all_agents(self) -> None:
        """등록된 모든 에이전트의 서버를 동시에 시작합니다."""
        print("Starting all device agents...")
        start_tasks = [agent.start() for agent in self._agents.values()]
        await asyncio.gather(*start_tasks)

    async def stop_all_agents(self) -> None:
        """등록된 모든 에이전트를 동시에 중지합니다."""
        print("Stopping all device agents...")
        if self._scenario_task and not self._scenario_task.done():
            self.is_running = False
            self._scenario_task.cancel()
        
        stop_tasks = [agent.stop() for agent in self._agents.values()]
        await asyncio.gather(*stop_tasks)

    def run_scenario(self, scenario_data: Dict[str, Any]) -> None:
        """
        주어진 시나리오를 실행하는 백그라운드 태스크를 시작합니다.
        UI가 멈추지 않도록 즉시 반환합니다.
        """
        if self.is_running:
            print("Scenario is already running.")
            return

        print(f"Starting scenario: {scenario_data.get('name', 'Unnamed')}")
        self.is_running = True
        self._scenario_task = asyncio.create_task(self._run_scenario_steps(scenario_data))

    async def _run_scenario_steps(self, scenario_data: Dict[str, Any]) -> None:
        """실제로 시나리오의 각 스텝을 순차적으로 실행하는 코루틴."""
        try:
            for step in scenario_data.get('steps', []):
                if not self.is_running:
                    print("Scenario stopped by user.")
                    break

                device_id = step.get('device_id')
                target_agent = self._agents.get(device_id)
                if not target_agent:
                    print(f"Scenario Warning: Device '{device_id}' not found.")
                    continue

                # 메시지 전송
                if 'message' in step:
                    message = step['message']
                    await target_agent.send_message(
                        s=message.get('s', 0),
                        f=message.get('f', 0),
                        body=message.get('body')
                    )

                # 스텝 실행 후 지연 (delay가 0보다 클 경우에만)
                if (delay := step.get('delay', 0)) > 0:
                    await asyncio.sleep(delay)
        
        except asyncio.CancelledError:
            print("Scenario execution was cancelled.")
        except Exception as e:
            print(f"An error occurred during scenario execution: {e}")
        finally:
            self.is_running = False
            print("Scenario finished.")
            # 시나리오 종료 상태를 UI에 알림
            await self._status_callback("Orchestrator", "Scenario Finished")
