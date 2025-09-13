## 제 1장: HSMS 표준의 이해

### 1.1 HSMS란 무엇인가?

HSMS는 **H**igh-Speed SECS **M**essage **S**ervices의 약자로, 반도체 및 평판 디스플레이 제조 장비와 호스트(Host) 컴퓨터 간의 통신을 위해 정의된 표준 프로토콜입니다. SEMI (Semiconductor Equipment and Materials International)에 의해 **E37** 표준으로 지정되어 있습니다.

기존의 직렬 통신(RS-232C) 기반인 SECS-I (SEMI E4) 표준은 속도가 느리고 일대일 연결만 가능하다는 한계가 있었습니다. HSMS는 이러한 단점을 극복하기 위해 **TCP/IP 이더넷(Ethernet)** 기술을 기반으로 설계되었습니다. 🚀

- **주요 특징**:
    
    - **고속 통신**: TCP/IP를 사용하여 대용량 데이터를 빠르고 안정적으로 전송할 수 있습니다.
        
    - **다중 연결**: 하나의 호스트가 여러 장비와 동시에 통신하는 것이 가능합니다.
        
    - **표준 네트워크 기술**: 널리 사용되는 이더넷 기술을 기반으로 하므로 유연하고 확장성이 뛰어납니다.
        

HSMS는 SECS-II (SEMI E5) 메시지의 '전송 수단' 역할을 담당합니다. 즉, 장비와 호스트가 주고받는 실제 데이터 내용(예: "작업 시작", "데이터 보고")은 SECS-II 형식에 담겨 있고, HSMS는 이 메시지 꾸러미를 TCP/IP 네트워크를 통해 정확하게 배달하는 **우편 시스템**과 같습니다.

### 1.2 Active Role과 Passive Role의 핵심 개념

HSMS 통신에서는 연결을 맺는 과정에서 두 가지 명확한 역할이 존재합니다. 이는 통신을 누가 시작하고 누가 기다리는지에 따라 구분됩니다.

- **Active Role (능동적 주체)**
    
    - 일반적으로 **호스트(Host)** 또는 MES(Manufacturing Execution System)가 이 역할을 담당합니다.
        
    - 통신 연결을 **시작하고 요청하는(Initiator)** 쪽입니다.
        
    - 마치 전화를 거는 사람처럼, Passive Role을 가진 장비의 특정 IP 주소와 포트 번호로 접속을 시도합니다.
        
    - **"Client"**의 개념과 유사합니다.
        
- **Passive Role (수동적 객체)**
    
    - 일반적으로 **장비(Equipment)**가 이 역할을 담당합니다.
        
    - 자신의 IP 주소와 지정된 포트 번호를 열어두고, Active Role의 연결 요청을 **기다리는(Listener)** 쪽입니다.
        
    - 마치 전화를 받는 사람처럼, 외부의 연결 요청을 수신하고 수락하여 통신 세션을 시작합니다.
        
    - **"Server"**의 개념과 유사합니다.
        

이러한 역할 구분은 HSMS 통신의 시작점을 명확히 하여 안정적인 연결 관리의 기초가 됩니다.

[LAN Network Diagram Vector Illustrator. 이미지](https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcREWNB6MGdG2fSnvopkYModF3OG28Q-g8XeD_Z0LGSVLdkyRtkRUx7Cux8tzFFxdeYm3ouzEelxnh4AG6Mb5K9kKDUKFlVkjEaphjFU0XjddXolkQU)



---

## 제 2장: HSMS 상태 모델 (State Machine)

HSMS 통신은 명확하게 정의된 **상태(State)**들을 가지며, 특정 이벤트가 발생할 때마다 하나의 상태에서 다른 상태로 전환됩니다. 이 상태 모델을 이해하는 것은 통신 프로토콜의 동작을 정확히 파악하고 안정적인 소프트웨어를 구현하는 데 필수적입니다.

### 2.1 HSMS의 주요 상태

HSMS의 상태는 크게 **연결되지 않은 상태**와 **연결된 상태**로 나뉩니다.

- **`NOT_CONNECTED`**: TCP/IP 연결이 수립되지 않은 초기 상태 또는 연결이 끊어진 상태입니다.
    
- **`CONNECTED`**: TCP/IP 연결은 수립되었지만, 아직 HSMS 통신을 위한 세션은 확립되지 않은 상태입니다. 이 상태는 다시 두 개의 하위 상태로 나뉩니다.
    
    - **`NOT_SELECTED`**: TCP/IP 연결은 되었으나, 통신 주체(Active)가 자신을 식별하고 통신을 시작하겠다는 `Select.req` 요청을 보내기 전의 상태입니다.
        
    - **`SELECTED`**: Active Role이 보낸 `Select.req`를 Passive Role이 성공적으로 수신하고 응답하여, 양측 간에 데이터 메시지(SECS-II 메시지)를 교환할 준비가 완료된 상태입니다. 모든 데이터 통신은 이 `SELECTED` 상태에서만 이루어집니다.
        

### 2.2 [Passive Role] 상태 전이 모델

장비(Passive Role)는 연결 요청을 기다리는 입장이므로, 상태 변화는 주로 Active Role의 요청에 의해 발생합니다.


``` mermaid
stateDiagram-v2
    direction LR
    [*] --> NOT_CONNECTED
    NOT_CONNECTED --> CONNECTED: TCP 연결 요청 수락
    CONNECTED --> NOT_CONNECTED: TCP 연결 끊김

    state CONNECTED {
        direction LR
        [*] --> NOT_SELECTED
        NOT_SELECTED --> SELECTED: 유효한 Select.req 수신
        SELECTED --> NOT_SELECTED: Separate.req 수신
    }
```

- **`NOT_CONNECTED` -> `CONNECTED / NOT_SELECTED`**: Active 측(Host)에서 TCP/IP 연결 요청이 들어와 수락(Accept)하면 상태가 전환됩니다.
    
- **`NOT_SELECTED` -> `SELECTED`**: Active 측으로부터 유효한 `Select.req` 메시지를 수신하고, 성공 응답(`Select.rsp`)을 보내면 데이터 교환이 가능한 `SELECTED` 상태가 됩니다.
    
- **`SELECTED` -> `NOT_SELECTED`**: Active 측으로부터 연결 종료를 의미하는 `Separate.req` 메시지를 받으면 세션이 종료되고 `NOT_SELECTED` 상태로 돌아갑니다.
    
