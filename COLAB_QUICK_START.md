# 코랩 빠른 시작 가이드

## 완전한 실행 코드 (복사해서 사용)

### 셀 1: 구글 드라이브 마운트
```python
from google.colab import drive
drive.mount('/content/drive')
```

### 셀 2: 모든 필수 패키지 설치 (한 번만 실행, 이미 설치된 것은 스킵)
```python
# ALFRED 실행에 필요한 모든 패키지 (한 번만 실행)
import subprocess
import sys

# 필수 패키지 목록
required_packages = [
    "ai2thor==2.1.0",  # ALFRED 시뮬레이터
    "hydra-core",  # 설정 관리
    "omegaconf",  # 설정 관리
    "gym",  # 환경 인터페이스
    "revtok",  # ALFRED 토크나이저
    "vocab",  # ALFRED 어휘 처리
    "progressbar2",  # 진행 표시줄
    "anthropic",  # Claude API (모델 선택 시 필요)
    "openai",  # OpenAI API (GPT 사용 시 필요)
]

print("Checking and installing required packages...")
installed_count = 0
skipped_count = 0

for package in required_packages:
    package_name = package.split("==")[0]
    try:
        __import__(package_name)
        print(f"✅ {package_name} already installed")
        skipped_count += 1
    except ImportError:
        print(f"📦 Installing {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ {package_name} installed")
            installed_count += 1
        except:
            print(f"⚠️ Failed to install {package_name}")

print(f"\n📊 Summary: {installed_count} installed, {skipped_count} already present")

# 프로젝트 경로 설정
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# 프로젝트 설치 (한 번만)
try:
    import embodiedbench
    print("✅ Project already installed")
except ImportError:
    print("📦 Installing project...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Project installed")

print("\n✅ All packages ready!")
```

### 셀 2.5: Headless X 서버 시작 (코랩용 수정 버전)
```python
# startx.py 수정 버전 (코랩 환경에 맞게)
import subprocess
import os
import sys
import time
import tempfile
import shlex
import re
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

def pci_records():
    """NVIDIA GPU 찾기"""
    try:
        command = shlex.split('lspci -vmm')
        output = subprocess.check_output(command).decode()
        records = []
        for devices in output.strip().split("\n\n"):
            record = {}
            records.append(record)
            for row in devices.split("\n"):
                if '\t' in row:
                    key, value = row.split("\t", 1)
                    record[key.split(':')[0]] = value
        return records
    except Exception as e:
        print(f"Error getting PCI records: {e}")
        return []

def generate_xorg_conf(devices):
    """Xorg 설정 파일 생성"""
    device_section = """
Section "Device"
    Identifier     "Device{device_id}"
    Driver         "nvidia"
    VendorName     "NVIDIA Corporation"
    BusID          "{bus_id}"
EndSection
"""
    screen_section = """
Section "Screen"
    Identifier     "Screen{screen_id}"
    Device         "Device{device_id}"
    DefaultDepth    24
    Option         "AllowEmptyInitialConfiguration" "True"
    SubSection     "Display"
        Depth       24
        Virtual 1024 768
    EndSubSection
EndSection
"""
    server_layout = """
Section "ServerLayout"
    Identifier     "Layout0"
    {screen_records}
EndSection
"""
    xorg_conf = []
    screen_records = []
    for i, bus_id in enumerate(devices):
        xorg_conf.append(device_section.format(device_id=i, bus_id=bus_id))
        xorg_conf.append(screen_section.format(device_id=i, screen_id=i))
        screen_records.append(f'Screen {i} "Screen{i}" 0 0')
    xorg_conf.append(server_layout.format(screen_records="\n    ".join(screen_records)))
    return "\n".join(xorg_conf)

# 이미 실행 중인지 확인
try:
    result = subprocess.run(['xdpyinfo', '-display', ':1'], 
                          capture_output=True, timeout=1)
    if result.returncode == 0:
        print("✅ X server already running on :1")
        os.environ['DISPLAY'] = ':1'
    else:
        raise Exception("Not running")
except:
    print("📦 Starting X server on :1...")
    
    # 기존 X 서버 종료
    try:
        subprocess.run(['pkill', '-f', 'Xorg.*:1'], capture_output=True, timeout=2)
        time.sleep(1)
    except:
        pass
    
    # NVIDIA GPU 찾기
    devices = []
    for r in pci_records():
        if r.get('Vendor', '') == 'NVIDIA Corporation' \
                and r.get('Class', '') in ['VGA compatible controller', '3D controller']:
            slot = r.get('Slot', '')
            if slot:
                try:
                    bus_id = 'PCI:' + ':'.join(map(lambda x: str(int(x, 16)), re.split(r'[:\.]', slot)))
                    devices.append(bus_id)
                    print(f"Found NVIDIA GPU: {bus_id}")
                except:
                    pass
    
    if devices:
        # Xorg 설정 생성 및 실행
        xorg_conf = generate_xorg_conf(devices)
        fd, path = tempfile.mkstemp(suffix='.conf', dir='/tmp')
        try:
            with open(path, 'w') as f:
                f.write(xorg_conf)
            
            command = shlex.split(
                f"Xorg -noreset +extension GLX +extension RANDR +extension RENDER "
                f"-config {path} :1"
            )
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            time.sleep(3)
            
            # 확인
            try:
                result = subprocess.run(['xdpyinfo', '-display', ':1'], 
                                      capture_output=True, timeout=2)
                if result.returncode == 0:
                    os.environ['DISPLAY'] = ':1'
                    print("✅ Xorg started successfully on :1")
                else:
                    raise Exception("Not responding")
            except:
                stdout, stderr = process.communicate(timeout=1)
                if stderr:
                    print(f"Xorg error: {stderr.decode()[:200]}")
                raise Exception("Failed")
        finally:
            os.close(fd)
            try:
                os.unlink(path)
            except:
                pass
    else:
        print("⚠️ No NVIDIA GPU found, using Xvfb...")
        devices = None
    
    # Fallback: Xvfb
    if not devices:
        try:
            subprocess.run(['apt-get', 'update', '-qq'], check=True)
            subprocess.run(['apt-get', 'install', '-y', '-qq', 'xvfb'], check=True)
            subprocess.Popen(['Xvfb', ':1', '-screen', '0', '1024x768x24'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            os.environ['DISPLAY'] = ':1'
            print("✅ Xvfb started on :1")
        except Exception as e:
            print(f"❌ Failed: {e}")

print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
```

