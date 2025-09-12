# secs_simulator/engine/orchestrator.py

import asyncio
import json
from typing import Callable, Awaitable, Dict, Any

from secs_simulator.engine.device_agent import DeviceAgent

class Orchestrator:
    """
    여러 DeviceAgent를 관리하고 시나리오에 따라 제어하는 지휘자 클래스.
    """

    def __init__(self, status_callback: Callable[[str, str, str], Awaitable]):
        """
        Args:
            status_callback (Callable): UI로 에이전트의 상태를 전달하기 위한 비동기 콜백.
        """
        self._agents: Dict[str, DeviceAgent] = {}
        self._device_configs: Dict[str, Any] = {}
        self._status_callback = status_callback
        self._scenario_task: asyncio.Task | None = None
        self.is_running = False

    def load_device_configs(self, config_path: str) -> Dict[str, Any]:
        """
        설정 파일로부터 장비 구성을 로드하고 DeviceAgent 인스턴스를 생성합니다.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._device_configs = json.load(f)

            for device_id, settings in self._device_configs.items():
                agent = DeviceAgent(
                    device_id=device_id,
                    host=settings['host'],
                    port=settings['port'],
                    status_callback=self._status_callback
                )
                self._agents[device_id] = agent
            
            print(f"Loaded {len(self._agents)} agents from '{config_path}'")
            return self._device_configs
        except FileNotFoundError:
            print(f"Error: Device config file not found at '{config_path}'")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{config_path}'")
        except Exception as e:
            print(f"An unexpected error occurred while loading device configs: {e}")
        return {}

    def get_device_configs(self) -> Dict[str, Any]:
        """로드된 장비 설정의 복사본을 반환합니다."""
        return self._device_configs.copy()

    async def start_all_agents(self) -> None:
        print("Starting all device agents...")
        start_tasks = [agent.start() for agent in self._agents.values()]
        await asyncio.gather(*start_tasks)

    async def stop_all_agents(self) -> None:
        print("Stopping all device agents...")
        if self._scenario_task and not self._scenario_task.done():
            self.is_running = False
            self._scenario_task.cancel()
        
        stop_tasks = [agent.stop() for agent in self._agents.values()]
        await asyncio.gather(*stop_tasks)

    def run_scenario(self, scenario_data: Dict[str, Any]) -> None:
        if self.is_running:
            print("Scenario is already running.")
            return

        print(f"Starting scenario: {scenario_data.get('name', 'Unnamed')}")
        self.is_running = True
        self._scenario_task = asyncio.create_task(self._run_scenario_steps(scenario_data))

    async def _run_scenario_steps(self, scenario_data: Dict[str, Any]) -> None:
        """✅ [핵심 수정] 'send'와 'wait_recv' 액션을 모두 처리하도록 개선된 실행기입니다."""
        try:
            for step in scenario_data.get('steps', []):
                if not self.is_running:
                    print("Scenario stopped by user.")
                    break

                device_id = step.get('device_id')
                target_agent = self._agents.get(device_id)

                # --- 'wait_recv' 액션 처리 ---
                if 'wait_recv' in step:
                    if not target_agent:
                        print(f"Scenario Warning: Device '{device_id}' not found for wait_recv.")
                        continue
                    
                    match_criteria = step['wait_recv']
                    s = match_criteria.get('s')
                    f = match_criteria.get('f')
                    timeout = step.get('timeout', 10.0) # 기본 타임아웃 10초

                    if s is not None and f is not None:
                        result = await target_agent.wait_for_message(s, f, timeout)
                        if result is None:
                            error_msg = f"Scenario FAIL: Timed out waiting for S{s}F{f} from {device_id}"
                            print(error_msg)
                            await self._status_callback("Orchestrator", error_msg, "red")
                            break # 타임아웃 시 시나리오 중단
                    else:
                        print(f"Scenario Warning: Invalid 'wait_recv' criteria for device '{device_id}'.")
                
                # --- 'message' (send) 액션 처리 ---
                if 'message' in step:
                    if not target_agent:
                        print(f"Scenario Warning: Device '{device_id}' not found for send message.")
                        continue

                    message = step['message']
                    await target_agent.send_message(
                        s=message.get('s', 0),
                        f=message.get('f', 0),
                        body=message.get('body')
                    )

                # --- Delay 처리 ---
                if (delay := step.get('delay', 0)) > 0:
                    await asyncio.sleep(delay)
        
        except asyncio.CancelledError:
            print("Scenario execution was cancelled.")
        except Exception as e:
            print(f"An error occurred during scenario execution: {e}")
        finally:
            self.is_running = False
            print("Scenario finished.")
            await self._status_callback("Orchestrator", "Scenario Finished", "blue")

    def send_single_message(self, device_id: str, message: dict):
        """지정된 장비로 단일 SECS 메시지를 즉시 전송합니다."""
        agent = self._agents.get(device_id)
        if not agent:
            print(f"Manual Send Error: Agent '{device_id}' not found.")
            return

        asyncio.create_task(agent.send_message(
            s=message.get('s', 0),
            f=message.get('f', 0),
            body=message.get('body')
        ))
        print(f"Manually sent message to {device_id}: S{message.get('s')}F{message.get('f')}")