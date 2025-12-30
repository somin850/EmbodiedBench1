"""
실험 단계별 실행 스크립트

1. 기본 실행 (baseline, 10개씩)
2. 실패한 task 메모리에 저장 및 추가 입력 (10개씩)
3. 실패/성공 task 모두 추가 입력 (10개씩)
4. 성공 task 추가 입력 (10개씩)
"""
import subprocess
import os
import sys

def run_baseline():
    """기본 실행"""
    print("=" * 50)
    print("Step 1: Running baseline (10 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4o-mini",
        "exp_name=baseline_re",
        "tasks_per_variation=5",
        "memory_mode=baseline"
    ]
    subprocess.run(cmd)
    print("\nBaseline completed!\n")

def run_with_failure_memory(baseline_results_dir):
    """실패한 task만 메모리에 추가"""
    print("=" * 50)
    print("Step 2: Running with failure memory only (10 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4o-mini",
        "exp_name=failure_memory_re",
        "tasks_per_variation=5",
        "memory_mode=failure_only",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd)
    print("\nFailure memory experiment completed!\n")

def run_with_all_memory(baseline_results_dir):
    """성공/실패 모두 메모리에 추가"""
    print("=" * 50)
    print("Step 3: Running with success and failure memory (10 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4o-mini",
        "exp_name=all_memory_re",
        "tasks_per_variation=5",
        "memory_mode=success_and_failure",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd)
    print("\nAll memory experiment completed!\n")

def run_with_success_memory(baseline_results_dir):
    """성공한 task만 메모리에 추가"""
    print("=" * 50)
    print("Step 4: Running with success memory only (10 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4o-mini",
        "exp_name=success_memory_re",
        "tasks_per_variation=5",
        "memory_mode=success_only",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd)
    print("\nSuccess memory experiment completed!\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 커맨드라인 인자로 특정 단계만 실행
        step = sys.argv[1]
        baseline_results_dir = sys.argv[2] if len(sys.argv) > 2 else "running/eb_manipulation/gpt-4o-mini/baseline_re/base/results"
        
        if step == "1":
            run_baseline()
        elif step == "2":
            run_with_failure_memory(baseline_results_dir)
        elif step == "3":
            run_with_all_memory(baseline_results_dir)
        elif step == "4":
            run_with_success_memory(baseline_results_dir)
        else:
            print("Usage: python memory_experiment_re.py [1|2|3|4] [baseline_results_dir]")
    else:
        # 전체 실행
        # 1. 기본 실행
        run_baseline()
        baseline_results_dir = "running/eb_manipulation/gpt-4o-mini/baseline_re/base/results"
        
        # 2. 실패한 task만 메모리에 추가
        run_with_failure_memory(baseline_results_dir)
        
        # 3. 성공/실패 모두 메모리에 추가
        run_with_all_memory(baseline_results_dir)
        
        # 4. 성공한 task만 메모리에 추가
        run_with_success_memory(baseline_results_dir)
        
        print("=" * 50)
        print("All experiments completed!")
        print("=" * 50)

