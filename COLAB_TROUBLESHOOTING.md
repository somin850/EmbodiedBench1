# 코랩 오류 해결 가이드

코랩에서 실행 시 발생할 수 있는 오류와 수정 방법을 정리했습니다.

## 🔧 주요 수정 포인트

### 1. 프로젝트 경로 오류

**오류 메시지:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/content/drive/MyDrive/2025_EmbodiedBench2'
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')`
- **수정 방법**: 
  1. 구글 드라이브에서 실제 업로드한 경로 확인
  2. 경로를 정확히 수정
  3. 예: `/content/drive/MyDrive/Projects/2025_EmbodiedBench2`

**확인 방법:**
```python
# 셀에서 실행하여 경로 확인
!ls /content/drive/MyDrive/
# 또는
from pathlib import Path
import os
for item in Path('/content/drive/MyDrive').iterdir():
    print(item)
```

---

### 2. API 키 오류

**오류 메시지:**
```
openai.error.AuthenticationError: Invalid API key
# 또는
KeyError: 'OPENAI_API_KEY'
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'`
- **수정 방법**: 
  1. 실제 OpenAI API 키로 변경
  2. 또는 코랩 Secrets 사용 (권장)

**코랩 Secrets 사용 (권장):**
```python
# 셀에서 실행
from google.colab import userdata
os.environ['OPENAI_API_KEY'] = userdata.get('OPENAI_API_KEY')
```

**Secrets 설정 방법:**
1. 코랩 노트북 우측 상단 🔧 아이콘 클릭
2. "Secrets" 탭 선택
3. "Add secret" 클릭
4. Name: `OPENAI_API_KEY`, Value: 실제 API 키 입력
5. 저장

---

### 3. eval_set 오류

**오류 메시지:**
```
AssertionError: eval_set not in ValidEvalSets
# 또는
KeyError: 'common_sense'
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `'eval_sets': ['common_sense']`
- **수정 방법**: 
  - 유효한 eval_set 사용: `'base'`, `'common_sense'`, `'complex_instruction'`, `'spatial'`, `'visual_appearance'`, `'long_horizon'`

**예시:**
```python
config_baseline = {
    # ...
    'eval_sets': ['common_sense'],  # ← 여기 수정
    # ...
}
```

---

### 4. previous_results_dir 경로 오류 (Failure Only 실행 시)

**오류 메시지:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'running/eb_alfred/...'
# 또는
No memory found for eval_set=...
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `'previous_results_dir': baseline_results_path`
- **수정 방법**: 
  1. Baseline 실행 완료 후 출력된 경로 확인
  2. 정확한 경로로 수정
  3. 경로 형식: `running/eb_alfred/{model_name}_{exp_name}/{eval_set}/results`

**확인 방법:**
```python
# Baseline 실행 후 결과 경로 확인
baseline_results_path = os.path.join(
    evaluator_baseline.env.log_path,
    'gpt-4o-mini_baseline_memory_test',
    'common_sense',
    'results'
)

# 경로가 존재하는지 확인
import os
if os.path.exists(baseline_results_path):
    print(f"✅ Path exists: {baseline_results_path}")
    print(f"Files: {os.listdir(baseline_results_path)[:5]}")  # 처음 5개 파일 확인
else:
    print(f"❌ Path not found: {baseline_results_path}")
    # 실제 경로 찾기
    log_path = evaluator_baseline.env.log_path
    print(f"Actual log_path: {log_path}")
    print(f"Files in log_path: {os.listdir(log_path) if os.path.exists(log_path) else 'N/A'}")
```

**수정 예시:**
```python
# 방법 1: Baseline 실행 후 자동으로 경로 저장
baseline_results_path = os.path.join(
    evaluator_baseline.env.log_path,
    'gpt-4o-mini_baseline_memory_test',
    'common_sense',
    'results'
)