- **`CONNECTED` -> `NOT_CONNECTED`**: 어떤 이유로든(정상 종료, 네트워크 단절 등) TCP/IP 연결이 끊어지면 초기 상태인 `NOT_CONNECTED`로 돌아갑니다.
    

### 2.3 [Active Role] 상태 전이 모델

호스트(Active Role)는 연결을 주도하는 입장이므로, 자신의 요청과 상대방의 응답에 따라 상태가 변화합니다.


``` mermaid
stateDiagram-v2
    direction LR
    [*] --> NOT_CONNECTED
    NOT_CONNECTED --> CONNECTED: TCP 연결 성공
    CONNECTED --> NOT_CONNECTED: TCP 연결 끊김

    state CONNECTED {
        direction LR
        [*] --> NOT_SELECTED
        NOT_SELECTED --> SELECTED: Select.rsp(성공) 수신
        SELECTED --> NOT_SELECTED: Separate.req 전송
        NOT_SELECTED --> NOT_CONNECTED: T7 Timeout 발생
    }
```

- **`NOT_CONNECTED` -> `CONNECTED / NOT_SELECTED`**: Passive 측(장비)에 TCP/IP 연결을 시도(Connect)하여 성공하면 상태가 전환됩니다. 이후 즉시 `Select.req`를 전송하여 세션 수립을 시도합니다.
    
- **`NOT_SELECTED` -> `SELECTED`**: `Select.req` 전송 후, Passive 측으로부터 성공적인 응답(`Select.rsp`)을 받으면 데이터 교환이 가능한 `SELECTED` 상태가 됩니다.
    
- **`NOT_SELECTED` -> `NOT_CONNECTED`**: `Select.req`를 보냈으나 일정 시간(T7 Timeout) 내에 응답이 오지 않으면 연결에 문제가 있다고 판단하여 TCP/IP 연결을 끊고 `NOT_CONNECTED` 상태로 돌아갑니다.
    
- **`SELECTED` -> `NOT_SELECTED`**: 통신 종료를 위해 `Separate.req` 메시지를 전송하면 세션 종료를 시작하며, 이후 TCP/IP 연결을 끊게 됩니다.
    
- **`CONNECTED` -> `NOT_CONNECTED`**: TCP/IP 연결이 끊어지면 `NOT_CONNECTED` 상태로 돌아가며, 보통 정해진 로직에 따라 재연결을 시도합니다.
    

---

## 제 3장: [Passive Role] 통신 준비 및 연결 대기

Passive Role을 담당하는 장비는 Active Role(호스트)이 언제든지 접속할 수 있도록 통신 채널을 열고 대기 상태를 유지해야 합니다. 이 과정은 TCP/IP 소켓 프로그래밍의 서버(Server) 모델과 매우 유사합니다.

### 3.1 Passive 측의 통신 설정

가장 먼저, 장비는 통신을 위한 기본적인 네트워크 정보를 설정해야 합니다.

- **IP 주소**: 장비가 네트워크 상에서 식별될 수 있는 고유한 주소입니다. 이 주소는 고정 IP를 사용하는 것이 일반적입니다.
    
- **Port 번호**: 하나의 IP 주소 내에서 특정 통신 프로그램을 구분하기 위한 논리적인 번호입니다. HSMS 표준에서는 특별히 정해진 포트는 없으나, 일반적으로 **5000번 이상**의 포트가 관례적으로 사용됩니다. (예: 5000, 5001 등)
    

이 IP와 Port 정보는 Active Role(호스트)이 연결을 시도할 때 사용하는 목적지 주소가 됩니다.

### 3.2 소켓(Socket) 생성 및 연결 대기 과정

장비의 통신 프로그램은 다음의 절차를 통해 연결 대기 상태에 들어갑니다.

1. **소켓 생성 (Socket Creation)**
    
    - 통신을 위한 Endpoint, 즉 창구를 만드는 단계입니다. TCP/IP 통신을 위한 스트림(Stream) 타입의 소켓을 생성합니다.
        
2. **바인딩 (Binding)**
    
    - 생성된 소켓을 위에서 설정한 장비의 **IP 주소와 Port 번호에 할당**하는 과정입니다. "이 소켓은 `192.168.0.10`의 `5000`번 포트를 통해 들어오는 통신을 담당한다"라고 지정하는 것과 같습니다.
        
3. **리슨 (Listening)**
    
    - 바인딩된 소켓을 통해 외부(Active Role)로부터의 연결 요청을 받을 수 있도록 **대기 모드로 전환**합니다. 이 시점부터 장비는 호스트의 접속을 기다리게 됩니다.
        
    - 동시에 여러 연결 요청이 들어올 경우를 대비해 대기 큐(Queue)의 크기를 설정하기도 합니다.
        

### 3.3 연결 요청 수락 (Accept)

`Listen` 상태에서 호스트가 올바른 IP와 Port로 연결을 요청하면, 장비의 운영체제는 이를 감지합니다. 통신 프로그램은 `Accept` 함수를 호출하여 이 연결 요청을 수락합니다.

연결이 수락되면, **새로운 통신용 소켓**이 생성됩니다. 이 새로운 소켓을 통해 해당 호스트와의 실제 데이터 송수신이 이루어집니다. 기존에 `Listen`하던 소켓은 계속해서 다른 호스트의 연결 요청을 기다리는 역할을 수행합니다.

이로써 장비는 `NOT_CONNECTED` 상태에서 `CONNECTED / NOT_SELECTED` 상태로 전환되며, 호스트로부터 `Select.req` 메시지가 오기를 기다립니다.

### 3.4 주요 파라미터: T5 (Connection Separation Timeout)

- **T5 (Connection Separation Timeout)**
    
    - HSMS 메시지 송수신이 **전혀 없는 상태**가 T5에 설정된 시간만큼 지속되면, 장비는 통신 채널에 문제가 발생했다고 간주하고 스스로 TCP/IP 연결을 끊습니다.
        
    - 이는 비정상적으로 연결이 유지되는 "좀비 커넥션(Zombie Connection)"을 방지하고 시스템 자원을 보호하는 중요한 역할을 합니다.
        
    - 일반적으로 **10초** 내외로 설정됩니다.
        


---

## 제 4장: [Active Role] 연결 요청 및 세션 수립

