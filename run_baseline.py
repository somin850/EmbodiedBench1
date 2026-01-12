#!/usr/bin/env python
"""Baseline evaluation script for ALFRED"""
from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator
import os

# 환경 변수 설정
os.environ['DISPLAY'] = ':1'
# API 키 확인
if 'OPENAI_API_KEY' not in os.environ:
    print("⚠️  WARNING: OPENAI_API_KEY not set! Please set it:")
    print("   export OPENAI_API_KEY='your-api-key-here'")
    print("   Or uncomment the line below in run_baseline.py")
    # os.environ['OPENAI_API_KEY'] = 'your-api-key-here'  # ⚠️ 실제 키로 변경!

config = {
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

if __name__ == '__main__':
    print("=" * 60)
    print("Running Baseline Evaluation")
    print("=" * 60)
    
    evaluator = EB_AlfredEvaluator(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()
    
    print("\n✅ Baseline evaluation completed!")

