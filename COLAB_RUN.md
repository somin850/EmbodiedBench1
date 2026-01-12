# 코랩에서 ALFRED 실행 가이드

코랩에서는 명령줄 대신 Python 코드로 직접 실행해야 합니다.

## 방법 1: Python 스크립트 사용 (추천)

### 1단계: Baseline 실행

```python
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정 (코랩에서 실제 경로로 변경)
PROJECT_ROOT = Path('/content/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator

# Baseline 설정
config_baseline = {
    'model_name': 'gpt-4o-mini',
    'n_shots': 10,
    'down_sample_ratio': 1.0,
    'model_type': 'remote',
    'language_only': 0,
    'exp_name': 'baseline_memory_test',
    'chat_history': 0,
    'detection_box': 0,
    'eval_sets': ['common_sense'],  # 원하는 eval_set로 변경 가능
    'selected_indexes': [],
    'multistep': 0,
    'resolution': 500,
    'env_feedback': 1,
    'tp': 1,
    'memory_mode': 'baseline',
    'previous_results_dir': None,
    'seed': 42,
    'tasks_per_task_type': 5,  # 각 task_type당 5개씩 선택
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
    evaluator_baseline.env.log_path if evaluator_baseline.env else 'running/eb_alfred',
    'gpt-4o-mini_baseline_memory_test',
    'common_sense',
    'results'
)

print(f"\nBaseline evaluation completed!")
print(f"Results saved to: {baseline_results_path}")
```

### 2단계: Failure Only 실행

```python
# 위 셀에서 저장된 baseline_results_path 사용
# 또는 직접 경로 지정:
# baseline_results_path = 'running/eb_alfred/gpt-4o-mini_baseline_memory_test/common_sense/results'

# Failure Only 설정
config_failure = {
    'model_name': 'gpt-4o-mini',
    'n_shots': 10,
    'down_sample_ratio': 1.0,
    'model_type': 'remote',
    'language_only': 0,
    'exp_name': 'failure_only_memory_test',
    'chat_history': 0,
    'detection_box': 0,
    'eval_sets': ['common_sense'],  # baseline과 동일한 eval_set 사용
    'selected_indexes': [],
    'multistep': 0,
    'resolution': 500,
    'env_feedback': 1,
    'tp': 1,
    'memory_mode': 'failure_only',
    'previous_results_dir': baseline_results_path,  # baseline 결과 경로
    'seed': 42,  # baseline과 동일한 시드
    'tasks_per_task_type': 5,  # baseline과 동일
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
print(f"Results saved to: {evaluator_failure.env.log_path if evaluator_failure.env else 'N/A'}")
```

## 방법 2: 스크립트 파일 사용

코랩에서 `run_alfred_colab.py` 파일을 업로드하고:

```python
# 셀에서 실행
!python run_alfred_colab.py --mode baseline --eval_set common_sense --tasks_per_task_type 5

# 또는 failure_only 실행
!python run_alfred_colab.py --mode failure_only \
  --baseline_results_dir running/eb_alfred/gpt-4o-mini_baseline_memory_test/common_sense/results \
  --eval_set common_sense --tasks_per_task_type 5
```

## 방법 3: 셀에서 직접 실행 (간단한 방법)

코랩 노트북 셀에서:

```python
# 셀 1: Baseline
exec(open('run_alfred_colab.py').read().replace('if __name__', '# if __name__'))
run_baseline()

# 셀 2: Failure Only (baseline 완료 후)
baseline_path = 'running/eb_alfred/gpt-4o-mini_baseline_memory_test/common_sense/results'
run_failure_only(baseline_path)
```

## 주의사항

1. **프로젝트 경로**: 코랩에서 실제 프로젝트 경로로 변경 (`/content/2025_EmbodiedBench2`)
2. **환경 변수**: API 키 등 필요한 환경 변수 설정
3. **결과 경로**: baseline 실행 후 결과 경로를 정확히 확인하여 failure_only 실행 시 사용

## 결과 확인

```python
import json
from pathlib import Path

# Baseline 결과 확인
baseline_results_dir = Path(baseline_results_path)
if baseline_results_dir.exists():
    print(f"Files in directory:")
    for f in sorted(baseline_results_dir.glob('*.json')):
        print(f"  - {f.name}")
    
    # Summary 파일 확인
    summary_file = baseline_results_dir / 'summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        print(f"\nBaseline Summary:")
        print(json.dumps(summary, indent=2))
```