Active Role을 담당하는 호스트는 통신의 시작을 책임집니다. 장비(Passive Role)가 열어놓은 통신 채널로 정확하게 접속을 시도하고, HSMS 세션을 공식적으로 수립하는 역할을 수행합니다.

### 4.1 Active 측의 통신 설정

호스트는 접속할 대상, 즉 장비의 네트워크 정보를 명확히 알고 있어야 합니다.

- **Target IP 주소**: 접속하고자 하는 장비의 고유 IP 주소입니다.
    
- **Target Port 번호**: 해당 장비가 HSMS 통신을 위해 열어놓은(Listen) 포트 번호입니다.
    

이 두 정보가 있어야만 호스트는 통신을 시작할 수 있습니다. 📞

### 4.2 소켓 생성 및 연결 시도

호스트의 통신 프로그램은 다음 절차에 따라 장비에 연결을 시도합니다.

1. **소켓 생성 (Socket Creation)**
    
    - 장비와 마찬가지로 TCP/IP 통신을 위한 소켓을 생성합니다.
        
2. **연결 시도 (Connect)**
    
    - 생성된 소켓을 사용하여 설정된 **Target IP와 Port로 접속을 시도**합니다. 이 `Connect` 과정이 바로 Active Role의 핵심 동작입니다.
        
    - **성공**: 장비가 해당 요청을 `Accept`하면 TCP/IP 연결이 성공적으로 수립되고, 호스트의 상태는 `NOT_CONNECTED`에서 `CONNECTED / NOT_SELECTED`로 전환됩니다.
        
    - **실패**: 장비가 꺼져 있거나, 네트워크 문제, 혹은 IP/Port 정보가 잘못된 경우 연결은 실패합니다. 이 경우, 호스트는 보통 일정 시간 간격을 두고 재연결을 시도하는 로직을 가집니다.
        

### 4.3 `Select.req` 전송과 세션 수립

TCP/IP 연결이 성공적으로 이루어졌다고 해서 바로 데이터(SECS-II 메시지)를 교환할 수 있는 것은 아닙니다. 호스트는 자신이 누구이며 통신할 준비가 되었음을 장비에게 공식적으로 알려야 합니다. 이 과정에서 `Select.req` 제어 메시지를 사용합니다.

- **`Select.req` 전송**: TCP/IP 연결이 수립되면, 호스트는 즉시 장비에게 `Select.req` 메시지를 전송합니다. 이 메시지는 "이제부터 당신과 HSMS 통신을 시작하겠습니다"라는 공식적인 요청입니다.
    
- **`Select.rsp` 수신**: `Select.req`를 받은 장비는 요청을 처리한 후 응답으로 `Select.rsp` 메시지를 보냅니다.
    
    - **성공 응답**: `Select.rsp`에 성공 코드가 포함되어 있으면, 비로소 양측은 `SELECTED` 상태로 진입합니다. 이제부터 실제 데이터 메시지를 교환할 수 있습니다.
        
    - **실패 응답**: 장비가 이미 다른 호스트와 통신 중이거나 다른 이유로 요청을 거절하면 실패 코드가 담긴 `Select.rsp`가 오게 되고, 호스트는 `SELECTED` 상태로 진입할 수 없습니다.
        

### 4.4 주요 파라미터: T7, T8

- **T7 (Not Selected Timeout)**
    
    - Active Role이 `Select.req`를 보낸 후 `Select.rsp` 응답을 기다리는 **최대 시간**입니다. 만약 이 시간 내에 응답이 도착하지 않으면, 호스트는 통신 세션 수립에 실패했다고 판단하고 TCP/IP 연결을 끊은 후 `NOT_CONNECTED` 상태로 돌아갑니다. 일반적으로 **10초** 내외로 설정됩니다.
        
- **T8 (Network Inter-character Timeout)**
    
    - 하나의 완전한 HSMS 메시지를 수신할 때, 메시지의 각 데이터 패킷(조각) 사이의 최대 지연 시간을 의미합니다. 만약 메시지 수신 중 이 시간을 초과하면 메시지가 비정상적으로 전송된 것으로 간주하고 해당 메시지를 폐기합니다. 네트워크 안정성을 확보하기 위한 파라미터입니다.
        

---

### ## 5.1 통신 연결 수립 절차 (Sequence)

정상적인 HSMS 통신 연결은 크게 **TCP/IP 연결 단계**와 **HSMS 세션 수립 단계**로 나뉩니다. 아래 다이어그램은 이 과정을 시간 순서에 따라 보여줍니다.



``` mermaid
sequenceDiagram
    participant Active Role (Host)
    participant Passive Role (Equipment)

    Note over Active Role (Host), Passive Role (Equipment): 초기 상태: NOT_CONNECTED

    Active Role (Host)->>Passive Role (Equipment): 1. TCP/IP 연결 요청 (Connect)
    Note right of Passive Role (Equipment): Listen 상태에서 요청 수신
    Passive Role (Equipment)-->>Active Role (Host): 2. TCP/IP 연결 수락 (Accept)

    Note over Active Role (Host), Passive Role (Equipment): 상태: CONNECTED / NOT_SELECTED

    Active Role (Host)->>Passive Role (Equipment): 3. HSMS 세션 요청 (Select.req)
    Passive Role (Equipment)-->>Active Role (Host): 4. HSMS 세션 응답 (Select.rsp)

    Note over Active Role (Host), Passive Role (Equipment): 상태: SELECTED (데이터 교환 가능)

    Active Role (Host)->>Passive Role (Equipment): Data Message (S1F13 등)
    Passive Role (Equipment)-->>Active Role (Host): Data Message (S1F14 등)
```

1. **TCP/IP 연결 요청**: **Active Role(Host)**이 **Passive Role(Equipment)**의 IP와 Port로 TCP/IP 연결을 시도합니다.
    
2. **TCP/IP 연결 수락**: **Passive Role**은 `Listen` 상태에서 이 요청을 받아들이고, 양측 간에 네트워크 경로가 열립니다. 이 시점부터 두 역할 모두 `CONNECTED / NOT_SELECTED` 상태가 됩니다.
    
3. **HSMS 세션 요청**: 연결이 수립되면 **Active Role**은 통신을 개시하겠다는 의미로 `Select.req` 메시지를 보냅니다.
    
