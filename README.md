SECS/GEM 시뮬레이터
본 프로젝트는 반도체 및 디스플레이 장비의 SECS/GEM 통신 프로토콜을 시뮬레이션하기 위한 다중 가상 장비 시뮬레이터입니다.
주요 기능
다중 가상 장비(Device Agent) 동시 운영시나리오 기반 자동 메시지 송수신
비주얼 시나리오 편집기를 통한 손쉬운 테스트 케이스 작성
실시간 메시지 로깅 및 상태 모니터링

기술 스택
언어: Python 3.10+
UI: PySide6
비동기 처리: asyncio, qasync

PYTEST
pytest --cov=secs_simulator
pytest --cov=secs_simulator --cov-report=html
