# log_converter.py
import os
import json
import argparse
from log_importer import get_messages_from_log

def get_ceid_from_body(body: list) -> str | None:
    """
    S6F11 메시지 Body 구조를 분석하여 CEID 값을 추출합니다.
    SECS-II 표준에 따라 S6F11의 Body는 L[ L[ DATAID, CEID, L[...]]] 구조를 가집니다.
    """
    try:
        # Body가 비어있지 않고, 첫 번째 아이템이 'L' 타입인지 확인
        if not body or body[0].get('type') != 'L':
            return None
        
        # 첫 번째 리스트('L')의 값(value)을 가져옴
        main_list = body[0].get('value', [])
        
        # CEID는 이 리스트의 두 번째 요소여야 함 (인덱스 1)
        if len(main_list) > 1:
            ceid_item = main_list[1]
            return str(ceid_item.get('value')) # 값을 문자열로 반환
            
    except (IndexError, TypeError, AttributeError):
        # 예상치 못한 구조일 경우 에러를 방지하고 None을 반환
        return None
    return None

def generate_assets(log_file: str, profile_file: str, output_dir: str, device_id: str):
    """
    로그 파일로부터 시나리오와 메시지 라이브러리를 생성합니다.
    """
    print(f"Starting asset generation from '{log_file}'...")
    messages = get_messages_from_log(log_file, profile_file)
    
    if not messages:
        print("No SECS messages found or parsed. Aborting.")
        return

    scenario_steps = []
    message_library = {}
    pending_requests = {}

    for msg in messages:
        # 🎯 [핵심 수정] S6F11 메시지를 위한 특별 처리 로직 추가
        is_s6f11 = msg['s'] == 6 and msg['f'] == 11
        
        msg_key_base = f"S{msg['s']}F{msg['f']}"
        
        if is_s6f11:
            ceid = get_ceid_from_body(msg.get('message', {}).get('body', []))
            if ceid:
                # CEID가 있으면 키에 추가합니다. 예: S6F11_CEID251
                msg_key_base += f"_CEID{ceid}"

        # W-Bit 값에 따라 최종 메시지 키를 완성합니다.
        suffix = "_Request" if msg["w_bit"] else "_Reply"
        msg_key = msg_key_base + suffix

        # W-Bit가 True인 메시지 (요청)
        if msg["w_bit"]:
            step = {
                "device_id": device_id,
                "delay": 0.0,
                "message_id": msg_key,
                "message": msg["message"]
            }
            scenario_steps.append(step)
            pending_requests[msg["system_bytes"]] = msg
            
            # 덮어쓰기 방지: 키가 존재하지 않을 때만 라이브러리에 추가
            if msg_key not in message_library:
                message_library[msg_key] = msg["message"]

        # W-Bit가 False인 메시지 (응답)
        else:
            if msg["system_bytes"] in pending_requests:
                request_msg = pending_requests.pop(msg["system_bytes"])
                wait_step = {
                    "device_id": device_id,
                    "wait_recv": {"s": msg["s"], "f": msg["f"]},
                    "timeout": 10.0
                }
                scenario_steps.append(wait_step)

                if msg_key not in message_library:
                    message_library[msg_key] = msg["message"]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 시나리오 저장
    scenario_path = os.path.join(output_dir, "generated_scenario.json")
    scenario_data = {"name": "GeneratedScenarioFromLog", "steps": scenario_steps}
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=4)
    print(f"✅ Scenario saved to '{scenario_path}'")

    # 라이브러리 저장
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