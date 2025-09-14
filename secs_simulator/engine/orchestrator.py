import asyncio
import json
from typing import Callable, Awaitable, Dict, Any

from secs_simulator.engine.device_agent import DeviceAgent

class Orchestrator:
    def __init__(self, status_callback: Callable[[str, str, str], Awaitable]):
        self._agents: Dict[str, DeviceAgent] = {}
        self._device_configs: Dict[str, Any] = {}
        self._status_callback = status_callback
        self._scenario_task: asyncio.Task | None = None
        self.is_running = False
        self._last_request_context: Dict[str, int] = {}
        self.config_path: str = ""

    def load_device_configs(self, config_path: str) -> Dict[str, Any]:
        self.config_path = config_path
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._device_configs = json.load(f)

            for device_id, settings in self._device_configs.items():
                agent = DeviceAgent(
                    device_id=device_id,
                    host=settings['host'],
                    port=settings['port'],
                    connection_mode=settings.get('connection_mode', 'Passive'),
                    status_callback=self._status_callback,
                    # JSON 파일에서 타임아웃 값들을 읽어서 전달
                    t3=settings.get('t3', 10),
                    t5=settings.get('t5', 10),
                    t6=settings.get('t6', 5),
                    t7=settings.get('t7', 10)
                )
                self._agents[device_id] = agent
            
            print(f"Loaded {len(self._agents)} agents from '{config_path}'")
            return self._device_configs
        except FileNotFoundError:
            print(f"Error: Device config file not found at '{config_path}'")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{config_path}'")
        return {}

    def save_device_configs(self) -> bool:
        if not self.config_path:
            return False
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._device_configs, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving device configs: {e}")
            return False

    def add_device(self, device_id: str, config: dict) -> bool:
        if device_id in self._device_configs:
            print(f"Error: Device ID '{device_id}' already exists.")
            return False
        
        self._device_configs[device_id] = config
        agent = DeviceAgent(
            device_id=device_id,
            host=config['host'],
            port=config['port'],
            connection_mode=config.get('connection_mode', 'Passive'),
            status_callback=self._status_callback,
            # 새로 추가된 장비의 타임아웃 값도 전달
            t3=config.get('t3', 10),
            t5=config.get('t5', 10),
            t6=config.get('t6', 5),
            t7=config.get('t7', 10)
        )
        self._agents[device_id] = agent
        return self.save_device_configs()

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

    async def start_agent(self, device_id: str):
        agent = self._agents.get(device_id)
        if agent:
            await agent.start()
        else:
            print(f"Cannot start: Agent '{device_id}' not found.")
            
    async def stop_agent(self, device_id: str):
        agent = self._agents.get(device_id)
        if agent:
            await agent.stop()
        else:
            print(f"Cannot stop: Agent '{device_id}' not found.")

    def run_scenario(self, scenario_data: Dict[str, Any]) -> None:
        if self.is_running:
            print("Scenario is already running.")
            return

        print(f"Starting scenario: {scenario_data.get('name', 'Unnamed')}")
        self.is_running = True
        self._last_request_context.clear()
        self._scenario_task = asyncio.create_task(self._run_scenario_steps(scenario_data))

    async def _run_scenario_steps(self, scenario_data: Dict[str, Any]) -> None:
        """[수정됨] 트랜잭션 기반의 시나리오 스텝을 실행합니다."""
        try:
            for step in scenario_data.get('steps', []):
                if not self.is_running:
                    print("Scenario stopped by user.")
                    break

                device_id = step.get('device_id')
                target_agent = self._agents.get(device_id)
                if not target_agent:
                    continue

                # --- 'Send Message' 스텝 처리 ---
                if 'message' in step:
                    message = step['message']
                    w_bit = message.get('w_bit', False)
                    
                    # 1. 메시지를 보내고, 요청에 사용된 system_bytes를 받습니다.
                    sent_system_bytes = await target_agent.send_message(
                        s=message.get('s', 0),
                        f=message.get('f', 0),
                        w_bit=w_bit,
                        body=message.get('body')
                    )
                    
                    # 2. 만약 응답이 필요한 메시지였다면, 해당 system_bytes를 저장해 둡니다.
                    if w_bit:
                        self._last_request_context[device_id] = sent_system_bytes

                # --- 'Wait for Reply' 스텝 처리 ---
                elif 'wait_recv' in step:
                    # 3. 이전에 저장해 둔 요청의 system_bytes를 가져옵니다.
                    system_bytes_to_wait_for = self._last_request_context.get(device_id)
                    if system_bytes_to_wait_for is None:
                        error_msg = f"Scenario FAIL: Device '{device_id}' is waiting for a reply, but no prior request was made."
                        await self._status_callback("Orchestrator", error_msg, "red")
                        break
                    
                    match_criteria = step['wait_recv']
                    s, f, timeout = match_criteria.get('s'), match_criteria.get('f'), step.get('timeout', 10.0)

                    # 4. S/F 정보와 함께, 기다려야 할 정확한 system_bytes를 전달합니다.
                    result = await target_agent.wait_for_message(
                        s=s, 
                        f=f, 
                        timeout=timeout, 
                        reply_to_system_bytes=system_bytes_to_wait_for
                    )
                    if result is None:
                        error_msg = f"Scenario FAIL: Timed out waiting for reply to request (SB={system_bytes_to_wait_for}) from {device_id}"
                        await self._status_callback("Orchestrator", error_msg, "red")
                        break
                
                if (delay := step.get('delay', 0)) > 0:
                    await asyncio.sleep(delay)
        
        except asyncio.CancelledError:
            print("Scenario execution was cancelled.")
        finally:
            self.is_running = False
            await self._status_callback("Orchestrator", "Scenario Finished", "blue")

    def send_single_message(self, device_id: str, message: dict):
        agent = self._agents.get(device_id)
        if not agent:
            # ✅ [수정] 에이전트가 없을 경우를 대비한 로그 추가
            print(f"Error: Agent '{device_id}' not found for sending single message.")
            return

        # ✅ [핵심 수정] agent.send_message가 비동기 함수이므로,
        # asyncio.create_task를 사용하여 현재 실행 중인 이벤트 루프에서
        # 이 작업을 스케줄링(예약)해야 합니다.
        asyncio.create_task(agent.send_message(
            s=message.get('s', 0),
            f=message.get('f', 0),
            w_bit=message.get('w_bit', False),
            body=message.get('body')
        ))

    async def edit_device(self, old_device_id: str, new_device_id: str, config: dict) -> bool:
        """✅ [추가] 디바이스 설정을 수정합니다."""
        # 1. 기존 에이전트가 있으면 정지시킵니다.
        if old_device_id in self._agents:
            await self._agents[old_device_id].stop()
            del self._agents[old_device_id]
        
        # 2. 설정 딕셔너리를 업데이트합니다. ID가 변경되었을 수 있습니다.
        if old_device_id in self._device_configs:
            del self._device_configs[old_device_id]
        self._device_configs[new_device_id] = config
        
        # 3. 새로운 설정으로 에이전트를 다시 생성합니다.
        agent = DeviceAgent(
            device_id=new_device_id,
            host=config['host'],
            port=config['port'],
            connection_mode=config.get('connection_mode', 'Passive'),
            status_callback=self._status_callback,
            t3=config.get('t3', 10),
            t5=config.get('t5', 10),
            t6=config.get('t6', 5),
            t7=config.get('t7', 10)
        )
        self._agents[new_device_id] = agent
        
        # 4. 변경된 내용을 파일에 저장합니다.
        return self.save_device_configs()

    async def delete_device(self, device_id: str) -> bool:
        """✅ [추가] 디바이스를 삭제합니다."""
        if device_id in self._agents:
            await self._agents[device_id].stop()
            del self._agents[device_id]
        
        if device_id in self._device_configs:
            del self._device_configs[device_id]
            return self.save_device_configs()
            
        return False
