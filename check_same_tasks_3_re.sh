#!/bin/bash

# 같은 seed로 실행된 실험들이 같은 task를 수행했는지 확인하는 스크립트

MODEL_NAME=${1:-"gpt-4o-mini"}

echo "=========================================="
echo "같은 Task 수행 여부 확인 (3_re)"
echo "Model: $MODEL_NAME"
echo "=========================================="
echo ""

BASELINE_DIR="running/eb_manipulation/$MODEL_NAME/baseline3_re/base/results"
FAILURE_DIR="running/eb_manipulation/$MODEL_NAME/failure_memory3_re/base/results"
ALL_DIR="running/eb_manipulation/$MODEL_NAME/all_memory3_re/base/results"
SUCCESS_DIR="running/eb_manipulation/$MODEL_NAME/success_memory3_re/base/results"

# 디렉토리 존재 확인
if [ ! -d "$BASELINE_DIR" ]; then
    echo "❌ Baseline 결과 디렉토리가 없습니다: $BASELINE_DIR"
    exit 1
fi

if [ ! -d "$FAILURE_DIR" ]; then
    echo "❌ Failure Memory 결과 디렉토리가 없습니다: $FAILURE_DIR"
    exit 1
fi

if [ ! -d "$ALL_DIR" ]; then
    echo "❌ All Memory 결과 디렉토리가 없습니다: $ALL_DIR"
    exit 1
fi

if [ ! -d "$SUCCESS_DIR" ]; then
    echo "❌ Success Memory 결과 디렉토리가 없습니다: $SUCCESS_DIR"
    exit 1
fi

echo "=== Episode별 Instruction 비교 ==="
echo ""

# 각 episode별로 instruction 비교
for baseline_file in "$BASELINE_DIR"/episode_*_res_baseline.json; do
    if [ ! -f "$baseline_file" ]; then
        continue
    fi
    
    episode_num=$(basename "$baseline_file" | grep -o "episode_[0-9]*" | grep -o "[0-9]*")
    baseline_instruction=$(grep -o '"instruction": "[^"]*"' "$baseline_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
    
    failure_file="$FAILURE_DIR/episode_${episode_num}_res_failure_only.json"
    all_file="$ALL_DIR/episode_${episode_num}_res_success_and_failure.json"
    success_file="$SUCCESS_DIR/episode_${episode_num}_res_success_only.json"
    
    failure_instruction=""
    all_instruction=""
    success_instruction=""
    
    if [ -f "$failure_file" ]; then
        failure_instruction=$(grep -o '"instruction": "[^"]*"' "$failure_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
    fi
    
    if [ -f "$all_file" ]; then
        all_instruction=$(grep -o '"instruction": "[^"]*"' "$all_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
    fi
    
    if [ -f "$success_file" ]; then
        success_instruction=$(grep -o '"instruction": "[^"]*"' "$success_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
    fi
    
    # 비교
    all_match=true
    if [ -n "$failure_instruction" ] && [ "$baseline_instruction" != "$failure_instruction" ]; then
        all_match=false
    fi
    if [ -n "$all_instruction" ] && [ "$baseline_instruction" != "$all_instruction" ]; then
        all_match=false
    fi
    if [ -n "$success_instruction" ] && [ "$baseline_instruction" != "$success_instruction" ]; then
        all_match=false
    fi
    
    if [ "$all_match" = true ] && [ -n "$failure_instruction" ] && [ -n "$all_instruction" ] && [ -n "$success_instruction" ]; then
        echo "✅ Episode $episode_num: 모두 일치"
    elif [ "$all_match" = false ]; then
        echo "❌ Episode $episode_num: 불일치"
        echo "   Baseline: $baseline_instruction"
        if [ -n "$failure_instruction" ]; then
            echo "   Failure:  $failure_instruction"
        fi
        if [ -n "$all_instruction" ]; then
            echo "   All:      $all_instruction"
        fi
        if [ -n "$success_instruction" ]; then
            echo "   Success:  $success_instruction"
        fi
    fi
done

echo ""
echo "=== 요약 ==="
echo ""

baseline_count=$(ls "$BASELINE_DIR"/episode_*_res_baseline.json 2>/dev/null | wc -l)
failure_count=$(ls "$FAILURE_DIR"/episode_*_res_failure_only.json 2>/dev/null | wc -l)
all_count=$(ls "$ALL_DIR"/episode_*_res_success_and_failure.json 2>/dev/null | wc -l)
success_count=$(ls "$SUCCESS_DIR"/episode_*_res_success_only.json 2>/dev/null | wc -l)

echo "Baseline: $baseline_count episodes"
echo "Failure:  $failure_count episodes"
echo "All:      $all_count episodes"
echo "Success:  $success_count episodes"
echo ""

# 모든 episode의 instruction이 일치하는지 확인
match_count=0
mismatch_count=0

for baseline_file in "$BASELINE_DIR"/episode_*_res_baseline.json; do
    if [ ! -f "$baseline_file" ]; then
        continue
    fi
    
    episode_num=$(basename "$baseline_file" | grep -o "episode_[0-9]*" | grep -o "[0-9]*")
    baseline_instruction=$(grep -o '"instruction": "[^"]*"' "$baseline_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
    
    failure_file="$FAILURE_DIR/episode_${episode_num}_res_failure_only.json"
    all_file="$ALL_DIR/episode_${episode_num}_res_success_and_failure.json"
    success_file="$SUCCESS_DIR/episode_${episode_num}_res_success_only.json"
    
    if [ -f "$failure_file" ] && [ -f "$all_file" ] && [ -f "$success_file" ]; then
        failure_instruction=$(grep -o '"instruction": "[^"]*"' "$failure_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
        all_instruction=$(grep -o '"instruction": "[^"]*"' "$all_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
        success_instruction=$(grep -o '"instruction": "[^"]*"' "$success_file" | head -1 | sed 's/"instruction": "\(.*\)"/\1/')
        
        if [ "$baseline_instruction" = "$failure_instruction" ] && \
           [ "$baseline_instruction" = "$all_instruction" ] && \
           [ "$baseline_instruction" = "$success_instruction" ]; then
            match_count=$((match_count + 1))
        else
            mismatch_count=$((mismatch_count + 1))
        fi
    fi
done

echo "일치하는 episodes: $match_count"
echo "불일치하는 episodes: $mismatch_count"
echo ""

if [ $mismatch_count -eq 0 ] && [ $match_count -gt 0 ]; then
    echo "✅ 모든 실험이 같은 task를 수행했습니다!"
else
    echo "❌ 일부 실험이 다른 task를 수행했습니다."
fi



