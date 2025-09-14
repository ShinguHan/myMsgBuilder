# log_converter.py
import os
import json
import argparse
from log_importer import get_messages_from_log

def get_value_from_path(data: list, path: list):
    """
    SECS-II 메시지 Body(dict 리스트)와 경로(path)를 받아, 해당 경로의 값을 추출합니다.
    """
    current_level = data
    try:
        for key in path:
            if isinstance(current_level, list) and isinstance(key, int):
                current_level = current_level[key]
            elif isinstance(current_level, dict) and isinstance(key, str):
                current_level = current_level[key]
            else:
                return None # 경로 타입 불일치
        
        # 최종 값이 리스트일 경우 첫 번째 요소 반환 (예: U2, U4 등)
        if isinstance(current_level, list):
            return current_level[0] if current_level else None
        return current_level
    except (IndexError, TypeError, KeyError):
        return None

def generate_message_key_suffix(msg: dict, rules: list) -> str:
    """
    메시지 데이터와 규칙 목록을 받아, 규칙에 맞는 메시지 이름 접미사를 생성합니다.
    (예: '_CEID[251]', '_HC_START')
    """
    msg_s, msg_f = msg['s'], msg['f']
    body = msg.get('message', {}).get('body', [])
    
    for rule in rules:
        if rule['s'] == msg_s and rule['f'] == msg_f:
            value = get_value_from_path(body, rule.get('value_path', []))
            if value is not None:
                prefix = rule.get('name_prefix', '')
                # 값이 숫자일 경우와 문자열일 경우를 구분하여 포맷팅
                if isinstance(value, int):
                    return f"_{prefix}[{value}]"
                else:
                    return f"_{prefix}_{value}"
    return "" # 규칙에 맞는 메시지가 없으면 빈 문자열 반환

def generate_assets(log_file: str, profile_file: str, rules_file: str, output_dir: str, device_id: str):
    """
    로그 파일로부터 시나리오와 메시지 라이브러리를 생성합니다.
    """
    print(f"Starting asset generation from '{log_file}'...")
    
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            key_rules = json.load(f).get('rules', [])
        print(f"Successfully loaded {len(key_rules)} rules from '{rules_file}'.")
    except Exception as e:
        print(f"Warning: Could not load message key rules from '{rules_file}'. {e}")
        key_rules = []

    messages = get_messages_from_log(log_file, profile_file)
    
    if not messages:
        print("No SECS messages found or parsed. Aborting.")
        return

    scenario_steps = []
    message_library = {}
    last_timestamp = None

    for msg in messages:
        current_timestamp = msg.get("timestamp", 0)
        delay = 0.0
        if last_timestamp is not None and current_timestamp > last_timestamp:
            delay = round((current_timestamp - last_timestamp) / 1000.0, 3)
        last_timestamp = current_timestamp

        # ✅ [핵심 수정] 규칙 기반으로 메시지 키 접미사 생성
        msg_key_base = f"S{msg['s']}F{msg['f']}"
        suffix_from_rule = generate_message_key_suffix(msg, key_rules)
        msg_key_base += suffix_from_rule

        # W-Bit 값에 따라 최종 메시지 키 완성
        w_bit_suffix = "_Request" if msg["w_bit"] else "_Reply"
        msg_key = msg_key_base + w_bit_suffix

        step = {
            "device_id": device_id,
            "delay": delay,
            "message_id": msg_key,
            "message": msg["message"]
        }
        scenario_steps.append(step)
        
        if msg_key not in message_library:
            message_library[msg_key] = msg["message"]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    scenario_path = os.path.join(output_dir, "generated_scenario_with_rules.json")
    scenario_data = {"name": "GeneratedScenarioFromLog", "steps": scenario_steps}
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=4)
    print(f"✅ Scenario with rule-based keys saved to '{scenario_path}'")

    library_path = os.path.join(output_dir, f"Generated_{device_id}_Library_with_rules.json")
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(message_library, f, indent=4)
    print(f"✅ Message library with rule-based keys saved to '{library_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SECS simulator assets from log files.")
    parser.add_argument("logfile", help="Path to the log file to be analyzed.")
    parser.add_argument("--profile", default="profile.json", help="Path to the log parsing profile JSON file.")
    # ✅ [추가] 규칙 파일을 받을 수 있도록 인자 추가
    parser.add_argument("--rules", default="message_key_rules.json", help="Path to the message key generation rules JSON file.")
    parser.add_argument("--out", default="./generated_assets", help="Directory to save the generated files.")
    parser.add_argument("--device", default="MyDevice", help="Device ID to use in the scenario.")
    
    args = parser.parse_args()
    
    generate_assets(args.logfile, args.profile, args.rules, args.out, args.device)