### 셀 3: 환경 설정 및 API 키
```python
import os
import sys
from pathlib import Path

# ⚠️ API 키 설정 (실제 API 키로 변경)
os.environ['OPENAI_API_KEY'] = "your-api-key-here"

# 구글 드라이브의 프로젝트 경로
PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')  # 실제 경로로 변경
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

print(f"Working directory: {os.getcwd()}")
print(f"API Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")
```

### 셀 4: Baseline 실행
```python
from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator

config_baseline = {
    'model_name': 'gpt-4o-mini',
    'n_shots': 10,
    'down_sample_ratio': 1.0,
    'model_type': 'remote',
    'language_only': 0,
    'exp_name': 'baseline_memory_test',
    'chat_history': 0,
    'detection_box': 0,
    'eval_sets': ['common_sense'],
    'selected_indexes': [],
    'multistep': 0,
    'resolution': 500,
    'env_feedback': 1,
    'tp': 1,
    'memory_mode': 'baseline',
    'previous_results_dir': None,
    'seed': 42,
    'tasks_per_task_type': 5,
    'task_selection_seed': None,
}

print("=" * 60)
print("Running Baseline Evaluation")
print("=" * 60)

evaluator_baseline = EB_AlfredEvaluator(config_baseline)
evaluator_baseline.check_config_valid()
evaluator_baseline.evaluate_main()

# 결과 경로 저장
baseline_results_path = os.path.join(
    evaluator_baseline.env.log_path,
    'gpt-4o-mini_baseline_memory_test',
    'common_sense',
    'results'
)

print(f"\nBaseline evaluation completed!")
print(f"Results saved to: {baseline_results_path}")
```

### 셀 5: Failure Only 실행 (baseline 완료 후)
```python
config_failure = {
    'model_name': 'gpt-4o-mini',
    'n_shots': 10,
    'down_sample_ratio': 1.0,
    'model_type': 'remote',
    'language_only': 0,
    'exp_name': 'failure_only_memory_test',
    'chat_history': 0,
    'detection_box': 0,
    'eval_sets': ['common_sense'],
    'selected_indexes': [],
    'multistep': 0,
    'resolution': 500,
    'env_feedback': 1,
    'tp': 1,
    'memory_mode': 'failure_only',
    'previous_results_dir': baseline_results_path,
    'seed': 42,
    'tasks_per_task_type': 5,
    'task_selection_seed': None,
}

print("=" * 60)
print("Running Failure Only Evaluation")
print(f"Loading memory from: {baseline_results_path}")
print("=" * 60)

evaluator_failure = EB_AlfredEvaluator(config_failure)
evaluator_failure.check_config_valid()
evaluator_failure.evaluate_main()

print(f"\nFailure only evaluation completed!")
```

## 주의사항

1. **셀 2에서 패키지 설치**: `ai2thor` 등 필수 패키지가 설치되어야 합니다
2. **셀 3에서 API 키 설정**: 실제 OpenAI API 키로 변경해야 합니다
3. **셀 3에서 프로젝트 경로**: 실제 업로드한 경로로 변경해야 합니다
4. **셀 4와 5는 순서대로 실행**: Baseline 완료 후 Failure Only 실행

## 오류 발생 시

- `ModuleNotFoundError: No module named 'ai2thor'` → 셀 2 다시 실행
- `FileNotFoundError` → 셀 3의 프로젝트 경로 확인
- `AuthenticationError` → 셀 3의 API 키 확인