4. **HSMS 세션 응답**: **Passive Role**은 이 요청이 유효한지 확인하고 `Select.rsp`로 응답합니다. 성공 응답을 보내면, 양측 모두 데이터를 주고받을 수 있는 최종 단계인 **`SELECTED` 상태**로 전환됩니다.
    

---

### ## 5.2 정상적인 통신 해제 절차

통신을 정상적으로 종료할 때는 `Separate.req` 제어 메시지가 사용됩니다. 이는 "이제 통신을 마치겠습니다"라는 신호와 같습니다.

- 일반적으로 **Active Role**이 `Separate.req` 메시지를 **Passive Role**에게 보냅니다.
    
- `Separate.req`를 받은 **Passive Role**은 `SELECTED` 상태에서 `NOT_SELECTED` 상태로 돌아갑니다.
    
- 이후, 통신을 시작했던 **Active Role**이 최종적으로 TCP/IP 연결을 끊습니다(Disconnect).
    

이러한 절차는 양측이 통신 종료를 명확하게 인지하고 자원을 안전하게 해제할 수 있도록 보장합니다.

---

### ## 5.3 비정상적인 연결 해제

네트워크 케이블이 뽑히거나, 장비/호스트의 전원이 갑자기 꺼지는 등 예기치 못한 상황으로 TCP/IP 연결이 끊어질 수 있습니다.

- 이 경우, `Separate.req`와 같은 정상적인 절차 없이 연결이 단절됩니다.
    
- 운영체제(OS)의 소켓 시스템은 이 단절을 감지하고, 통신 프로그램은 `NOT_CONNECTED` 상태로 즉시 복귀합니다.
    
- **Active Role**은 보통 이런 비정상적인 단절을 감지하면, 잠시 후 다시 연결을 시도하는 재연결 로직을 수행합니다. (이는 9장에서 자세히 다룹니다.)
    
네, 바로 **제 6장 '데이터 메시지 교환'**으로 넘어가겠습니다. `SELECTED` 상태가 된 후 실제로 어떻게 데이터를 주고받는지 알아보겠습니다.

---

## 제 6장: 데이터 메시지 교환

`SELECTED` 상태는 호스트와 장비가 SECS-II 메시지를 자유롭게 교환할 수 있는 단계입니다. HSMS는 이 SECS-II 메시지를 안정적으로 전달하는 역할을 합니다.

### 6.1 HSMS 메시지 구조

HSMS를 통해 전송되는 모든 메시지는 **헤더(Header)**와 **바디(Body)** 두 부분으로 구성됩니다.

- **Header (10 bytes)**: 메시지의 종류, 길이, 그리고 가장 중요한 **'시스템 바이트(System Bytes)'**와 같은 제어 정보를 담고 있습니다. 헤더는 항상 10바이트의 고정된 크기를 가집니다.
    
- **Body (Variable length)**: 실제 주고받고자 하는 내용, 즉 **SECS-II 메시지**가 이 부분에 담깁니다. 메시지의 내용에 따라 크기가 달라질 수 있습니다.
    

마치 편지 봉투(Header)에 편지지(Body)를 넣어 보내는 것과 같습니다. 수신자는 봉투를 보고 누가 보냈고 어떤 종류의 편지인지 파악한 후, 안의 편지지를 읽게 됩니다.

---

### 6.2 [Active] 메시지 송신과 T3 타이머

Active Role(호스트)이 장비에게 데이터를 요청하거나 명령을 내리는 메시지를 보낼 때, 대부분 응답을 기대합니다.

- **메시지 전송**: 호스트는 장비에게 요청 메시지(예: `S1F13`, 통신 수립 요청)를 보냅니다. 이때, 이 요청을 식별하기 위한 고유한 **시스템 바이트(System Bytes)** 값을 헤더에 포함시킵니다.
    
- **T3 타이머 시작**: 응답이 필요한 메시지를 보낸 직후, 호스트는 **T3 (Reply Timeout)** 타이머를 작동시킵니다. 이는 "이 시간 안에 응답이 오지 않으면 문제가 있는 것이다"라고 판단하는 기준 시간입니다.
    
- **응답 수신**: T3 타이머가 만료되기 전에 장비로부터 응답 메시지(예: `S1F14`)가 도착하면, 호스트는 헤더의 시스템 바이트 값을 확인하여 어떤 요청에 대한 응답인지 파악하고 트랜잭션을 성공적으로 마칩니다.
    

---

### 6.3 [Passive] 메시지 수신과 응답

Passive Role(장비)은 호스트로부터 메시지를 수신하고 그에 맞게 동작합니다.

- **메시지 수신**: 호스트로부터 메시지를 받으면, 먼저 헤더를 분석하여 메시지의 종류와 길이를 파악하고, Body에 담긴 SECS-II 메시지를 해석합니다.
    
- **요청 처리**: 수신한 메시지의 내용에 따라 장비는 특정 동작을 수행합니다. (예: 데이터 수집, 상태 변경 등)
    
- **응답 생성**: 응답이 필요한 메시지였다면, 장비는 처리 결과를 담은 응답 SECS-II 메시지를 생성합니다. 이때 **가장 중요한 규칙**은, 응답 메시지 헤더의 **시스템 바이트** 값을 수신했던 요청 메시지의 시스템 바이트 값과 **반드시 동일하게** 설정해야 한다는 것입니다.
    

---

### 6.4 시스템 바이트(System Bytes)와 트랜잭션

**시스템 바이트**는 HSMS 통신에서 **트랜잭션(Transaction)을 식별하는 핵심적인 역할**을 합니다. 🤝

호스트는 동시에 여러 요청을 보낼 수 있습니다. 예를 들어, "현재 상태 알려줘"(`S1F3`)라는 요청과 "A 레시피 정보 줘"(`S7F5`)라는 요청을 거의 동시에 보냈다고 가정해 봅시다. 잠시 후 장비로부터 `S1F4`와 `S7F6`라는 두 개의 응답이 도착했을 때, 호스트는 어떤 응답이 어떤 요청에 대한 것인지 구분해야 합니다.

이때 사용되는 것이 바로 **시스템 바이트**입니다. 호스트는 각 요청에 고유한 시스템 바이트(예: `0x0001`, `0x0002`)를 부여하고, 장비는 응답 시 해당 시스템 바이트를 그대로 돌려주기 때문에 호스트는 요청과 응답을 정확하게 짝지을 수 있습니다.


