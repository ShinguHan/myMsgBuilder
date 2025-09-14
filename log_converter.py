# log_converter.py
import os
import json
import argparse
from log_importer import get_messages_from_log

def get_ceid_from_body(body: list) -> str | None:
    """S6F11 메시지 Body 구조를 분석하여 CEID 값을 추출합니다."""
    try:
        if not body or body[0].get('type') != 'L':
            return None
        
        main_list = body[0].get('value', [])
        
        if len(main_list) > 1:
            ceid_item = main_list[1]
            # ✅ [수정] CEID 값이 리스트 형태일 경우를 대비하여 값 추출 로직 강화
            value = ceid_item.get('value')
            if isinstance(value, list):
                return str(value[0]) if value else None
            return str(value)
            
    except (IndexError, TypeError, AttributeError):
        return None
    return None

def generate_assets(log_file: str, profile_file: str, output_dir: str, device_id: str):
    """로그 파일로부터 시나리오와 메시지 라이브러리를 생성합니다."""
    print(f"Starting asset generation from '{log_file}'...")
    messages = get_messages_from_log(log_file, profile_file)
    
    if not messages:
        print("No SECS messages found or parsed. Aborting.")
        return

    scenario_steps = []
    message_library = {}
    
    # ✅ [추가] 이전 메시지의 타임스탬프를 저장할 변수
    last_timestamp = None

    for msg in messages:
        # ✅ [추가] 현재 메시지와 이전 메시지의 시간 차이를 계산하여 delay 값을 결정
        current_timestamp = msg.get("timestamp", 0)
        delay = 0.0
        if last_timestamp is not None and current_timestamp > last_timestamp:
            # 밀리초(ms)를 초(s)로 변환하고 소수점 3자리까지 반올림
            delay = round((current_timestamp - last_timestamp) / 1000.0, 3)
        
        # 다음 계산을 위해 현재 타임스탬프를 저장
        last_timestamp = current_timestamp

        is_s6f11 = msg['s'] == 6 and msg['f'] == 11
        msg_key_base = f"S{msg['s']}F{msg['f']}"
        
        if is_s6f11:
            ceid = get_ceid_from_body(msg.get('message', {}).get('body', []))
            if ceid:
                msg_key_base += f"_CEID[{ceid}]"

        suffix = "_Request" if msg["w_bit"] else "_Reply"
        msg_key = msg_key_base + suffix

        # 요청/응답 쌍을 맞추는 대신, 모든 메시지를 순서대로 시나리오 스텝으로 생성
        step = {
            "device_id": device_id,
            "delay": delay, # ✅ [수정] 하드코딩된 0.0 대신 계산된 delay 값을 사용
            "message_id": msg_key,
            "message": msg["message"]
        }
        scenario_steps.append(step)
        
        if msg_key not in message_library:
            message_library[msg_key] = msg["message"]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    scenario_path = os.path.join(output_dir, "generated_scenario_with_delay.json")
    scenario_data = {"name": "GeneratedScenarioFromLog", "steps": scenario_steps}
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=4)
    print(f"✅ Scenario with realistic delays saved to '{scenario_path}'")

    library_path = os.path.join(output_dir, f"Generated_{device_id}_Library.json")
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(message_library, f, indent=4)
    print(f"✅ Message library saved to '{library_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SECS simulator assets from log files.")
    parser.add_argument("logfile", help="Path to the log file to be analyzed.")
    parser.add_argument("--profile", default="profile.json", help="Path to the log parsing profile JSON file.")
    parser.add_argument("--out", default="./generated_assets", help="Directory to save the generated files.")
    parser.add_argument("--device", default="MyDevice", help="Device ID to use in the scenario.")
    
    args = parser.parse_args()
    
    generate_assets(args.logfile, args.profile, args.out, args.device)