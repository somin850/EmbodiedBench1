"""
코랩에서 ALFRED 평가를 실행하기 위한 스크립트
"""
import os
import sys
import yaml
from pathlib import Path

# API 키 설정 (필요한 경우)
# 코랩에서 실행 시 환경 변수로 설정하거나 여기서 직접 설정
if 'OPENAI_API_KEY' not in os.environ:
    # 여기에 API 키를 직접 입력하거나, 환경 변수로 설정
    # os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'
    pass

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from embodiedbench.evaluator.eb_alfred_evaluator import EB_AlfredEvaluator

def run_baseline():
    """Baseline 실행 (메모리 없이)"""
    config = {
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
    evaluator = EB_AlfredEvaluator(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()
    print("Baseline evaluation completed!")
    print(f"Results saved to: {evaluator.env.log_path if evaluator.env else 'N/A'}")


def run_failure_only(baseline_results_dir):
    """Failure Only 실행 (baseline 결과를 메모리로 사용)"""
    config = {
        'model_name': 'gpt-4o-mini',
        'n_shots': 10,
        'down_sample_ratio': 1.0,
        'model_type': 'remote',
        'language_only': 0,
        'exp_name': 'failure_only_memory_test',
        'chat_history': 0,
        'detection_box': 0,
        'eval_sets': ['common_sense'],  # 원하는 eval_set로 변경 가능
        'selected_indexes': [],
        'multistep': 0,
        'resolution': 500,
        'env_feedback': 1,
        'tp': 1,
        'memory_mode': 'failure_only',
        'previous_results_dir': baseline_results_dir,  # baseline 결과 경로
        'seed': 42,
        'tasks_per_task_type': 5,  # 각 task_type당 5개씩 선택
        'task_selection_seed': None,
    }
    
    print("=" * 60)
    print("Running Failure Only Evaluation")
    print(f"Loading memory from: {baseline_results_dir}")
    print("=" * 60)
    evaluator = EB_AlfredEvaluator(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()
    print("Failure only evaluation completed!")
    print(f"Results saved to: {evaluator.env.log_path if evaluator.env else 'N/A'}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run ALFRED evaluation in Colab')
    parser.add_argument('--mode', type=str, choices=['baseline', 'failure_only', 'both'], 
                       default='both', help='Evaluation mode')
    parser.add_argument('--baseline_results_dir', type=str, default=None,
                       help='Path to baseline results directory (required for failure_only mode)')
    parser.add_argument('--eval_set', type=str, default='common_sense',
                       help='Evaluation set (common_sense, complex_instruction, spatial, visual_appearance, long_horizon)')
    parser.add_argument('--tasks_per_task_type', type=int, default=5,
                       help='Number of tasks per task_type')
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                       help='Model name')
    
    args = parser.parse_args()
    
    # 공통 설정
    common_config = {
        'eval_sets': [args.eval_set],
        'tasks_per_task_type': args.tasks_per_task_type,
        'model_name': args.model_name,
    }
    
    if args.mode in ['baseline', 'both']:
        config = {
            'model_name': args.model_name,
            'n_shots': 10,
            'down_sample_ratio': 1.0,
            'model_type': 'remote',
            'language_only': 0,
            'exp_name': 'baseline_memory_test',
            'chat_history': 0,
            'detection_box': 0,
            'eval_sets': [args.eval_set],
            'selected_indexes': [],
            'multistep': 0,
            'resolution': 500,
            'env_feedback': 1,
            'tp': 1,
            'memory_mode': 'baseline',
            'previous_results_dir': None,
            'seed': 42,
            'tasks_per_task_type': args.tasks_per_task_type,
            'task_selection_seed': None,
        }
        
        print("=" * 60)
        print("Running Baseline Evaluation")
        print("=" * 60)
        evaluator = EB_AlfredEvaluator(config)
        evaluator.check_config_valid()
        evaluator.evaluate_main()
        
        # 결과 경로 저장
        baseline_results_path = os.path.join(
            evaluator.env.log_path if evaluator.env else 'running/eb_alfred',
            f"{args.model_name.split('/')[-1]}_baseline_memory_test",
            args.eval_set,
            'results'
        )
        print(f"\nBaseline results saved to: {baseline_results_path}")
        
        if args.mode == 'both':
            print("\n" + "=" * 60)
            print("Starting Failure Only Evaluation...")
            print("=" * 60)
            run_failure_only(baseline_results_path)
    
    elif args.mode == 'failure_only':
        if args.baseline_results_dir is None:
            print("Error: --baseline_results_dir is required for failure_only mode")
            print("Example: --baseline_results_dir running/eb_alfred/gpt-4o-mini_baseline_memory_test/common_sense/results")
            sys.exit(1)
        
        run_failure_only(args.baseline_results_dir)