---

## 제 7장: 통신 채널 상태 관리 (Health Check)

`SELECTED` 상태에서 한동안 데이터 교환이 없는 경우, 호스트와 장비는 서로의 연결이 아직 유효한지 궁금해할 수 있습니다. 네트워크 케이블이 물리적으로 뽑혔지만 TCP/IP 세션은 아직 살아있는 것처럼 보이는 애매한 상황도 발생할 수 있습니다. 🔌

이럴 때 사용하는 것이 바로 **`Linktest`**입니다. `Linktest`는 주기적으로 "거기 잘 있나요?"라고 물어보며 통신 채널의 건강 상태를 확인하는 절차입니다.

### 7.1 `Linktest.req` / `Linktest.rsp`의 목적

- **`Linktest.req` (요청)**: "이 메시지를 받으면 즉시 응답해 주세요"라는 의미를 가진 제어 메시지입니다.
    
- **`Linktest.rsp` (응답)**: `Linktest.req`를 받은 쪽이 "네, 잘 받았습니다. 통신에 문제없습니다"라고 회신하는 제어 메시지입니다.
    

이 간단한 요청과 응답 절차를 통해, 양측은 통신 경로에 문제가 없는지, 그리고 상대방의 HSMS 애플리케이션이 정상적으로 동작하고 있는지 확인할 수 있습니다.

### 7.2 [Active] 관점에서의 Health Check

일반적으로 **Health Check의 주체는 Active Role(호스트)**입니다. 호스트는 통신 세션이 유휴(Idle) 상태일 때 주기적으로 `Linktest`를 수행합니다.

1. **타이머 기반 전송**: 호스트는 마지막으로 메시지를 주고받은 시점부터 특정 시간(보통 **T6 Timeout**의 절반 정도)이 지나면 `Linktest.req`를 장비로 전송합니다.
    
2. **응답 대기**: `Linktest.req`를 보낸 후, 호스트는 **T6 (Control Transaction Timeout)** 타이머를 작동시켜 응답을 기다립니다.
    
3. **응답 확인**: T6 시간 내에 `Linktest.rsp`가 도착하면, 호스트는 통신 채널이 정상이라고 판단하고 다음 주기를 기다립니다.
    
4. **실패 처리**: 만약 T6 시간 내에 응답이 오지 않으면, 호스트는 통신 채널에 심각한 문제가 발생했다고 간주하고 **스스로 TCP/IP 연결을 끊습니다.** 그 후, 정해진 재연결 로직에 따라 다시 연결을 시도하게 됩니다.
    

### 7.3 [Passive] 관점에서의 Health Check

Passive Role(장비)은 Health Check를 주도하지 않고, Active Role의 요청에 응답하는 역할을 합니다.

1. **`Linktest.req` 수신**: 호스트로부터 `Linktest.req` 메시지를 받습니다.
    
2. **즉시 응답**: 수신 즉시, 별다른 처리 없이 `Linktest.rsp` 메시지를 생성하여 호스트에게 보냅니다.
    

장비 입장에서 `Linktest`는 매우 간단한 동작이지만, 이를 통해 자신이 통신 가능한 상태임을 호스트에게 알려주는 중요한 역할을 합니다.

---

## 제 8장: [Passive Role] 주요 예외 처리 가이드

Passive Role인 장비는 언제나 안정적으로 동작하며 비정상적인 요청이나 상황에도 시스템이 중단되지 않도록 견고하게 설계되어야 합니다. 다음은 장비가 겪을 수 있는 주요 예외 상황과 권장되는 처리 방법입니다.

---

### 8.1 상황: `Select.req`가 오지 않는 경우

상황

호스트(Active Role)가 TCP/IP 연결(Connect)에는 성공했지만, 그 이후 아무런 메시지도 보내지 않고, 특히 HSMS 세션을 시작하기 위한 Select.req 메시지를 보내지 않는 경우입니다.

문제점

장비는 이 연결이 유효한지, 아니면 그냥 연결만 된 채로 방치된 '유령' 연결인지 알 수 없습니다. 이런 연결을 무한정 유지하면 시스템 자원(소켓, 메모리 등)이 낭비됩니다.

**권장 조치**

- **자체 타임아웃 설정**: TCP/IP 연결이 수락된 (`Accept`) 후, `NOT_SELECTED` 상태에서 일정 시간(예: 호스트의 T7과 유사하게 10~15초) 내에 `Select.req`가 도착하지 않으면, 장비는 **스스로 해당 TCP/IP 연결을 끊어야 합니다.**
    
- **상태 복귀**: 연결을 끊은 후, 다시 다른 호스트의 연결 요청을 받을 수 있도록 `Listen` 상태로 돌아갑니다.
    

---

### 8.2 상황: `SELECTED` 상태에서 다른 `Select.req` 수신

상황

이미 특정 호스트와 성공적으로 SELECTED 상태에 진입하여 통신 중인데, 동일한 연결을 통해 또 다른 Select.req가 오거나 혹은 다른 호스트가 새로운 연결을 맺고 Select.req를 보내는 경우입니다.

문제점

이는 명백한 프로토콜 위반입니다. 장비는 한 번에 하나의 제어 호스트와 통신 세션을 유지하는 것이 일반적입니다. 이 요청을 수락하면 기존 통신이 엉망이 될 수 있습니다.

**권장 조치**

- **요청 거절**: 새로운 `Select.req` 요청에 대해 "이미 `SELECTED` 상태임"을 의미하는 **실패 코드**를 담아 `Select.rsp`를 보냅니다.
    
- **기존 세션 유지**: 기존에 연결되어 있던 호스트와의 `SELECTED` 상태는 그대로 **유지해야 합니다.**
    

---

### 8.3 상황: 통신 중 TCP/IP 연결이 갑자기 끊어지는 경우

상황

Separate.req와 같은 정상적인 종료 절차 없이, 네트워크 장애나 호스트의 비정상 종료로 인해 TCP/IP 연결이 예고 없이 끊어지는 경우입니다.

문제점

장비는 호스트와의 통신이 불가능해졌음을 인지하고, 관련 자원을 정리한 후 새로운 연결을 맞이할 준비를 해야 합니다.

**권장 조치**

