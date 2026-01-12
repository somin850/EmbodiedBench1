# 코랩에서 ALFRED 실행 설정 가이드

## 방법 1: 구글 드라이브에 올리고 마운트 (추천)

### 1단계: 프로젝트를 구글 드라이브에 업로드
- `2025_EmbodiedBench2` 폴더 전체를 구글 드라이브에 업로드
- 예: `/content/drive/MyDrive/2025_EmbodiedBench2`

### 2단계: 코랩에서 실행

```python
# 셀 1: 구글 드라이브 마운트
from google.colab import drive
drive.mount('/content/drive')

# 셀 2: 필요한 패키지 설치 (한 번만 실행, 이미 설치된 것은 스킵)
import subprocess
import sys

def check_and_install(package, version=None):
    """패키지가 설치되어 있으면 스킵, 없으면 설치"""
    try:
        __import__(package)
        print(f"✅ {package} already installed")
        return False
    except ImportError:
        if version:
            print(f"📦 Installing {package}=={version}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}=={version}", "-q"])
        else:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
        return True

# 필수 패키지 확인 및 설치 (없는 것만)
print("Checking required packages...")
check_and_install("ai2thor", "2.1.0")
check_and_install("hydra-core")
check_and_install("omegaconf")
check_and_install("gym")
check_and_install("revtok")  # ALFRED 데이터 전처리용
check_and_install("progressbar2")  # progressbar 모듈

# 프로젝트 경로 설정 (셀 2에서 이미 했으면 생략 가능)
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')  # 실제 경로로 변경
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if os.getcwd() != str(PROJECT_ROOT):
    os.chdir(PROJECT_ROOT)

# 프로젝트 설치 확인
try:
    import embodiedbench
    print("✅ Project already installed")
except ImportError:
    print("📦 Installing project...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", ".", "-q"])

# 셀 3: API 키 설정
os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'  # 실제 API 키로 변경
# os.environ['ANTHROPIC_API_KEY'] = 'your-anthropic-api-key-here'  # Claude 사용 시
# os.environ['GEMINI_API_KEY'] = 'your-gemini-api-key-here'  # Gemini 사용 시

print(f"Working directory: {os.getcwd()}")
print(f"API Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")

# 프로젝트 설치 (필요한 경우)
!pip install -e . 2>&1 | tail -5  # 에러만 확인

# 셀 4: Baseline 실행
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

# 셀 5: Failure Only 실행 (baseline 완료 후)
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

## 방법 2: GitHub에서 클론 (더 깔끔함)

```python
# 셀 1: GitHub에서 클론
!git clone https://github.com/your-username/2025_EmbodiedBench2.git
# 또는 구글 드라이브에 올린 후 클론
!git clone /content/drive/MyDrive/2025_EmbodiedBench2

# 셀 2: 환경 설정
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path('/content/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# 나머지는 방법 1과 동일
```

## 방법 3: 직접 업로드 (간단하지만 느림)

```python
# 셀 1: 파일 업로드
from google.colab import files
uploaded = files.upload()  # zip 파일 업로드

# 셀 2: 압축 해제
!unzip 2025_EmbodiedBench2.zip

# 셀 3: 환경 설정 및 실행 (방법 1과 동일)
```

## 주의사항

1. **구글 드라이브 경로**: 실제 업로드한 경로로 변경해야 함
   - 예: `/content/drive/MyDrive/2025_EmbodiedBench2`
   - 또는: `/content/drive/MyDrive/Projects/2025_EmbodiedBench2`

2. **환경 변수**: API 키 등 필요한 환경 변수 설정
   ```python
   import os
   os.environ['OPENAI_API_KEY'] = 'your-api-key'
   ```

3. **패키지 설치**: 필요한 패키지가 설치되어 있는지 확인
   ```python
   !pip install -r requirements.txt  # 필요시
   ```

4. **결과 저장**: 결과는 구글 드라이브에 저장되므로 영구 보관됨

## 추천 방법

**방법 1 (구글 드라이브 마운트)**을 추천합니다:
- ✅ 결과가 구글 드라이브에 저장되어 영구 보관
- ✅ 코드 수정 후 바로 반영 가능
- ✅ 여러 노트북에서 같은 프로젝트 사용 가능

## 오류 발생 시

오류가 발생하면 **`COLAB_TROUBLESHOOTING.md`** 파일을 참고하세요.
주요 오류와 수정 방법이 정리되어 있습니다:
- 프로젝트 경로 오류
- API 키 오류
- eval_set 오류
- previous_results_dir 경로 오류
- 모듈 import 오류
- 기타 설정 오류

