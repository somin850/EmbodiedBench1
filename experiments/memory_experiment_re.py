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
import time

def setup_environment():
    """환경 변수 및 Xvfb 설정"""
    # 환경 변수 설정
    coppeliasim_root = os.environ.get('COPPELIASIM_ROOT', '/home/somin/CoppeliaSim')
    os.environ['COPPELIASIM_ROOT'] = coppeliasim_root
    os.environ['LD_LIBRARY_PATH'] = f'/usr/lib/x86_64-linux-gnu:{coppeliasim_root}:{os.environ.get("LD_LIBRARY_PATH", "")}'
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = coppeliasim_root
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    # OpenAI API 키 설정 (항상 업데이트)
    # 여기에 추가 
    old_key = os.environ.get('OPENAI_API_KEY', '')
    os.environ['OPENAI_API_KEY'] = default_key
    if old_key:
        print(f"✓ OPENAI_API_KEY updated (old length: {len(old_key)}, new length: {len(default_key)})")
    else:
        print(f"✓ OPENAI_API_KEY set (length: {len(default_key)})")
    
    # 기존 Xvfb 프로세스 종료
    subprocess.run(['pkill', '-f', 'Xvfb :1'], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    # Xvfb 시작
    xvfb_proc = subprocess.Popen(
        ['Xvfb', ':1', '-screen', '0', '1024x768x24'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    if xvfb_proc.poll() is None:
        os.environ['DISPLAY'] = ':1'
        print(f"✓ Xvfb started (PID: {xvfb_proc.pid})")
        print(f"✓ DISPLAY set to :1")
        return xvfb_proc
    else:
        print("✗ Xvfb failed to start")
        return None

def run_baseline():
    """기본 실행"""
    print("=" * 50)
    print("Step 1: Running baseline (6 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4.1",
        "exp_name=version2",
        "tasks_per_variation=6",
        "task_selection_seed=42",
        "memory_mode=baseline",
        "eval_sets=[base]"
    ]
    subprocess.run(cmd, env=os.environ.copy())
    print("\nBaseline completed!\n")

def run_with_failure_memory(baseline_results_dir):
    """실패한 task만 메모리에 추가"""
    print("=" * 50)
    print("Step 2: Running with failure memory only (6 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4.1",
        "exp_name=version2",
        "tasks_per_variation=6",
        "task_selection_seed=42",
        "memory_mode=failure_only",
        "eval_sets=[base]",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd, env=os.environ.copy())
    print("\nFailure memory experiment completed!\n")

def run_with_all_memory(baseline_results_dir):
    """성공/실패 모두 메모리에 추가"""
    print("=" * 50)
    print("Step 3: Running with success and failure memory (6 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4.1",
        "exp_name=version3",
        "tasks_per_variation=6",
        "task_selection_seed=42",
        "memory_mode=success_and_failure",
        "eval_sets=[base]",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd, env=os.environ.copy())
    print("\nAll memory experiment completed!\n")

def run_with_success_memory(baseline_results_dir):
    """성공한 task만 메모리에 추가"""
    print("=" * 50)
    print("Step 4: Running with success memory only (5 tasks per variation)")
    print("=" * 50)
    cmd = [
        "python", "-m", "embodiedbench.main",
        "env=eb-man",
        "model_name=gpt-4.1",
        "exp_name=4_re",
        "tasks_per_variation=5",
        "task_selection_seed=42",
        "memory_mode=success_only",
        f"previous_results_dir={baseline_results_dir}"
    ]
    subprocess.run(cmd, env=os.environ.copy())
    print("\nSuccess memory experiment completed!\n")

if __name__ == "__main__":
    # 환경 설정
    xvfb_proc = setup_environment()
    if xvfb_proc is None:
        print("Failed to setup environment. Exiting.")
        sys.exit(1)
    
    try:
        if len(sys.argv) > 1:
            # 커맨드라인 인자로 특정 단계만 실행
            step = sys.argv[1]
            baseline_results_dir = sys.argv[2] if len(sys.argv) > 2 else "running/eb_manipulation/gpt-4.1/baselineversion2/base/results"
            
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
            # 전체 실행 (baseline + failure_only만)
            # 1. 기본 실행
            run_baseline()
            baseline_results_dir = "running/eb_manipulation/gpt-4.1/baselineversion2/base/results"
            
            # 2. 실패한 task만 메모리에 추가
            run_with_failure_memory(baseline_results_dir)
            
            print("=" * 50)
            print("All experiments completed!")
            print("=" * 50)
    finally:
        # Xvfb 종료
        if xvfb_proc:
            xvfb_proc.terminate()
            xvfb_proc.wait()