- **상태 전환**: 운영체제로부터 연결 종료를 감지하는 즉시, 상태를 `NOT_CONNECTED`로 변경합니다.
    
- **자원 해제**: 해당 통신에 사용되던 소켓과 메모리 등의 자원을 깨끗하게 해제합니다.
    
- **로그 기록**: 언제, 어떤 호스트와의 연결이 비정상적으로 종료되었는지 로그를 남겨 문제 추적을 용이하게 합니다.
    

---

### 8.4 상황: 잘못된 형식의 HSMS 메시지를 수신한 경우

상황

수신한 메시지의 헤더 정보가 표준과 맞지 않거나(예: 길이가 10바이트가 아님), 헤더에 명시된 메시지 길이와 실제 수신한 데이터의 길이가 다른 경우입니다.

문제점

잘못된 메시지를 처리하려고 시도하면 프로그램에 오류가 발생하거나 시스템이 멈출 수 있습니다. 🐛

**권장 조치**

- **메시지 폐기**: 해당 메시지는 처리하지 않고 즉시 폐기합니다.
    
- **오류 로그 기록**: 어떤 호스트로부터 어떤 종류의 잘못된 메시지가 수신되었는지 상세한 로그를 남깁니다.
    
- **응답하지 않음**: 일반적으로 이런 경우 응답 메시지를 보내지 않습니다. 응답을 보내는 것 자체가 또 다른 문제를 야기할 수 있기 때문입니다.
    

## 제 9장: [Active Role] 주요 예외 처리 가이드

Active Role인 호스트는 통신의 시작과 유지를 책임지기 때문에, 다양한 실패 상황에 대비한 **재시도(Retry)** 및 **오류 처리(Error Handling)** 로직을 갖추는 것이 매우 중요합니다.

---

### 9.1 상황: `Connect` 실패 시 재시도 전략

상황

장비의 IP/Port로 TCP/IP 연결(Connect)을 시도했으나 실패하는 경우입니다. 원인은 장비의 전원이 꺼져 있거나, 네트워크 문제, 설정 오류 등 다양합니다.

문제점

한 번의 실패로 통신을 포기하면 장비가 정상 상태가 되어도 영구히 통신이 단절됩니다. 호스트는 장비가 다시 온라인 상태가 되었을 때 자동으로 통신을 복구할 수 있어야 합니다.

**권장 조치**

- **주기적인 재연결 (Reconnection)**: `Connect` 실패 시, 즉시 다시 시도하지 않고 **일정 시간(예: 5~10초)을 대기**한 후 재시도하는 로직을 구현합니다.
    
- **재시도 횟수 및 로깅**: 무한정 재시도하기보다는, 특정 횟수나 시간 동안 실패가 지속되면 운영자에게 알림(Alarm)을 보내고, 모든 연결 시도와 실패 기록을 로그로 남겨 원인 분석을 용이하게 합니다.
    

---

### 9.2 상황: `Select.rsp` 응답이 없거나(T7) 실패 코드를 받은 경우

상황

Connect에는 성공하고 Select.req까지 보냈지만, 장비로부터 Select.rsp 응답이 T7 Timeout 내에 오지 않거나, "이미 사용 중"과 같은 실패 코드가 담긴 응답을 받은 경우입니다.

문제점

응답이 없는 것은 장비의 HSMS 애플리케이션이 멈췄거나 통신 경로에 문제가 생겼을 가능성을 의미합니다. 실패 코드를 받은 것은 장비가 현재 통신할 준비가 되지 않았다는 명확한 신호입니다.

**권장 조치**

- **T7 Timeout 발생 시**: 통신 세션 수립에 실패한 것으로 간주하고, 즉시 **TCP/IP 연결을 끊습니다.** 그 후, 위의 9.1에서 설명한 재연결 로직에 따라 처음부터 다시 연결을 시도합니다.
    
- **실패 응답 수신 시**: 마찬가지로 TCP/IP 연결을 끊고, 재연결 로직으로 전환합니다. 이때, 장비가 보낸 실패 사유를 로그에 상세히 기록하여 왜 세션 수립에 실패했는지 명확히 남기는 것이 중요합니다.
    

---

### 9.3 상황: 메시지 전송 후 `Reply`가 없는 경우 (T3)

상황

SELECTED 상태에서 장비에게 응답이 필요한 데이터 메시지(예: S1F3)를 보냈으나, T3 (Reply Timeout) 시간 내에 해당 응답(예: S1F4)이 오지 않는 경우입니다.

문제점

이는 장비가 해당 요청을 처리하는 데 문제가 생겼거나, 응답 메시지가 네트워크 중간에 유실되었을 가능성을 시사합니다. 이 트랜잭션은 실패한 것으로 간주해야 합니다.

**권장 조치**

- **트랜잭션 실패 처리**: 해당 요청-응답 트랜잭션은 실패했음을 명확히 하고, 관련 처리(예: 사용자에게 알림, 재시도 준비)를 수행합니다.
    
- **재시도 카운트 관리**: 동일한 메시지를 무한정 재전송하면 장비에 부하를 줄 수 있습니다. 보통 **2~3회 재시도** 후에도 계속 실패하면, 통신 채널 자체에 문제가 있다고 판단하는 것이 좋습니다.
    
- **통신 채널 리셋**: 반복적인 T3 Timeout은 통신 채널의 불안정성을 의미할 수 있습니다. 이 경우, 호스트는 현재 TCP/IP 연결을 강제로 끊고, 재연결 로직에 따라 통신을 처음부터 다시 시작하여 채널을 '리셋'하는 것이 안정적입니다.
    

---

### 9.4 상황: 통신 중 TCP/IP 연결이 갑자기 끊어지는 경우

상황

Linktest 실패나 네트워크 장애 등으로 인해 SELECTED 상태에서 갑자기 TCP/IP 연결이 끊어지는 경우입니다.

문제점

호스트는 통신이 불가능해졌음을 인지하고, 신속하게 복구를 시도해야 합니다.

**권장 조치**

- **상태 전환**: 연결 단절을 감지하는 즉시 상태를 `NOT_CONNECTED`로 변경합니다.
    
- **재연결 로직 실행**: 즉시 9.1의 재연결 로직을 가동하여 통신 복구를 시도합니다. 연결이 끊긴 원인(예: Linktest T6 timeout)을 로그에 명확히 기록합니다.
    