# 방법 2: 직접 경로 지정 (확인 후)
baseline_results_path = 'running/eb_alfred/gpt-4o-mini_baseline_memory_test/common_sense/results'
```

---

### 5. 모듈 import 오류

**오류 메시지:**
```
ModuleNotFoundError: No module named 'ai2thor'
# 또는
ModuleNotFoundError: No module named 'embodiedbench'
# 또는
ImportError: cannot import name 'EB_AlfredEvaluator'
```

**수정 위치:**
- **파일**: 코랩 노트북 셀
- **위치**: import 전에 패키지 설치 셀 추가
- **수정 방법**: 
  1. **필수 패키지 설치 셀 추가** (import 전에 실행):
  ```python
  !pip install ai2thor==2.1.0 hydra-core omegaconf gym numpy tqdm pillow opencv-python-headless -q
  !pip install revtok torch transformers -q  # ALFRED 데이터 전처리용
  !pip install -e . -q  # 프로젝트 설치
  ```
  2. 프로젝트 경로가 올바른지 확인
  3. `os.chdir(PROJECT_ROOT)` 실행 확인

**확인 방법:**
```python
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
print(f"Project root exists: {PROJECT_ROOT.exists()}")
print(f"Project root: {PROJECT_ROOT}")

sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# 모듈 경로 확인
print(f"Python path: {sys.path[:3]}")
print(f"Current directory: {os.getcwd()}")

# embodiedbench 폴더 확인
embodiedbench_path = PROJECT_ROOT / 'embodiedbench'
print(f"embodiedbench exists: {embodiedbench_path.exists()}")

# 테스트 import
try:
    from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator
    print("✅ Import successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
```

---

### 6. tasks_per_task_type 관련 오류

**오류 메시지:**
```
TypeError: select_tasks_per_task_type_alfred() got an unexpected keyword argument
# 또는
No tasks found for task_type
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `'tasks_per_task_type': 5`
- **수정 방법**: 
  - `None`으로 설정하면 전체 task 사용
  - 숫자로 설정하면 각 task_type당 해당 개수만큼 선택

**예시:**
```python
config_baseline = {
    # ...
    'tasks_per_task_type': 5,  # ← 여기 수정 (또는 None)
    # ...
}
```

---

### 7. 시드 관련 오류

**오류 메시지:**
```
TypeError: seed must be an integer
```

**수정 위치:**
- **파일**: 코랩 노트북 셀 (또는 `run_alfred_colab.py`)
- **위치**: `'seed': 42`
- **수정 방법**: 정수 값으로 설정

**예시:**
```python
config_baseline = {
    # ...
    'seed': 42,  # ← 정수로 설정
    'task_selection_seed': None,  # None이면 seed 사용
    # ...
}
```

---

## 📋 체크리스트

코랩에서 실행하기 전 확인사항:

- [ ] 구글 드라이브 마운트 완료
- [ ] 프로젝트 경로가 실제 업로드한 경로와 일치
- [ ] API 키 설정 완료 (OPENAI_API_KEY)
- [ ] eval_set이 유효한 값인지 확인
- [ ] Baseline 실행 완료 후 결과 경로 확인
- [ ] Failure Only 실행 시 previous_results_dir 경로 확인
- [ ] 필요한 패키지 설치 완료

---

## 🔍 디버깅 코드

문제 발생 시 다음 코드로 확인:

```python
# 1. 환경 확인
import os
import sys
from pathlib import Path

print("=" * 60)
print("Environment Check")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path (first 3): {sys.path[:3]}")

# 2. 프로젝트 경로 확인
PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
print(f"\nProject root exists: {PROJECT_ROOT.exists()}")
if PROJECT_ROOT.exists():
    print(f"Project root contents: {list(PROJECT_ROOT.iterdir())[:5]}")

# 3. API 키 확인
print(f"\nAPI Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")
if os.environ.get('OPENAI_API_KEY'):
    key = os.environ.get('OPENAI_API_KEY')
    print(f"API Key (first 10 chars): {key[:10]}...")

# 4. 모듈 import 테스트
try:
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)
    from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator
    print("\n✅ All imports successful!")
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
```

---

## 📞 오류 보고 시 포함할 정보

오류가 발생하면 다음 정보를 포함해서 알려주세요:

1. **오류 메시지 전체** (에러 스택 트레이스)
2. **어느 단계에서 발생** (Baseline? Failure Only?)
3. **수정한 부분** (경로, API 키 등)
4. **위 디버깅 코드 실행 결과**

이 정보를 주시면 정확한 수정 방법을 알려드릴 수 있습니다!

