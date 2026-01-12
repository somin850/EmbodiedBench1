# 코랩 실행 최종 수정본 (Unity 통신 문제 해결)

## 문제 진단
- AI2-THOR 2.1.0 (2019 빌드)는 오래되어 현대 환경과 통신 문제 발생
- Unity 실행은 되지만 Python과 IPC 통신 실패

## 해결 방안 3가지

### 방안 1: AI2-THOR 업그레이드 (권장)
```python
# 셀 1: AI2-THOR 4.x 설치 (2.1.0보다 안정적, 5.x보다 호환성 좋음)
!pip install ai2thor==4.3.0 --force-reinstall

# 코드 수정 필요:
# - controller.py의 일부 API 변경 대응
# - raise_for_failure 인자 제거 등
```

### 방안 2: headless=True 모드 강제 (시도해볼 가치)
```python
# thor_env.py __init__에서
super().__init__(
    quality=quality,
    headless=True,  # 이미 False로 설정되어 있음
    # ... 기타 파라미터
)
```

### 방안 3: 네트워크 포트 기반 통신 강제
코랩에서 UNIX 소켓 대신 TCP 소켓 사용

## 즉시 시도 가능한 방법 (코드 수정 최소화)

### Step 1: Xvfb 확실하게 시작
```python
import subprocess, os, time

# 기존 정리
subprocess.run(['pkill', '-9', 'Xvfb'], stderr=subprocess.DEVNULL)
subprocess.run(['rm', '-rf', '/tmp/.X11-unix', '/tmp/.X*-lock'], stderr=subprocess.DEVNULL)
os.makedirs('/tmp/.X11-unix', mode=0o1777, exist_ok=True)
time.sleep(2)

# Xvfb 시작 (TCP 리스닝 추가)
xvfb_proc = subprocess.Popen([
    'Xvfb', ':1',
    '-screen', '0', '1024x768x24',
    '-ac',
    '+extension', 'GLX',
    '-listen', 'tcp',
    '-nolisten', 'unix'  # UNIX 소켓 비활성화
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)

# 확인
os.environ['DISPLAY'] = ':1'
print(f"Xvfb PID: {xvfb_proc.pid}")
print(f"Xvfb running: {xvfb_proc.poll() is None}")
```

### Step 2: Unity 실행 후 통신 상태 모니터링
```python
# run_baseline.py에 타임아웃 추가
import signal

def timeout_handler(signum, frame):
    print("❌ Unity 통신 타임아웃 (30초)")
    raise TimeoutError("Unity communication timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30초 타임아웃

try:
    evaluator.evaluate_main()
except TimeoutError:
    print("Unity가 응답하지 않습니다. 프로세스 종료 중...")
    subprocess.run(['pkill', '-9', 'thor'])
finally:
    signal.alarm(0)
```

### Step 3: Unity 로그 실시간 확인
```python
import threading

def monitor_unity_log():
    log_path = os.path.expanduser('~/.config/unity3d/Allen Institute for Artificial Intelligence/AI2-Thor/Player.log')
    if os.path.exists(log_path):
        subprocess.run(['tail', '-f', log_path])

# 백그라운드에서 로그 모니터링
log_thread = threading.Thread(target=monitor_unity_log, daemon=True)
log_thread.start()
```

## 최종 권장 사항

**코랩에서 바로 시도:**

```python
# === 셀 1: 환경 설정 ===
import subprocess, os, time

# 완전 정리
subprocess.run(['pkill', '-9', 'Xvfb', 'python', 'thor'], stderr=subprocess.DEVNULL)
time.sleep(2)

# Xvfb TCP 모드
os.makedirs('/tmp/.X11-unix', mode=0o1777, exist_ok=True)
xvfb = subprocess.Popen([
    'Xvfb', ':1', '-screen', '0', '1024x768x24', '-ac', '+extension', 'GLX',
    '-listen', 'tcp'
], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(3)
os.environ['DISPLAY'] = ':1'
print(f"✓ Xvfb started (PID: {xvfb.pid})")

# === 셀 2: 빠른 테스트 ===
from embodiedbench.envs.eb_alfred.env.thor_env import ThorEnv

print("ThorEnv 생성 시도...")
env = ThorEnv()
print("✓ ThorEnv 생성 성공!")
print(f"Server: {env.server is not None}")

# reset 테스트
print("Reset 시도...")
event = env.reset('FloorPlan1')
print(f"✓ Reset 성공! Event: {event is not None}")
```

이게 성공하면 → 전체 evaluation 실행
실패하면 → **AI2-THOR 버전 업그레이드 필요**

## AI2-THOR 4.3.0 업그레이드 가이드

만약 위 방법도 실패하면:

```bash
# 1. 설치
pip install ai2thor==4.3.0

# 2. 코드 수정 (자동 스크립트)
cd /content/drive/MyDrive/2025_EmbodiedBench2
python << 'EOF'
import re

# controller.py 수정
with open('embodiedbench/envs/eb_alfred/env/controller.py', 'r') as f:
    content = f.read()

# raise_for_failure 인자 제거
content = re.sub(r',\s*raise_for_failure=\w+', '', content)

with open('embodiedbench/envs/eb_alfred/env/controller.py', 'w') as f:
    f.write(content)

print("✓ controller.py 수정 완료")
EOF
```

## 결론

**코랩은 WSL2가 아니므로 소켓 문제 없음.** TCP 모드 Xvfb로 재시도하면 높은 확률로 성공할 것입니다.