## 제 10장: 부록: Best Practice 및 요약

이 장에서는 지금까지 다룬 내용을 바탕으로 Active와 Passive의 역할을 한눈에 비교하고, 안정적인 HSMS 통신 프로그램을 개발하기 위한 실용적인 권장 사항들을 정리합니다.

### 10.1 Active vs. Passive 역할별 책임 요약

|구분|Active Role (Host)|Passive Role (Equipment)|
|---|---|---|
|**주요 역할**|통신 **요청** 및 **주도** (Client)|통신 **대기** 및 **응답** (Server)|
|**연결**|`Connect`를 통해 연결 **시도**|`Listen`으로 대기하다 `Accept`로 **수락**|
|**세션 수립**|`Select.req`를 **전송**하여 세션 시작|`Select.req`를 **수신**하고 `Select.rsp`로 응답|
|**데이터 교환**|요청 메시지 전송 후 **T3 타이머** 관리|요청 메시지 수신 후 처리 및 응답|
|**상태 확인**|주기적으로 `Linktest.req`를 **전송**|`Linktest.req` 수신 시 `Linktest.rsp`로 **응답**|
|**연결 해제**|`Separate.req`를 보내고 연결을 **끊음**|`Separate.req` 수신 후 세션을 **종료**|
|**예외 처리**|연결 실패 시 **재연결** 시도|비정상 요청 **거부** 및 자원 해제|

---

### 10.2 안정적인 HSMS 구현을 위한 권장 사항 (Best Practices)

1. **상세한 로깅 (Detailed Logging) ✍️**
    
    - **모든 것을 기록하세요**: 상태 변경, 주고받는 모든 메시지(헤더 정보 포함), 타임아웃 발생, 연결/해제 이벤트 등 주요 동작은 반드시 로그로 남겨야 합니다. 문제 발생 시 로그는 원인을 찾을 수 있는 유일한 단서입니다.
        
2. **설정의 외부화 (External Configuration)**
    
    - **하드코딩은 피하세요**: IP 주소, Port 번호, T3/T5/T6/T7과 같은 타임아웃 값들을 소스 코드에 직접 작성하지 마세요. 별도의 설정 파일(예: `config.ini`, `settings.xml`)로 분리하면, 프로그램을 다시 컴파일하지 않고도 설정을 쉽게 변경할 수 있어 유지보수가 매우 편리해집니다.
        
3. **명확한 상태 관리 (Clear State Management)**
    
    - **상태 기계를 따르세요**: 2장에서 다룬 상태 모델(`NOT_CONNECTED`, `SELECTED` 등)을 코드에 명확하게 구현해야 합니다. 현재 상태에 따라 허용되는 동작과 그렇지 않은 동작을 명확히 구분하면, 예기치 않은 오류를 크게 줄일 수 있습니다.
        
4. **견고한 재연결 로직 (Robust Reconnection Logic)**
    
    - **Active Role의 필수 덕목입니다**: 호스트는 통신이 끊어졌을 때, 영원히 기다리는 것이 아니라 스스로 복구할 수 있어야 합니다. 연결 실패 시 무작정 바로 재시도하기보다는, 점차 대기 시간을 늘려가는 방식(Exponential Backoff) 등을 도입하여 네트워크 부하를 줄이는 것이 좋습니다.
        

---

### 10.3 자주 발생하는 문제와 해결 방안 (FAQ)

- **Q: 연결이 자꾸 끊어져요.**
    
    - **A:** 먼저 `Linktest`가 양측에 올바르게 구현되었는지 확인하세요. 호스트가 주기적으로 `Linktest.req`를 보내고 장비가 `Linktest.rsp`로 잘 응답하는지 로그를 통해 점검해야 합니다. 또한, 네트워크 장비(스위치, 방화벽)가 장시간 유휴(Idle) 상태인 TCP 연결을 강제로 끊는 설정이 있는지도 확인해 볼 필요가 있습니다.
        
- **Q: 메시지를 보냈는데 응답이 없습니다 (T3 Timeout).**
    
    - **A:** 첫째, 장비가 해당 메시지를 처리하는 데 시간이 오래 걸리는 것은 아닌지 확인하세요. 둘째, 보낸 메시지의 SECS-II Body 형식이 표준에 맞는지 검토해야 합니다. 형식이 잘못되면 장비가 메시지를 해석하지 못해 응답을 못 보낼 수 있습니다.
        
- **Q: `Connect`는 되는데 `SELECTED` 상태가 안돼요.**
    
    - **A:** 호스트가 `Select.req`를 보낸 후 T7 Timeout이 발생하는지 확인하세요. 만약 그렇다면, 장비의 HSMS 애플리케이션이 정상적으로 동작하지 않거나 방화벽이 특정 HSMS 메시지를 차단하고 있을 수 있습니다. 장비로부터 "Already Selected"와 같은 실패 응답이 온다면, 이미 다른 호스트가 장비에 연결되어 있는지 확인해야 합니다.

---

### HSMS 주요 타임아웃 (Timeout) 요약

| 타임아웃   | 명칭 (Name)                       | 의미                                                       | 역할                                     | 관리 주체 (주로)              |
| ------ | ------------------------------- | -------------------------------------------------------- | -------------------------------------- | ----------------------- |
| **T3** | Reply Timeout                   | 요청 메시지를 보낸 후 **응답 메시지를 기다리는 최대 시간**                      | 개별 트랜잭션의 성공/실패를 판단 (예: S1F13 → S1F14)  | **메시지 송신 측** (Sender)   |
| **T5** | Connection Separation Timeout   | 아무런 HSMS 메시지 교환이 없을 때 **연결을 유지하는 최대 시간**                 | 유령/좀비 연결을 방지하고 비정상 세션을 스스로 끊는 역할       | **메시지 수신 측** (Receiver) |
| **T6** | Control Transaction Timeout     | `Linktest.req`와 같은 제어 메시지를 보낸 후 **응답을 기다리는 최대 시간**       | 통신 채널의 물리적/논리적 연결 상태(Health Check)를 판단 | **Active Role** (Host)  |
| **T7** | Not Selected Timeout            | TCP 연결 후, `Select.req`를 보내고 **`Select.rsp`를 기다리는 최대 시간** | HSMS 세션 수립의 성공/실패를 판단                  | **Active Role** (Host)  |
| **T8** | Network Inter-character Timeout | 하나의 완전한 HSMS 메시지를 구성하는 **데이터 조각(패킷) 사이의 최대 지연 시간**       | 불완전하거나 손상된 메시지의 수신을 방지하여 통신 안정성 확보     | **메시지 수신 측** (Receiver) |
## 주요 SECS-II 메시지 요약

