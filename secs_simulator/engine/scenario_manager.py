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
            self._message_libraries_cache[device_type] = {}
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
            if device_type:
                all_libs[device_type] = self._load_message_library(device_type)
        return all_libs

    def get_device_type(self, device_id: str) -> str | None:
        """주어진 device_id에 해당하는 device_type을 반환합니다."""
        return self._device_types.get(device_id)

    def save_scenario(self, scenario_data: dict, file_path: str) -> bool:
        """시나리오 데이터를 JSON 파일로 저장합니다."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenario_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving scenario to {file_path}: {e}")
            return False

