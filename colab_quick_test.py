#!/usr/bin/env python3
"""
코랩에서 Unity 통신 문제 빠른 테스트
"""
import subprocess
import os
import time
import sys

def setup_xvfb_tcp():
    """TCP 모드로 Xvfb 시작"""
    print("=" * 60)
    print("Step 1: Xvfb 설정 (TCP 모드)")
    print("=" * 60)
    
    # 기존 프로세스 정리
    subprocess.run(['pkill', '-9', 'Xvfb'], stderr=subprocess.DEVNULL)
    subprocess.run(['pkill', '-9', 'thor'], stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # /tmp 디렉토리 권한 확인
    os.makedirs('/tmp/.X11-unix', mode=0o1777, exist_ok=True)
    
    # Xvfb 시작 (TCP 리스닝)
    xvfb_proc = subprocess.Popen([
        'Xvfb', ':1',
        '-screen', '0', '1024x768x24',
        '-ac',
        '+extension', 'GLX',
        '-listen', 'tcp'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(3)
    
    # 확인
    if xvfb_proc.poll() is None:
        print(f"✓ Xvfb started (PID: {xvfb_proc.pid})")
    else:
        stderr = xvfb_proc.stderr.read().decode()
        print(f"❌ Xvfb failed:")
        print(stderr)
        return False
    
    os.environ['DISPLAY'] = ':1'
    print(f"✓ DISPLAY set to :1")
    return True

def test_thor_env():
    """ThorEnv 생성 및 reset 테스트"""
    print("\n" + "=" * 60)
    print("Step 2: ThorEnv 테스트")
    print("=" * 60)
    
    try:
        from embodiedbench.envs.eb_alfred.env.thor_env import ThorEnv
        
        print("ThorEnv 생성 중...")
        env = ThorEnv()
        
        if env.server is None:
            print("❌ Unity 서버 초기화 실패")
            return False
        
        print(f"✓ ThorEnv 생성 성공 (server: {env.server is not None})")
        
        print("\nReset 테스트 중...")
        event = env.reset('FloorPlan1')
        
        if event is None:
            print("❌ Reset 실패 (event is None)")
            return False
        
        print(f"✓ Reset 성공!")
        print(f"  - Event type: {type(event)}")
        print(f"  - Has frame: {hasattr(event, 'frame') and event.frame is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ 에러 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_unity_processes():
    """Unity 프로세스 상태 확인"""
    print("\n" + "=" * 60)
    print("Unity 프로세스 상태")
    print("=" * 60)
    
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True
    )
    
    thor_procs = [line for line in result.stdout.split('\n') if 'thor' in line.lower() and 'grep' not in line]
    
    if thor_procs:
        print(f"발견된 Unity 프로세스: {len(thor_procs)}개")
        for proc in thor_procs[:3]:  # 최대 3개만 표시
            print(f"  {proc}")
    else:
        print("Unity 프로세스 없음")

def main():
    print("코랩 Unity 통신 문제 진단 스크립트")
    print("=" * 60)
    
    # Step 1: Xvfb 설정
    if not setup_xvfb_tcp():
        print("\n❌ Xvfb 설정 실패")
        sys.exit(1)
    
    # Step 2: ThorEnv 테스트
    success = test_thor_env()
    
    # Step 3: 프로세스 상태 확인
    check_unity_processes()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 모든 테스트 통과!")
        print("이제 전체 evaluation을 실행할 수 있습니다:")
        print("  python run_baseline.py")
    else:
        print("❌ 테스트 실패")
        print("\n해결 방안:")
        print("1. AI2-THOR 버전 업그레이드:")
        print("   pip install ai2thor==4.3.0")
        print("2. 또는 로컬 빌드 경로 지정")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())