SECS-II 메시지는 **Stream(S)**과 **Function(F)**의 조합으로 구성되며, 기능별로 그룹화되어 있습니다. 다음은 반도체 및 디스플레이 장비 통신에서 가장 일반적으로 사용되는 핵심 메시지들을 표로 정리한 것입니다.

---

### **S1: Equipment Status (장비 상태)**

장비의 상태를 질의하고 확인하는 기본적인 통신 채널 검증에 사용됩니다.

|메시지 (SxFy)|이름|역할 및 기능|
|---|---|---|
|**S1F1 (R)**|Are You There Request|호스트가 장비의 온라인 여부를 확인하기 위해 보내는 요청입니다. 📡|
|**S1F2 (S)**|On-Line Data|S1F1 요청에 대한 장비의 응답으로, 온라인 상태임을 알립니다.|
|**S1F13 (R)**|Establish Communications Request|호스트가 장비와 통신을 시작하겠다고 공식적으로 요청합니다. 🤝|
|**S1F14 (S)**|Establish Communications Acknowledge|S1F13 요청에 대한 응답으로, 통신 수락 여부를 회신합니다.|

---

### **S2: Equipment Control & Diagnostics (장비 제어 및 진단)**

호스트가 장비에 원격으로 명령을 보내거나 특정 정보를 요청할 때 사용됩니다.

|메시지 (SxFy)|이름|역할 및 기능|
|---|---|---|
|**S2F13 (R)**|Equipment Constant Request|장비가 가지고 있는 설정값(ECID)을 요청합니다.|
|**S2F15 (R)**|New Equipment Constant Send|장비의 설정값(ECID)을 원격으로 변경합니다.|
|**S2F31 (R)**|Date and Time Set Request|장비의 시스템 시간을 설정하도록 요청합니다. 🕒|
|**S2F41 (R)**|Remote Command Send|`START`, `STOP`, `PAUSE` 등 장비에 원격 명령을 보냅니다. 🕹️|
|**S2F42 (S)**|Remote Command Acknowledge|S2F41 명령에 대한 수신 응답으로, 명령의 유효성을 알립니다.|

---

### **S5: Exception & Alarm Reporting (예외 및 알람 보고)**

장비에서 발생한 알람이나 비정상 상황을 호스트에 보고할 때 사용됩니다.

|메시지 (SxFy)|이름|역할 및 기능|
|---|---|---|
|**S5F1 (S)**|Alarm Report Send|장비에 알람이 발생하거나 해제될 때 호스트로 그 내용을 보고합니다. 🚨|
|**S5F2 (R)**|Alarm Report Acknowledge|S5F1 보고에 대한 수신 응답입니다.|
|**S5F3 (R)**|Enable/Disable Alarm Send|호스트가 특정 알람의 보고 여부를 설정합니다.|

---

### **S6: Data Collection Reporting (데이터 수집 보고)**

장비에서 발생하는 각종 이벤트나 주기적인 데이터를 호스트로 보고하는 핵심 기능입니다.

|메시지 (SxFy)|이름|역할 및 기능|
|---|---|---|
|**S6F11 (S)**|Event Report Send|공정 시작/종료, 상태 변경 등 장비에서 특정 이벤트(CEID)가 발생했을 때 관련 데이터(DV, SV)를 묶어 호스트로 보고합니다. 📈|
|**S6F12 (R)**|Event Report Acknowledge|S6F11 보고에 대한 수신 응답입니다.|
|**S6F1 (S)**|Trace Data Send|1초 간격 등 특정 주기로 수집되는 센서 데이터(Trace Data)를 보고합니다.|

---

### **S7: Process Program Management (레시피 관리)**

공정에 사용되는 레시피(Process Program)를 장비와 주고받을 때 사용됩니다.

|메시지 (SxFy)|이름|역할 및 기능|
|---|---|---|
|**S7F1 (R)**|Process Program Load Inquire|특정 레시피를 장비로 전송해도 되는지 문의합니다.|
|**S7F3 (S)**|Process Program Send|S7F1 문의에 'OK' 응답을 받은 후, 실제 레시피 본문을 장비로 전송합니다. 📄|
|**S7F5 (R)**|Process Program Request|호스트가 장비에 저장된 특정 레시피를 요청합니다.|
|**S7F6 (S)**|Process Program Data|S7F5 요청에 대한 응답으로, 레시피 본문을 호스트로 전송합니다.|
|**S7F19 (R)**|Current EPPD Request|장비에 등록된 모든 레시피의 목록을 요청합니다.|

_(R) = Request (요청), (S) = Secondary (응답 또는 보고)_


``` mermaid
sequenceDiagram
    participant Host (Active Role)
    participant Equipment (Passive Role)

    %% == 1. HSMS/TCP-IP 연결 단계 == %%
    Note over Host, Equipment: 1. 네트워크 연결 (HSMS/TCP-IP)
    Host->>Equipment: TCP/IP 연결 요청 (Connect)
    Note right of Equipment: Listen 상태에서 대기
    Equipment-->>Host: TCP/IP 연결 수락 (Accept)
    Host->>Equipment: HSMS 세션 요청 (Select.req)
    Equipment-->>Host: HSMS 세션 응답 (Select.rsp)
    Note over Host, Equipment: HSMS 'SELECTED' 상태 진입 ✅

    %% == 2. SECS-II 통신 개시 단계 == %%
    Note over Host, Equipment: 2. 통신 개시 (SECS-II)
    Host->>Equipment: S1F13 (Establish Communication Request)
    Equipment-->>Host: S1F14 (Establish Communication Acknowledge)
    Note over Host, Equipment: SECS-II 통신 준비 완료 ✅

    %% == 3. SECS-II 상태 확인 단계 == %%
    Note over Host, Equipment: 3. 온라인 상태 확인 (SECS-II)
    Host->>Equipment: S1F1 (Are You There Request)
    Equipment-->>Host: S1F2 (On-Line Data)
    Note over Host, Equipment: 데이터 교환 가능 상태 확인 완료 ✅
```