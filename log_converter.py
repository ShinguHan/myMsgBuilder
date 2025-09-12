# log_converter.py
import os
import json
import argparse
from log_importer import get_messages_from_log

def generate_assets(log_file: str, profile_file: str, output_dir: str, device_id: str):
    """
    로그 파일로부터 시나리오와 메시지 라이브러리를 생성합니다.
    """
    print(f"Starting asset generation from '{log_file}'...")
    # 수정: get_messages_from_log에 프로필 파일 경로를 전달합니다.
    messages = get_messages_from_log(log_file, profile_file)
    
    if not messages:
        print("No SECS messages found or parsed. Aborting.")
        return

    scenario_steps = []
    message_library = {}
    pending_requests = {}

    for msg in messages:
        # W-Bit가 True인 메시지 (요청)
        if msg["w_bit"]:
            msg_key = f"S{msg['s']}F{msg['f']}_Request"
            step = {
                "device_id": device_id,
                "delay": 0.0,
                "message_id": msg_key,
                "message": msg["message"]
            }
            scenario_steps.append(step)
            pending_requests[msg["system_bytes"]] = msg
            
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

                msg_key = f"S{msg['s']}F{msg['f']}_Reply"
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