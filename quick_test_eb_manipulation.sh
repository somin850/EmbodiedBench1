#!/bin/bash
# EB-Manipulation 빠른 테스트 스크립트
# README의 down_sample_ratio=0.1 (10% 데이터) 사용

cd /home/somin/2025_EmbodiedBench2
source ~/miniconda3/etc/profile.d/conda.sh
conda activate embench_man

# 환경 변수 설정
export COPPELIASIM_ROOT=/home/somin/CoppeliaSim
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$COPPELIASIM_ROOT:$LD_LIBRARY_PATH
export QT_QPA_PLATFORM_PLUGIN_PATH=$COPPELIASIM_ROOT
export QT_QPA_PLATFORM=xcb

# 기존 Xvfb 프로세스 종료
pkill -f "Xvfb :1" 2>/dev/null
sleep 1

# Xvfb로 가상 디스플레이 시작
echo "=== Xvfb 가상 디스플레이 시작 ==="
Xvfb :1 -screen 0 1024x768x24 > /dev/null 2>&1 &
XVFB_PID=$!
sleep 3

if ps -p $XVFB_PID > /dev/null; then
    echo "✓ Xvfb 시작 성공 (PID: $XVFB_PID)"
    export DISPLAY=:1
    echo "DISPLAY: $DISPLAY"
    echo ""
    
    # API 키 확인
    if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
        echo "⚠️  경고: API 키가 설정되지 않았습니다."
        echo "   다음 중 하나를 설정하세요:"
        echo "   export OPENAI_API_KEY='your_key'"
        echo "   export ANTHROPIC_API_KEY='your_key'"
        echo "   export GEMINI_API_KEY='your_key'"
        echo ""
        echo "계속 진행하시겠습니까? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            kill $XVFB_PID 2>/dev/null
            exit 1
        fi
    fi
    
    # 모델 이름 (첫 번째 인자로 받거나 기본값 사용)
    MODEL_NAME=${1:-"gpt-4o-mini"}
    
    echo "=== EB-Manipulation 빠른 테스트 시작 ==="
    echo "Model: $MODEL_NAME"
    if [ -n "$2" ]; then
        echo "Tasks per variation: $2"
    else
        echo "Down sample ratio: 0.1 (10% 데이터, README 권장 디버깅 값)"
    fi
    echo "Memory mode: ${3:-baseline}"
    if [ -n "$4" ]; then
        echo "Previous results dir: $4"
    fi
    echo "Eval sets: base (빠른 테스트용)"
    echo ""
    echo "Usage: $0 [model_name] [tasks_per_variation] [memory_mode] [previous_results_dir]"
    echo "  Example: $0 gpt-4o-mini 10 baseline"
    echo "  Example: $0 gpt-4o-mini 10 failure_only running/eb_manipulation/gpt-4o-mini/baseline_re/base/results"
    echo ""
    
    # 평가 실행
    # tasks_per_variation과 memory_mode는 선택적 인자로 받음
    TASKS_PER_VARIATION=${2:-""}
    MEMORY_MODE=${3:-"baseline"}
    PREVIOUS_RESULTS_DIR=${4:-""}
    
    CMD="python -m embodiedbench.main \
        env=eb-man \
        model_name=\"$MODEL_NAME\" \
        model_type=remote \
        exp_name=quick_test \
        eval_sets=[base] \
        resolution=500 \
        n_shots=4 \
        detection_box=1 \
        multiview=0 \
        multistep=0 \
        language_only=0 \
        memory_mode=$MEMORY_MODE"
    
    # tasks_per_variation이 지정되면 사용, 아니면 down_sample_ratio 사용
    if [ -n "$TASKS_PER_VARIATION" ]; then
        CMD="$CMD tasks_per_variation=$TASKS_PER_VARIATION"
    else
        CMD="$CMD down_sample_ratio=0.1"
    fi
    
    # previous_results_dir가 지정되면 추가
    if [ -n "$PREVIOUS_RESULTS_DIR" ]; then
        CMD="$CMD previous_results_dir=$PREVIOUS_RESULTS_DIR"
    fi
    
    eval $CMD
    
    EXIT_CODE=$?
    
    # Xvfb 종료
    kill $XVFB_PID 2>/dev/null
    wait $XVFB_PID 2>/dev/null
    
    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ 빠른 테스트 완료!"
        echo ""
        echo "결과 파일 위치:"
        echo "  - 로그: outputs/eb-man/${MODEL_NAME}/quick_test/base/"
        echo "  - 결과: outputs/eb-man/${MODEL_NAME}/quick_test/base/results/"
        echo ""
        echo "결과 확인:"
        echo "  cat outputs/eb-man/${MODEL_NAME}/quick_test/base/results/summary.json"
    else
        echo "❌ 테스트 실패 (exit code: $EXIT_CODE)"
    fi
    
    exit $EXIT_CODE
else
    echo "✗ Xvfb 시작 실패"
    exit 1
fi



