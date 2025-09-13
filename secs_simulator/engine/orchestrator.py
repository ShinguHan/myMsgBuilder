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
                    status_callback=self._status_callback
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
            status_callback=self._status_callback
        )
        self._agents[device_id] = agent
        return self.save_device_configs()

    def get_device_configs(self) -> Dict[str, Any]:
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
        try:
            for step in scenario_data.get('steps', []):
                if not self.is_running:
                    print("Scenario stopped by user.")
                    break

                device_id = step.get('device_id')
                target_agent = self._agents.get(device_id)

                if 'message' in step:
                    if not target_agent:
                        continue
                    message = step['message']
                    w_bit = message.get('w_bit', False)
                    sent_system_bytes = await target_agent.send_message(
                        s=message.get('s', 0),
                        f=message.get('f', 0),
                        w_bit=w_bit,
                        body=message.get('body')
                    )
                    if w_bit:
                        self._last_request_context[device_id] = sent_system_bytes

                elif 'wait_recv' in step:
                    if not target_agent:
                        continue
                    
                    system_bytes_to_wait_for = self._last_request_context.get(device_id)
                    if system_bytes_to_wait_for is None:
                        error_msg = f"Scenario FAIL: Device '{device_id}' is waiting for a reply..."
                        print(error_msg)
                        await self._status_callback("Orchestrator", error_msg, "red")
                        break
                    
                    match_criteria = step['wait_recv']
                    s, f, timeout = match_criteria.get('s'), match_criteria.get('f'), step.get('timeout', 10.0)

                    if s is not None and f is not None:
                        result = await target_agent.wait_for_message(s, f, timeout, system_bytes=system_bytes_to_wait_for)
                        if result is None:
                            error_msg = f"Scenario FAIL: Timed out waiting for S{s}F{f} from {device_id}"
                            print(error_msg)
                            await self._status_callback("Orchestrator", error_msg, "red")
                            break
                
                if (delay := step.get('delay', 0)) > 0:
                    await asyncio.sleep(delay)
        
        except asyncio.CancelledError:
            print("Scenario execution was cancelled.")
        finally:
            self.is_running = False
            print("Scenario finished.")
            await self._status_callback("Orchestrator", "Scenario Finished", "blue")

    def send_single_message(self, device_id: str, message: dict):
        agent = self._agents.get(device_id)
        if not agent:
            return

        asyncio.create_task(agent.send_message(
            s=message.get('s', 0),
            f=message.get('f', 0),
            w_bit=message.get('w_bit', False),
            body=message.get('body')
        ))
