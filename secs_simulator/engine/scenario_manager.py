import json
from pathlib import Path
from typing import Dict, Any

class ScenarioManager:
    """
    시나리오 파일과 메시지 라이브러리를 로드하고,
    실행 가능한 형태로 가공하는 데이터 처리 전문가입니다.
    """

    def __init__(self, device_configs: Dict[str, Any], message_library_dir: str):
        self._device_configs = device_configs
        self._device_types = {dev_id: conf.get('type') for dev_id, conf in device_configs.items()}
        self._message_library_dir = Path(message_library_dir)
        self._message_libraries_cache: Dict[str, Any] = {}

    def get_message_body(self, device_type: str, message_id: str) -> dict | None:
        """
        특정 메시지 라이브러리에서 메시지 본문(dict)을 직접 가져옵니다.
        UI에서 드롭된 메시지의 상세 정보를 얻기 위해 사용됩니다.
        """
        library = self._load_message_library(device_type)
        return library.get(message_id)

    def _load_message_library(self, device_type: str) -> Dict[str, Any]:
        """장비 타입에 맞는 메시지 라이브러리를 로드하고 캐싱합니다."""
        if device_type in self._message_libraries_cache:
            return self._message_libraries_cache[device_type]

        library_path = self._message_library_dir / f"{device_type}.json"
        if not library_path.exists():
            print(f"Warning: Message library not found for type '{device_type}' at {library_path}")
            self._message_libraries_cache[device_type] = {} # 찾지 못해도 캐시에 기록
            return {}

        try:
            with library_path.open('r', encoding='utf-8') as f:
                library = json.load(f)
                self._message_libraries_cache[device_type] = library
                return library
        except Exception as e:
            print(f"Error loading message library {library_path}: {e}")
        
        self._message_libraries_cache[device_type] = {}
        return {}

    def get_all_message_libraries(self) -> Dict[str, Any]:
        """
        `devices.json`에 정의된 모든 장비 타입의 메시지 라이브러리를 로드하여 반환합니다.
        """
        all_libs = {}
        unique_device_types = set(self._device_types.values())
        
        for device_type in unique_device_types:
            if device_type: # device_type이 None이 아닌 경우
                all_libs[device_type] = self._load_message_library(device_type)
        return all_libs

    def prepare_scenario(self, master_scenario_path: str) -> Dict[str, Any] | None:
        """
        마스터 시나리오를 로드하고 message_id를 실제 메시지 객체로 교체합니다.
        """
        try:
            with open(master_scenario_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading master scenario {master_scenario_path}: {e}")
            return None

        hydrated_steps = []
        for step in scenario_data.get('steps', []):
            if 'message_id' not in step:
                hydrated_steps.append(step)
                continue

            device_id = step.get('device_id')
            message_id = step.get('message_id')
            
            device_type = self._device_types.get(device_id)
            if not device_type:
                print(f"Scenario Error: Device '{device_id}' not found in device configurations.")
                continue
            
            library = self._load_message_library(device_type)
            message_body = library.get(message_id)

            if not message_body:
                print(f"Scenario Error: Message '{message_id}' not found in '{device_type}' library.")
                continue

            hydrated_step = step.copy()
            del hydrated_step['message_id']
            hydrated_step['message'] = message_body
            hydrated_steps.append(hydrated_step)
        
        scenario_data['steps'] = hydrated_steps
        return scenario_data

