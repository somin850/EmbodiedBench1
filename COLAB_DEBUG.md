# 코랩 실행 중 문제 해결

## Unity 바이너리 다운로드 후 대기 시간

### 정상적인 경우
- Unity 바이너리 다운로드: 1-3분 (390MB)
- Unity 프로세스 시작: 30초-2분 (처음 실행 시)
- **총 대기 시간: 최대 5분까지 정상**

### 문제가 있는 경우
- 5분 이상 멈춤 → 문제 가능성 높음
- X 서버 경고 메시지 → headless 모드 문제 가능

## 현재 상황 진단

### 1. X 서버 확인
코랩 셀에서 실행:
```python
# X 서버 상태 확인
import subprocess
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
if 'X' in result.stdout or 'startx' in result.stdout:
    print("✅ X server is running")
else:
    print("❌ X server is NOT running")

# DISPLAY 환경 변수 확인
import os
print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
```

### 2. Unity 프로세스 확인
```python
# Unity 프로세스 확인
import subprocess
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
if 'thor' in result.stdout.lower() or 'unity' in result.stdout.lower():
    print("✅ Unity process is running")
    # 프로세스 정보 출력
    for line in result.stdout.split('\n'):
        if 'thor' in line.lower() or 'unity' in line.lower():
            print(line)
else:
    print("❌ Unity process is NOT running")
```

### 3. Xvfb 사용 (NVIDIA GPU 없을 때)

코랩에서는 NVIDIA GPU가 없을 수 있으므로 Xvfb를 사용해야 합니다:

```python
# 셀 2.5: Xvfb 설치 및 시작 (패키지 설치 셀 다음에 추가)
import subprocess
import os

# Xvfb 설치
try:
    subprocess.run(['which', 'Xvfb'], check=True, capture_output=True)
    print("✅ Xvfb already installed")
except:
    print("📦 Installing Xvfb...")
    subprocess.run(['apt-get', 'update', '-qq'], check=True)
    subprocess.run(['apt-get', 'install', '-y', '-qq', 'xvfb'], check=True)
    print("✅ Xvfb installed")

# Xvfb 시작 (display :1)
import subprocess
import time

# 이미 실행 중인지 확인
try:
    result = subprocess.run(['xdpyinfo', '-display', ':1'], 
                          capture_output=True, timeout=1)
    if result.returncode == 0:
        print("✅ Xvfb already running on :1")
    else:
        raise Exception("Not running")
except:
    print("📦 Starting Xvfb on :1...")
    # Xvfb를 백그라운드로 시작
    xvfb_process = subprocess.Popen(
        ['Xvfb', ':1', '-screen', '0', '1024x768x24'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)  # Xvfb 시작 대기
    if xvfb_process.poll() is None:
        print("✅ Xvfb started on :1")
        os.environ['DISPLAY'] = ':1'
    else:
        print("❌ Failed to start Xvfb")

print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
```

## 해결 방법

### 방법 1: startx.py 사용 (NVIDIA GPU 있을 때 - 공식 방법)

코랩 셀에서 실행:
```python
# 셀 2.5: Headless X 서버 시작 (공식 방법)
import subprocess
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

startx_script = PROJECT_ROOT / 'embodiedbench' / 'envs' / 'eb_alfred' / 'scripts' / 'startx.py'

if startx_script.exists():
    print("📦 Starting headless X server using startx.py...")
    process = subprocess.Popen(
        [sys.executable, str(startx_script), '1'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(3)
    if process.poll() is None:
        os.environ['DISPLAY'] = ':1'
        print("✅ Headless X server started on :1")
    else:
        print("⚠️ startx.py exited")
else:
    print(f"❌ startx.py not found")
```

위의 "셀 2.5" 코드를 셀 2와 셀 3 사이에 추가하고 실행하세요.

### 방법 2: 대기 시간 늘리기

5분까지는 정상이므로 조금 더 기다려보세요. 

### 방법 3: 재시작

만약 5분 이상 멈춰있다면:
1. 셀 중단 (Interrupt)
2. Xvfb 시작 (셀 2.5 실행)
3. 다시 Baseline 실행

## 체크리스트

- [ ] Unity 바이너리 다운로드 완료 (100%)
- [ ] Xvfb 실행 중 (display :1)
- [ ] DISPLAY 환경 변수 설정됨 (:1)
- [ ] 5분 이내 Unity 프로세스 시작

## 다음 단계

1. **지금**: 5분까지 기다려보기
2. **5분 초과 시**: 셀 중단 → Xvfb 시작 → 재실행
3. **Xvfb 시작 후**: 다시 Baseline 실행

