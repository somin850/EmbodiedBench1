#!/bin/bash
set -e

echo "🐳 Docker 컨테이너에서 ALFRED Baseline 실행"
echo "============================================================"

# 1. Docker 이미지 빌드 (처음 한번만)
if [[ ! $(docker images -q embodiedbench:latest 2> /dev/null) ]]; then
    echo "📦 Docker 이미지 빌드 중..."
    docker build -t embodiedbench:latest .
    echo "✅ 이미지 빌드 완료"
else
    echo "✅ 기존 이미지 사용"
fi

# 2. 컨테이너 실행
echo ""
echo "🚀 컨테이너 실행 중..."
docker run --rm \
    -v $(pwd):/app \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    -e DISPLAY=:1 \
    --ipc=host \
    embodiedbench:latest \
    bash -c "
        cd /app
        pip install -e . --quiet
        pip install opencv-python Pillow --quiet
        echo '✅ 패키지 설치 완료'
        echo ''
        echo '🧪 ThorEnv 테스트 중...'
        python3 -c '
from embodiedbench.envs.eb_alfred.env.thor_env import ThorEnv
import os
os.environ[\"DISPLAY\"] = \":1\"
env = ThorEnv()
print(\"✅ ThorEnv 생성 성공\")
event = env.reset(\"FloorPlan1\")
print(\"✅ Reset 성공!\")
        '
        echo ''
        echo '🎯 Baseline 실행...'
        python3 run_baseline.py
    "

