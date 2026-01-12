# startx.py 성공하게 하는 방법

## 문제 원인

`startx.py`가 실패하는 주요 원인:
1. **Xorg가 이미 실행 중**: display :1이 이미 사용 중
2. **권한 문제**: Xorg 실행 권한
3. **NVIDIA 드라이버 문제**: 코랩 환경에서 드라이버 접근 문제

## 해결 방법

### 방법 1: startx.py 수정 버전 (권장)

코랩 셀에서 실행:
```python
# 셀 2.5: startx.py 수정 버전 (코랩용)
import subprocess
import os
import sys
import time
import tempfile
import shlex
import re
from pathlib import Path

PROJECT_ROOT = Path('/content/drive/MyDrive/2025_EmbodiedBench2')
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

def pci_records():
    """NVIDIA GPU 찾기"""
    try:
        command = shlex.split('lspci -vmm')
        output = subprocess.check_output(command).decode()
        records = []
        for devices in output.strip().split("\n\n"):
            record = {}
            records.append(record)
            for row in devices.split("\n"):
                if '\t' in row:
                    key, value = row.split("\t", 1)
                    record[key.split(':')[0]] = value
        return records
    except Exception as e:
        print(f"Error getting PCI records: {e}")
        return []

def generate_xorg_conf(devices):
    """Xorg 설정 파일 생성"""
    xorg_conf = []
    device_section = """
Section "Device"
    Identifier     "Device{device_id}"
    Driver         "nvidia"
    VendorName     "NVIDIA Corporation"
    BusID          "{bus_id}"
EndSection
"""
    server_layout_section = """
Section "ServerLayout"
    Identifier     "Layout0"
    {screen_records}
EndSection
"""
    screen_section = """
Section "Screen"
    Identifier     "Screen{screen_id}"
    Device         "Device{device_id}"
    DefaultDepth    24
    Option         "AllowEmptyInitialConfiguration" "True"
    SubSection     "Display"
        Depth       24
        Virtual 1024 768
    EndSubSection
EndSection
"""
    screen_records = []
    for i, bus_id in enumerate(devices):
        xorg_conf.append(device_section.format(device_id=i, bus_id=bus_id))
        xorg_conf.append(screen_section.format(device_id=i, screen_id=i))
        screen_records.append('Screen {screen_id} "Screen{screen_id}" 0 0'.format(screen_id=i))
    
    xorg_conf.append(server_layout_section.format(screen_records="\n    ".join(screen_records)))
    return "\n".join(xorg_conf)

def startx_colab(display=1):
    """코랩용 startx (수정 버전)"""
    print(f"Starting X server on display :{display}...")
    
    # 1. NVIDIA GPU 찾기
    devices = []
    for r in pci_records():
        if r.get('Vendor', '') == 'NVIDIA Corporation' \
                and r.get('Class', '') in ['VGA compatible controller', '3D controller']:
            slot = r.get('Slot', '')
            if slot:
                try:
                    bus_id = 'PCI:' + ':'.join(map(lambda x: str(int(x, 16)), re.split(r'[:\.]', slot)))
                    devices.append(bus_id)
                    print(f"Found NVIDIA GPU: {bus_id}")
                except:
                    pass
    
    if not devices:
        raise Exception("No NVIDIA GPU found")
    
    # 2. 기존 X 서버 종료 (필요시)
    try:
        subprocess.run(['pkill', '-f', f'Xorg.*:{display}'], 
                      capture_output=True, timeout=2)
        time.sleep(1)
    except:
        pass
    
    # 3. Xorg 설정 파일 생성
    xorg_conf = generate_xorg_conf(devices)
    fd, path = tempfile.mkstemp(suffix='.conf', dir='/tmp')
    try:
        with open(path, 'w') as f:
            f.write(xorg_conf)
        
        # 4. Xorg 실행 (백그라운드)
        command = shlex.split(
            f"Xorg -noreset +extension GLX +extension RANDR +extension RENDER "
            f"-config {path} :{display}"
        )
        
        print(f"Starting Xorg with config: {path}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        # X 서버 시작 대기
        time.sleep(3)
        
        # 확인
        try:
            result = subprocess.run(['xdpyinfo', '-display', f':{display}'], 
                                  capture_output=True, timeout=2)
            if result.returncode == 0:
                os.environ['DISPLAY'] = f':{display}'
                print(f"✅ X server started successfully on :{display}")
                return True
            else:
                raise Exception("X server not responding")
        except:
            # 에러 확인
            stdout, stderr = process.communicate(timeout=1)
            if stderr:
                print(f"Xorg error: {stderr.decode()[:300]}")
            raise Exception("X server failed to start")
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except:
            pass

# 실행
try:
    if startx_colab(1):
        print(f"✅ DISPLAY: {os.environ.get('DISPLAY')}")
    else:
        raise Exception("Failed")
except Exception as e:
    print(f"❌ startx.py failed: {e}")
    print("Falling back to Xvfb...")
    # Xvfb fallback
    try:
        subprocess.run(['apt-get', 'update', '-qq'], check=True)
        subprocess.run(['apt-get', 'install', '-y', '-qq', 'xvfb'], check=True)
        subprocess.Popen(['Xvfb', ':1', '-screen', '0', '1024x768x24'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        os.environ['DISPLAY'] = ':1'
        print("✅ Xvfb started (fallback)")
    except Exception as e2:
        print(f"❌ Xvfb also failed: {e2}")
```

### 방법 2: 기존 X 서버 종료 후 재시작

```python
# 기존 X 서버 종료
import subprocess
subprocess.run(['pkill', '-f', 'Xorg'], capture_output=True)
subprocess.run(['pkill', '-f', 'Xvfb'], capture_output=True)
time.sleep(2)

# 그 다음 startx.py 실행
```

### 방법 3: 직접 Xorg 실행 (startx.py 우회)

```python
# startx.py 없이 직접 Xorg 실행
import subprocess
import tempfile
import os

# NVIDIA GPU BusID 찾기
result = subprocess.run(['nvidia-smi', '--query-gpu=pci.bus_id', '--format=csv,noheader'], 
                       capture_output=True, text=True)
bus_ids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

if bus_ids:
    # Xorg 설정 생성
    config = f"""
Section "Device"
    Identifier "Device0"
    Driver "nvidia"
    BusID "{bus_ids[0]}"
EndSection
Section "Screen"
    Identifier "Screen0"
    Device "Device0"
    DefaultDepth 24
    Option "AllowEmptyInitialConfiguration" "True"
EndSection
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config)
        config_path = f.name
    
    # Xorg 실행
    process = subprocess.Popen(
        ['Xorg', '-noreset', '+extension', 'GLX', '+extension', 'RANDR', 
         '+extension', 'RENDER', '-config', config_path, ':1'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(3)
    os.environ['DISPLAY'] = ':1'
    print(f"✅ Xorg started on :1")
else:
    print("No NVIDIA GPU found")
```

## 추천 방법

**방법 1 (수정된 startx.py)**을 사용하세요. 코랩 환경에 맞게 수정되었습니다.


