#!/bin/bash
# EB-Manipulation headless 모드 테스트 스크립트

cd /home/somin/2025_EmbodiedBench2
source ~/miniconda3/etc/profile.d/conda.sh
conda activate embench_man

# 환경 변수 설정
export COPPELIASIM_ROOT=/home/somin/CoppeliaSim
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$COPPELIASIM_ROOT:$LD_LIBRARY_PATH
export QT_QPA_PLATFORM_PLUGIN_PATH=$COPPELIASIM_ROOT
export QT_QPA_PLATFORM=xcb

# 기존 Xvfb 프로세스 종료 (있다면)
pkill -f "Xvfb :1" 2>/dev/null

# Xvfb로 가상 디스플레이 시작
echo "=== Xvfb 가상 디스플레이 시작 ==="
Xvfb :1 -screen 0 1024x768x24 > /dev/null 2>&1 &
XVFB_PID=$!
sleep 2

if ps -p $XVFB_PID > /dev/null; then
    echo "✓ Xvfb 시작 성공 (PID: $XVFB_PID)"
    export DISPLAY=:1
    echo "DISPLAY: $DISPLAY"
    echo ""
    
    echo "=== EB-Manipulation 테스트 실행 ==="
    timeout 30 python -m embodiedbench.envs.eb_manipulation.EBManEnv 2>&1 | \
        grep -v "This plugin does not support raise()" | \
        tail -30
    
    EXIT_CODE=$?
    
    # Xvfb 종료
    kill $XVFB_PID 2>/dev/null
    wait $XVFB_PID 2>/dev/null
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✓ 테스트 성공!"
    else
        echo ""
        echo "✗ 테스트 실패 (exit code: $EXIT_CODE)"
    fi
    
    exit $EXIT_CODE
else
    echo "✗ Xvfb 시작 실패"
    echo "Xvfb가 설치되어 있는지 확인하세요: sudo apt-get install -y xvfb"
    exit 1
fi



