# 코랩 필수 패키지 설치 (한 번만 실행)

## 셀 2: 모든 필수 패키지 한 번에 설치

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

## 중요 사항

1. **이 셀은 한 번만 실행**: 이미 설치된 패키지는 스킵합니다
2. **GPU 절약**: 중복 설치를 방지합니다
3. **필수 패키지만**: ALFRED 실행에 꼭 필요한 것만 설치합니다

## 패키지 목록 설명

- `ai2thor==2.1.0`: ALFRED 시뮬레이터 (버전 고정)
- `revtok`, `vocab`: ALFRED 데이터 전처리용
- `hydra-core`, `omegaconf`: 설정 관리
- `gym`: 환경 인터페이스
- `progressbar2`: 진행 표시줄
- 나머지: 이미 코랩에 설치되어 있을 수 있음

## 다음 단계

셀 2 실행 후 → 셀 3 (API 키 설정) → 셀 4 (Baseline 실행)

