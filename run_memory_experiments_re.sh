#!/bin/bash
# 메모리 실험 전체 실행 스크립트
# 1. Baseline (10개씩)
# 2. Failure only (10개씩)
# 3. Success and failure (10개씩)
# 4. Success only (10개씩)

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
    
    # 모델 이름 (첫 번째 인자로 받거나 기본값 사용)
    MODEL_NAME=${1:-"gpt-4o-mini"}
    TASKS_PER_VARIATION=${2:-5}
    
    echo "=========================================="
    echo "메모리 실험 전체 실행"
    echo "Model: $MODEL_NAME"
    echo "Tasks per variation: $TASKS_PER_VARIATION"
    echo "=========================================="
    echo ""
    
    # 1. Baseline 실행
    echo "=========================================="
    echo "Step 1: Baseline 실행"
    echo "=========================================="
    python -m embodiedbench.main \
        env=eb-man \
        model_name="$MODEL_NAME" \
        model_type=remote \
        exp_name=baseline3_re \
        tasks_per_variation=$TASKS_PER_VARIATION \
        task_selection_seed=42 \
        memory_mode=baseline \
        eval_sets=[base] \
        resolution=500 \
        n_shots=4 \
        detection_box=1 \
        multiview=0 \
        multistep=0 \
        language_only=0
    
    if [ $? -ne 0 ]; then
        echo "❌ Baseline 실행 실패"
        kill $XVFB_PID 2>/dev/null
        exit 1
    fi
    
    BASELINE_RESULTS="running/eb_manipulation/$MODEL_NAME/baseline3_re/base/results"
    echo ""
    echo "✅ Baseline 완료! 결과: $BASELINE_RESULTS"
    echo ""
    
    # 2. Failure only 실행
    echo "=========================================="
    echo "Step 2: Failure only 실행"
    echo "=========================================="
    python -m embodiedbench.main \
        env=eb-man \
        model_name="$MODEL_NAME" \
        model_type=remote \
        exp_name=failure_memory3_re \
        tasks_per_variation=$TASKS_PER_VARIATION \
        task_selection_seed=42 \
        memory_mode=failure_only \
        previous_results_dir=$BASELINE_RESULTS \
        eval_sets=[base] \
        resolution=500 \
        n_shots=4 \
        detection_box=1 \
        multiview=0 \
        multistep=0 \
        language_only=0
    
    if [ $? -ne 0 ]; then
        echo "❌ Failure only 실행 실패"
        kill $XVFB_PID 2>/dev/null
        exit 1
    fi
    
    echo ""
    echo "✅ Failure only 완료!"
    echo ""
    
    # 3. Success and failure 실행
    echo "=========================================="
    echo "Step 3: Success and failure 실행"
    echo "=========================================="
    python -m embodiedbench.main \
        env=eb-man \
        model_name="$MODEL_NAME" \
        model_type=remote \
        exp_name=all_memory3_re \
        tasks_per_variation=$TASKS_PER_VARIATION \
        task_selection_seed=42 \
        memory_mode=success_and_failure \
        previous_results_dir=$BASELINE_RESULTS \
        eval_sets=[base] \
        resolution=500 \
        n_shots=4 \
        detection_box=1 \
        multiview=0 \
        multistep=0 \
        language_only=0
    
    if [ $? -ne 0 ]; then
        echo "❌ Success and failure 실행 실패"
        kill $XVFB_PID 2>/dev/null
        exit 1
    fi
    
    echo ""
    echo "✅ Success and failure 완료!"
    echo ""
    
    # 4. Success only 실행
    echo "=========================================="
    echo "Step 4: Success only 실행"
    echo "=========================================="
    python -m embodiedbench.main \
        env=eb-man \
        model_name="$MODEL_NAME" \
        model_type=remote \
        exp_name=success_memory3_re \
        tasks_per_variation=$TASKS_PER_VARIATION \
        task_selection_seed=42 \
        memory_mode=success_only \
        previous_results_dir=$BASELINE_RESULTS \
        eval_sets=[base] \
        resolution=500 \
        n_shots=4 \
        detection_box=1 \
        multiview=0 \
        multistep=0 \
        language_only=0
    
    if [ $? -ne 0 ]; then
        echo "❌ Success only 실행 실패"
        kill $XVFB_PID 2>/dev/null
        exit 1
    fi
    
    echo ""
    echo "✅ Success only 완료!"
    echo ""
    
    # Xvfb 종료
    kill $XVFB_PID 2>/dev/null
    wait $XVFB_PID 2>/dev/null
    
    echo "=========================================="
    echo "✅ 모든 실험 완료!"
    echo "=========================================="
    echo ""
    echo "결과 위치:"
    echo "  - Baseline: running/eb_manipulation/$MODEL_NAME/baseline3_re/base/results/"
    echo "  - Failure only: running/eb_manipulation/$MODEL_NAME/failure_memory3_re/base/results/"
    echo "  - Success and failure: running/eb_manipulation/$MODEL_NAME/all_memory3_re/base/results/"
    echo "  - Success only: running/eb_manipulation/$MODEL_NAME/success_memory3_re/base/results/"
    echo ""
    
    exit 0
else
    echo "✗ Xvfb 시작 실패"
    exit 1
fi

