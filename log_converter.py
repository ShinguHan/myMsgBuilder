# log_converter.py
import os
import sys
import json
import argparse
import re # 👈 정규표현식 모듈 임포트
from log_importer import get_messages_from_log

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_value_from_path(data: list, path: list):
    """SECS-II 메시지 Body에서 경로에 해당하는 값을 추출합니다."""
    current_level = data
    try:
        for key in path:
            if isinstance(current_level, list) and isinstance(key, int):
                current_level = current_level[key]
            elif isinstance(current_level, dict) and isinstance(key, str):
                current_level = current_level[key]
            else:
                return None
        
        if isinstance(current_level, list):
            return current_level[0] if current_level else None
        return current_level
    except (IndexError, TypeError, KeyError):
        return None

def generate_message_key_suffix(msg: dict, rules: list) -> str:
    """
    [핵심 수정] 메시지와 규칙을 기반으로, 값과 설명을 조합하여
    'S1F4_MDLN_CV01'과 같은 최종 메시지 이름을 생성합니다.
    """
    msg_s, msg_f = msg['s'], msg['f']
    body = msg.get('message', {}).get('body', [])
    ascii_data = msg.get('ascii_data', '')
    
    for rule in rules:
        if rule['s'] == msg_s and rule['f'] == msg_f:
            # 1. Body에서 값(ID) 추출
            value = get_value_from_path(body, rule.get('value_path', []))
            value_str = str(value) if value is not None else ""

            # 2. AsciiData에서 설명 추출
            desc_str = ""
            if 'desc_regex' in rule:
                match = re.search(rule['desc_regex'], ascii_data)
                if match and match.groups():
                    # 정규식의 첫 번째 그룹을 설명으로 사용하고, 공백을 '_'로 치환
                    desc_str = match.group(1).strip().replace(' ', '_')

            # 3. 값과 설명을 조합하여 최종 이름 생성
            prefix = rule.get('name_prefix', '')
            
            # 이건 나중에 좀 고민을 ..
            # if prefix and desc_str:
            #     return f"_{prefix}_{desc_str}"
            # elif prefix and value_str and desc_str:
            #     return f"_{prefix}[{value_str}]_{desc_str}"
            # elif prefix and value_str:
            #     return f"_{prefix}[{value_str}]"
            # elif desc_str:
            #     return f"_{desc_str}"

            if prefix and desc_str:
                return f"_{prefix}_{desc_str}"
            elif prefix:
                return f"_{prefix}"
            elif desc_str:
                return f"_{desc_str}"

    return ""

def generate_assets(log_file: str, profile_file: str, rules_file: str, output_dir: str, device_id: str):
    """로그 파일로부터 시나리오와 메시지 라이브러리를 생성합니다."""
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

        msg_key_base = f"S{msg['s']}F{msg['f']}"
        suffix_from_rule = generate_message_key_suffix(msg, key_rules)
        msg_key_base += suffix_from_rule

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

    scenario_path = os.path.join(output_dir, "generated_scenario_final.json")
    scenario_data = {"name": "GeneratedScenarioFromLog", "steps": scenario_steps}
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=4)
    print(f"✅ Scenario with descriptive keys saved to '{scenario_path}'")

    library_path = os.path.join(output_dir, f"Generated_{device_id}_Library_final.json")
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(message_library, f, indent=4)
    print(f"✅ Message library with descriptive keys saved to '{library_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SECS simulator assets from log files.")
    parser.add_argument("logfile", help="Path to the log file to be analyzed.")
    # parser.add_argument("--profile", default="profile.json", help="Path to the log parsing profile JSON file.")
    # parser.add_argument("--rules", default="message_key_rules.json", help="Path to the message key generation rules JSON file.")
    # --- 수정 후 ---
    parser.add_argument("--profile", default=resource_path("profile.json"), help="Path to the log parsing profile JSON file.")
    parser.add_argument("--rules", default=resource_path("message_key_rules.json"), help="Path to the message key generation rules JSON file.")
    
    parser.add_argument("--out", default="./generated_assets", help="Directory to save the generated files.")
    parser.add_argument("--device", default="MyDevice", help="Device ID to use in the scenario.")
    
    args = parser.parse_args()
    
    generate_assets(args.logfile, args.profile, args.rules, args.out, args.device)