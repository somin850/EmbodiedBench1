# ALFRED Headless Mode Fixes

## 수정된 파일 목록

### 1. `embodiedbench/envs/eb_alfred/env/controller.py`
- **Line 731-735**: `Initialize` → `Pass`로 변경
  - 이유: headless 모드에서 `Initialize`가 blocking을 일으킴
  - `Initialize`는 `__init__`에서 이미 호출되므로 `reset()`에서는 프레임만 진행

### 2. `embodiedbench/envs/eb_alfred/env/thor_env.py`
- **Line 143-177**: `reset()` 메서드 수정
  - `super().reset(scene_name)`만 호출 (ai2thor Controller.reset는 scene_name만 받음)
  
- **Line 181-198**: `restore_scene()` 메서드
  - 중복 `Initialize` 호출 제거 (이미 `reset()`에서 처리됨)

- **Line 32-123**: 자동 headless X 서버 시작 로직 추가
  - NVIDIA GPU 감지 시 `startx.py` 자동 실행
  - 환경 변수 `AUTO_STARTX=True` (기본값)로 제어

### 3. `embodiedbench/envs/eb_alfred/EBAlfEnv.py`
- **Line 105-107**: X 서버 설정 로직을 `ThorEnv`로 위임

## 코랩 사용 방법

```bash
# 환경 변수 설정 (선택사항, 기본값이 True)
export AUTO_STARTX=True

# 실행
conda activate embench
python -m embodiedbench.main env=eb-alf model_name=gpt-4o-mini exp_name='baseline'
```

## 주요 변경 사항

1. **Blocking 문제 해결**: `Initialize` → `Pass`로 변경하여 headless 모드에서 blocking 방지
2. **자동 headless 모드**: NVIDIA GPU 감지 시 자동으로 `startx.py` 실행
3. **중복 제거**: `restore_scene()`에서 중복 `Initialize` 호출 제거

## 주의사항

- `controller.py`는 원본 파일이지만 blocking 문제 해결을 위해 수정됨
- 코랩에서는 NVIDIA GPU가 있으면 자동으로 headless X 서버가 시작됨
- 로컬에서 테스트 시 `AUTO_STARTX=False`로 설정하면 수동 제어 가능

