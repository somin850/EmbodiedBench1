"""
Memory utilities for loading and creating dynamic memory from episode results
"""
import os
import json
import re
from collections import defaultdict


def load_episode_results(results_dir):
    """
    결과 디렉토리에서 모든 episode 결과 로드
    
    Args:
        results_dir: 결과 디렉토리 경로 (예: "running/.../results")
    
    Returns:
        {episode_num: {
            'instruction': str,
            'task_success': int (0 or 1),
            'task_variation': str,
            'planner_output': str (planner_output_episode_X.txt 내용),
            'episode_num': int
        }}
    """
    episode_results = {}
    
    if not os.path.exists(results_dir):
        return episode_results
    
    # episode_X_res[_suffix].json 파일들 찾기 (suffix는 _baseline, _failure_only 등)
    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith('episode_') and '_res' in filename and filename.endswith('.json'):
            try:
                # episode_X_res[_suffix].json 형식 파싱
                parts = filename.replace('.json', '').split('_res')
                episode_num = int(parts[0].split('_')[1])
                suffix = parts[1] if len(parts) > 1 else ''  # _baseline, _failure_only 등
                
                file_path = os.path.join(results_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # planner_output 파일 읽기 (같은 suffix 사용)
                planner_output_filename = f'planner_output_episode_{episode_num}{suffix}.txt'
                planner_output_path = os.path.join(results_dir, planner_output_filename)
                planner_output = ""
                if os.path.exists(planner_output_path):
                    with open(planner_output_path, 'r', encoding='utf-8') as f:
                        planner_output = f.read()
                else:
                    # suffix 없는 파일도 시도 (하위 호환성)
                    planner_output_path_fallback = os.path.join(
                        results_dir, 
                        f'planner_output_episode_{episode_num}.txt'
                    )
                    if os.path.exists(planner_output_path_fallback):
                        with open(planner_output_path_fallback, 'r', encoding='utf-8') as f:
                            planner_output = f.read()
                
                # task_variation 추출 (episode_X_res.json에서 읽기)
                episode_results[episode_num] = {
                    'instruction': data.get('instruction', ''),
                    'task_success': int(data.get('task_success', 0)),
                    'task_variation': data.get('task_variation', ''),  # task_variation 추가
                    'planner_output': planner_output,
                    'episode_num': episode_num,
                    # 전체 궤적 분석을 위한 추가 정보
                    'reward': data.get('reward', []),  # 각 스텝의 reward
                    'action_success': data.get('action_success', []),  # 각 스텝의 action_success
                    'executed_actions': data.get('executed_actions', []),  # 각 스텝에서 실행된 액션
                    'step_task_success': data.get('step_task_success', []),  # 각 스텝의 task_success
                    'num_steps': data.get('num_steps', 0),  # 총 스텝 수
                    'planner_steps': data.get('planner_steps', 0)  # planner가 호출된 횟수
                }
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
    
    return episode_results


def get_tasks_by_variation(episode_results, task_variation, dataset_info=None):
    """
    특정 task variation의 task들만 필터링
    
    Args:
        episode_results: load_episode_results()의 결과
        task_variation: 필터링할 task variation (예: "pick_cube_shape")
        dataset_info: {episode_num: task_variation} 매핑 (선택적, 사용 안 함)
    
    Returns:
        필터링된 episode_results 리스트
    """
    filtered = []
    
    for episode_num, result in episode_results.items():
        # episode_results에서 직접 task_variation 확인
        result_task_variation = result.get('task_variation', '')
        if result_task_variation == task_variation:
            filtered.append(result)
    
    return filtered


def extract_example_from_planner_output(planner_output, instruction, avg_obj_coord=None, episode_result=None, is_success=True):
    """
    Planner output에서 예제 형식으로 변환
    LLM이 이해하기 쉽도록 간결하고 명확하게 구성
    
    Args:
        planner_output: planner_output_episode_X.txt의 내용 (JSON 문자열들)
        instruction: Human instruction
        avg_obj_coord: Input 좌표 (선택적)
        episode_result: 전체 에피소드 결과 (reward, action_success 등 포함)
        is_success: 성공 여부 (True/False) - 실패 시 더 자세한 정보 포함
    
    Returns:
        예제 문자열 (기존 예제 형식과 유사하되, 실패 시 추가 정보 포함)
    """
    lines = planner_output.strip().split('\n')
    if len(lines) == 0:
        return None
    
    try:
        # 예제 형식으로 변환
        example = f"""Human Instruction: {instruction}"""
        
        if avg_obj_coord:
            if isinstance(avg_obj_coord, dict):
                example += f"\nInput: {avg_obj_coord}"
            else:
                example += f"\nInput: {avg_obj_coord}"
        else:
            example += f"\nInput: {{}}"
        
        # 모든 스텝의 planner output 파싱
        all_steps = []
        for line in lines:
            if line.strip():
                try:
                    step_output = json.loads(line)
                    all_steps.append(step_output)
                except:
                    continue
        
        if len(all_steps) == 0:
            return None
        
        # 첫 번째 스텝의 정보 (기본 형식 - 기존 예제와 동일)
        first_output = all_steps[0]
        original_reasoning = first_output.get("reasoning_and_reflection", "")
        
        # 실패한 경우 reasoning에 실패 사실을 명시적으로 추가
        if not is_success:
            # 실패했다는 것을 명확히 표시 (유사한 task임을 명시)
            failure_notice = "[IMPORTANT: This is a FAILED example from a SIMILAR task type. **This is NOT the same task as your current task** - it is a similar but different task. You must:\n1. Analyze the failure_analysis section below to understand why this similar task failed\n2. Extract the root causes of the failure (e.g., incorrect reasoning, wrong action sequence, positioning errors, gripper state issues)\n3. Apply these lessons to your current task by avoiding the same mistakes\n4. Adapt the failure patterns to your current task's specific context\n\nThe reasoning below was the initial plan for that similar task, but it did not succeed. Use this as a reference to understand what went wrong and avoid making the same mistakes in your current task.]\n\n"
            modified_reasoning = failure_notice + original_reasoning
        else:
            modified_reasoning = original_reasoning
        
        output_dict = {
            "visual_state_description": first_output.get("visual_state_description", ""),
            "reasoning_and_reflection": modified_reasoning,
            "executable_plan": first_output.get("executable_plan", "")
        }
        
        # 실패한 경우에만 추가 정보 포함 (실패 원인 분석을 위해)
        if not is_success and episode_result:
            executed_actions = episode_result.get('executed_actions', [])
            step_task_success = episode_result.get('step_task_success', [])
            action_success_list = episode_result.get('action_success', [])
            
            # 실패 원인 분석을 위한 핵심 정보만 간결하게 추가
            failure_analysis = {
                "total_steps": len(executed_actions) if executed_actions else 0,
                "final_task_success": episode_result.get('task_success', 0),
                "note": "This task failed. Analyze the failed_steps below to understand what went wrong. Pay attention to the executed actions and their outcomes."
            }
            
            # 실패한 스텝이 있으면 추가
            failed_steps = []
            if executed_actions and step_task_success:
                for idx, (action, task_success) in enumerate(zip(executed_actions, step_task_success)):
                    if task_success == 0.0:  # task가 실패한 스텝
                        action_success = action_success_list[idx] if idx < len(action_success_list) else None
                        failed_steps.append({
                            "step": idx + 1,
                            "executed_action": action,
                            "action_success": action_success,  # 액션 자체가 성공했는지도 포함
                            "task_success": task_success  # task는 실패
                        })
                        if len(failed_steps) >= 3:  # 최대 3개까지만 (너무 길어지지 않도록)
                            break
            
            if failed_steps:
                failure_analysis["failed_steps"] = failed_steps
                # 실패 원인 추론을 위한 힌트 추가
                failure_analysis["analysis_hint"] = "**Failure Analysis Guide:**\n1. Check if actions were executed correctly but task still failed (indicates planning/coordination issue)\n2. Examine coordinate values - were Z positions appropriate? Was alignment correct?\n3. Review gripper state transitions - was it opened/closed at the right time?\n4. Verify object selection - was the correct object/color chosen?\n5. Compare with successful examples to identify what was different."
            
            # 마지막 planner step의 reasoning이 실패 원인을 포함할 수 있음
            if len(all_steps) > 1:
                last_reasoning = all_steps[-1].get("reasoning_and_reflection", "")
                if last_reasoning:
                    failure_analysis["final_reasoning"] = last_reasoning[:300]  # 200자에서 300자로 증가 (더 많은 정보)
            
            output_dict["failure_analysis"] = failure_analysis
        
        example += f"\nOutput: {json.dumps(output_dict, ensure_ascii=False, indent=4)}"
        
        return example
    except Exception as e:
        print(f"Error extracting example from planner output: {e}")
        return None


def create_memory_example(episode_result, is_success, avg_obj_coord=None):
    """
    에피소드 결과에서 메모리 예제 생성
    LLM이 이해하기 쉽도록 간결하고 명확하게 구성
    
    Args:
        episode_result: episode_X_res.json + planner_output 내용
        is_success: 성공 여부 (True/False)
        avg_obj_coord: Input 좌표 (선택적)
    
    Returns:
        예제 문자열 (기존 예제 형식과 유사, 실패 시 추가 정보 포함)
    """
    # Planner output에서 예제 추출
    example = extract_example_from_planner_output(
        episode_result['planner_output'],
        episode_result['instruction'],
        avg_obj_coord,
        episode_result,  # 전체 에피소드 결과 전달
        is_success  # 성공/실패 여부 전달
    )
    
    if example is None:
        return None
    
    # 성공/실패에 따라 프롬프트 앞에 설명 추가 (더 명확하게)
    if is_success:
        prefix = "=== SUCCESSFUL EXAMPLE ===\n**IMPORTANT**: This is a SUCCESSFUL example from a **similar task type** (NOT your exact task). Learn from its successful approach to complete your task.\n\n**Your task:**\n1. **Analyze the successful pattern** - Identify WHY this task succeeded (correct coordinate values? proper gripper state management? right action sequence? accurate object identification?)\n2. **Extract the success pattern** - What specific approach worked? (e.g., appropriate Z-coordinate, correct gripper timing, proper object selection)\n3. **Apply the lesson** - How can you adapt this successful approach to YOUR current task? Adapt the pattern to your specific situation.\n\n**Key success factors to learn from:**\n- **Coordinate precision**: Appropriate Z-positions, proper alignment with targets\n- **Gripper state management**: Opening/closing at correct time and position\n- **Action sequence**: Correct order of operations\n- **Object identification**: Accurate object/color selection\n\n**Key principle**: Don't copy actions blindly. Extract the success pattern and adapt it to achieve similar success in your task.\n\n"
    else:
        prefix = "=== FAILED EXAMPLE ===\n**IMPORTANT**: This is a FAILED example from a **similar task type** (NOT your exact task). Learn from its mistakes to avoid similar failures.\n\n**Your task:**\n1. **Analyze the failure_analysis section** - Identify WHY this task failed (coordinate errors? gripper state issues? wrong action sequence? object misidentification?)\n2. **Extract the failure pattern** - What specific mistake was made? (e.g., Z-coordinate too high, gripper opened too early, wrong object selected)\n3. **Apply the lesson** - How can you avoid this same mistake in YOUR current task? Adapt the lesson to your specific situation.\n\n**Common failure types to watch for:**\n- **Coordinate errors**: Z-position too high/low, misalignment with target\n- **Gripper state errors**: Opening/closing at wrong time or position\n- **Action sequence errors**: Wrong order of operations\n- **Object identification errors**: Selecting wrong object or color\n\n**Key principle**: Don't copy actions blindly. Extract the failure pattern and adapt it to prevent similar mistakes in your task.\n\n"
    
    return prefix + example


def calculate_instruction_similarity(current_instruction, other_instruction):
    """
    두 instruction 간의 유사도 계산 (키워드 기반)
    
    Args:
        current_instruction: 현재 task instruction
        other_instruction: 비교할 instruction
    
    Returns:
        유사도 점수 (0.0 ~ 1.0, 높을수록 유사)
    """
    if not current_instruction or not other_instruction:
        return 0.0
    
    # 소문자로 변환
    current = current_instruction.lower()
    other = other_instruction.lower()
    
    # 색상 키워드 추출
    colors = ["red", "maroon", "lime", "green", "blue", "navy", "yellow", "cyan", 
              "magenta", "silver", "gray", "olive", "purple", "teal", "azure", 
              "violet", "rose", "black", "white", "orange", "brown", "pink"]
    
    # 객체 타입 키워드 추출
    object_types = ["star", "cube", "cylinder", "prism", "container", "sorter", 
                    "box", "ball", "triangle", "rectangle", "circle", "square"]
    
    # 현재 instruction에서 키워드 추출
    current_keywords = set()
    for color in colors:
        if color in current:
            current_keywords.add(color)
    for obj_type in object_types:
        if obj_type in current:
            current_keywords.add(obj_type)
    
    # 비교 instruction에서 키워드 추출
    other_keywords = set()
    for color in colors:
        if color in other:
            other_keywords.add(color)
    for obj_type in object_types:
        if obj_type in other:
            other_keywords.add(obj_type)
    
    # 공통 키워드 개수 계산
    common_keywords = current_keywords & other_keywords
    total_keywords = current_keywords | other_keywords
    
    if len(total_keywords) == 0:
        return 0.0
    
    # Jaccard 유사도
    similarity = len(common_keywords) / len(total_keywords) if len(total_keywords) > 0 else 0.0
    
    # 공통 키워드가 많을수록 가중치 증가
    if len(common_keywords) > 0:
        similarity += len(common_keywords) * 0.1  # 추가 보너스
    
    return min(similarity, 1.0)


def load_memory_from_results(results_dir, task_variation, dataset_info=None, 
                             current_episode_num=None, max_success=3, max_failure=3):
    """
    이전 실행 결과에서 메모리 로드 (성공/실패 모두 로드, 유사도 계산 없이 순서대로 선택)
    
    Args:
        results_dir: 이전 실행 결과 디렉토리
        task_variation: 현재 task variation
        dataset_info: {episode_num: task_variation} 매핑 (선택적)
        current_episode_num: 현재 실행 중인 episode 번호 (자기 자신 제외를 위해, None이면 제외 안 함)
        max_success: 최대 성공 예제 개수 (기본 3개)
        max_failure: 최대 실패 예제 개수 (기본 3개)
    
    Returns:
        {
            'success_examples': [예제1, 예제2, ...],  # 최대 max_success개 (순서대로 선택)
            'failure_examples': [예제1, 예제2, ...]   # 최대 max_failure개 (순서대로 선택)
        }
    """
    # 결과 로드
    episode_results = load_episode_results(results_dir)
    
    # 같은 task variation 필터링
    variation_tasks = get_tasks_by_variation(
        episode_results, 
        task_variation, 
        dataset_info
    )
    
    # 자기 자신(같은 episode_num) 제외
    if current_episode_num is not None:
        variation_tasks = [
            task for task in variation_tasks 
            if task.get('episode_num') != current_episode_num
        ]
    
    success_examples = []
    failure_examples = []
    
    # 성공 예제 선택 (순서대로, 유사도 계산 없이)
    success_tasks = [task for task in variation_tasks if task['task_success'] == 1]
    for task in success_tasks[:max_success]:
        example = create_memory_example(task, is_success=True)
        if example:
            success_examples.append(example)
    
    # 실패 예제 선택 (순서대로, 유사도 계산 없이)
    failure_tasks = [task for task in variation_tasks if task['task_success'] == 0]
    for task in failure_tasks[:max_failure]:
        example = create_memory_example(task, is_success=False)
        if example:
            failure_examples.append(example)
    
    return {
        'success_examples': success_examples,
        'failure_examples': failure_examples
    }


def load_episode_results_alfred(results_dir):
    """
    ALFRED 결과 디렉토리에서 모든 episode 결과 로드
    
    Args:
        results_dir: 결과 디렉토리 경로 (예: "running/.../results")
    
    Returns:
        {episode_num: {
            'instruction': str,
            'task_success': int (0 or 1),
            'eval_set': str,
            'planner_output': str (planner_output_episode_X.txt 내용),
            'episode_num': int
        }}
    """
    episode_results = {}
    
    if not os.path.exists(results_dir):
        return episode_results
    
    # episode_X_final_res[_suffix].json 파일들 찾기
    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith('episode_') and '_final_res' in filename and filename.endswith('.json'):
            try:
                # episode_X_final_res[_suffix].json 형식 파싱
                parts = filename.replace('.json', '').split('_final_res')
                episode_num = int(parts[0].split('_')[1])
                suffix = parts[1] if len(parts) > 1 else ''  # _baseline, _failure_only 등
                
                file_path = os.path.join(results_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # planner_output 파일 읽기 (같은 suffix 사용)
                planner_output_filename = f'planner_output_episode_{episode_num}{suffix}.txt'
                planner_output_path = os.path.join(results_dir, planner_output_filename)
                planner_output = ""
                if os.path.exists(planner_output_path):
                    with open(planner_output_path, 'r', encoding='utf-8') as f:
                        planner_output = f.read()
                else:
                    # suffix 없는 파일도 시도 (하위 호환성)
                    planner_output_path_fallback = os.path.join(
                        results_dir, 
                        f'planner_output_episode_{episode_num}.txt'
                    )
                    if os.path.exists(planner_output_path_fallback):
                        with open(planner_output_path_fallback, 'r', encoding='utf-8') as f:
                            planner_output = f.read()
                
                episode_results[episode_num] = {
                    'instruction': data.get('instruction', ''),
                    'task_success': int(data.get('task_success', 0)),
                    'eval_set': data.get('eval_set', ''),  # eval_set 추가
                    'task_type': data.get('task_type', ''),  # task_type 추가 (카테고리별 메모리 로드를 위해)
                    'planner_output': planner_output,
                    'episode_num': episode_num,
                    # 전체 궤적 분석을 위한 추가 정보
                    'reward': data.get('reward', []),  # 각 스텝의 reward
                    'num_invalid_actions': data.get('num_invalid_actions', 0),
                    'num_steps': data.get('num_steps', 0),
                    'planner_steps': data.get('planner_steps', 0)
                }
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
    
    return episode_results


def get_tasks_by_eval_set(episode_results, eval_set):
    """
    특정 eval_set의 task들만 필터링
    
    Args:
        episode_results: load_episode_results_alfred()의 결과
        eval_set: 필터링할 eval_set (예: "common_sense")
    
    Returns:
        필터링된 episode_results 리스트
    """
    filtered = []
    
    for episode_num, result in episode_results.items():
        result_eval_set = result.get('eval_set', '')
        if result_eval_set == eval_set:
            filtered.append(result)
    
    return filtered


def get_tasks_by_task_type(episode_results, task_type):
    """
    특정 task_type의 task들만 필터링 (ALFRED 카테고리별 메모리 로드를 위해)
    
    Args:
        episode_results: episode_results 리스트 (get_tasks_by_eval_set의 결과)
        task_type: 필터링할 task_type (예: "pick_and_place_simple")
    
    Returns:
        필터링된 episode_results 리스트
    """
    filtered = []
    
    for result in episode_results:
        result_task_type = result.get('task_type', '')
        if result_task_type == task_type:
            filtered.append(result)
    
    return filtered


def extract_example_from_planner_output_alfred(planner_output, instruction, episode_result=None, is_success=True):
    """
    ALFRED Planner output에서 예제 형식으로 변환
    ALFRED는 JSON 형식의 reasoning을 사용
    
    Args:
        planner_output: planner_output_episode_X.txt의 내용 (JSON 문자열들)
        instruction: Human instruction
        episode_result: 전체 에피소드 결과
        is_success: 성공 여부 (True/False)
    
    Returns:
        예제 문자열
    """
    lines = planner_output.strip().split('\n')
    if len(lines) == 0:
        return None
    
    try:
        # 예제 형식으로 변환
        example = f"""Human Instruction: {instruction}"""
        
        # 모든 스텝의 planner output 파싱
        all_steps = []
        for line in lines:
            if line.strip():
                try:
                    step_output = json.loads(line)
                    all_steps.append(step_output)
                except:
                    continue
        
        if len(all_steps) == 0:
            return None
        
        # 첫 번째 스텝의 정보
        first_output = all_steps[0]
        original_reasoning = first_output.get("reasoning_and_reflection", "") or first_output.get("reasoning", "")
        
        # 실패한 경우 reasoning에 실패 사실을 명시적으로 추가
        if not is_success:
            failure_notice = "[IMPORTANT: This is a FAILED example from a SIMILAR task type. **This is NOT the same task as your current task** - it is a similar but different task. You must:\n1. Analyze the failure_analysis section below to understand why this similar task failed\n2. Extract the root causes of the failure\n3. Apply these lessons to your current task by avoiding the same mistakes\n4. Adapt the failure patterns to your current task's specific context\n\nThe reasoning below was the initial plan for that similar task, but it did not succeed. Use this as a reference to understand what went wrong and avoid making the same mistakes in your current task.]\n\n"
            modified_reasoning = failure_notice + original_reasoning
        else:
            modified_reasoning = original_reasoning
        
        output_dict = {
            "visual_state_description": first_output.get("visual_state_description", ""),
            "reasoning_and_reflection": modified_reasoning,
            "executable_plan": first_output.get("executable_plan", [])
        }
        
        # 실패한 경우에만 추가 정보 포함
        if not is_success and episode_result:
            failure_analysis = {
                "total_steps": episode_result.get('num_steps', 0),
                "num_invalid_actions": episode_result.get('num_invalid_actions', 0),
                "final_task_success": episode_result.get('task_success', 0),
                "note": "This task failed. Analyze why it failed and avoid similar mistakes."
            }
            
            # 마지막 planner step의 reasoning이 실패 원인을 포함할 수 있음
            if len(all_steps) > 1:
                last_reasoning = all_steps[-1].get("reasoning_and_reflection", "") or all_steps[-1].get("reasoning", "")
                if last_reasoning:
                    failure_analysis["final_reasoning"] = last_reasoning[:300]
            
            output_dict["failure_analysis"] = failure_analysis
        
        example += f"\nOutput: {json.dumps(output_dict, ensure_ascii=False, indent=4)}"
        
        return example
    except Exception as e:
        print(f"Error extracting example from planner output: {e}")
        return None


def create_memory_example_alfred(episode_result, is_success):
    """
    ALFRED 에피소드 결과에서 메모리 예제 생성
    
    Args:
        episode_result: episode_X_final_res.json + planner_output 내용
        is_success: 성공 여부 (True/False)
    
    Returns:
        예제 문자열
    """
    example = extract_example_from_planner_output_alfred(
        episode_result['planner_output'],
        episode_result['instruction'],
        episode_result,
        is_success
    )
    
    if example is None:
        return None
    
    # 성공/실패에 따라 프롬프트 앞에 설명 추가
    if is_success:
        prefix = "=== SUCCESSFUL EXAMPLE ===\n**IMPORTANT**: This is a SUCCESSFUL example from a **similar task type** (NOT your exact task). Learn from its successful approach to complete your task.\n\n**Your task:**\n1. **Analyze the successful pattern** - Identify WHY this task succeeded (correct action sequence? proper object handling? accurate navigation?)\n2. **Extract the success pattern** - What specific approach worked? (e.g., correct action order, proper object manipulation, efficient path planning)\n3. **Apply the lesson** - How can you adapt this successful approach to YOUR current task? Adapt the pattern to your specific situation.\n\n**Key success factors to learn from:**\n- **Action sequence**: Correct order of operations\n- **Object handling**: Proper manipulation and placement\n- **Navigation**: Efficient path planning\n- **Task understanding**: Accurate interpretation of instructions\n\n**Key principle**: Don't copy actions blindly. Extract the success pattern and adapt it to achieve similar success in your task.\n\n"
    else:
        prefix = "=== FAILED EXAMPLE ===\n**IMPORTANT**: This is a FAILED example from a **similar task type** (NOT your exact task). Learn from its mistakes to avoid similar failures.\n\n**Your task:**\n1. **Analyze the failure_analysis section** - Identify WHY this task failed (action sequence errors? object handling issues? navigation problems?)\n2. **Extract the failure pattern** - What specific mistake was made? (e.g., wrong action order, incorrect object manipulation, inefficient path)\n3. **Apply the lesson** - How can you avoid this same mistake in YOUR current task? Adapt the lesson to your specific situation.\n\n**Common failure types to watch for:**\n- **Action sequence errors**: Wrong order of operations\n- **Object handling errors**: Incorrect manipulation or placement\n- **Navigation errors**: Inefficient or incorrect path planning\n- **Task understanding errors**: Misinterpretation of instructions\n\n**Key principle**: Don't copy actions blindly. Extract the failure pattern and adapt it to prevent similar mistakes in your task.\n\n"
    
    return prefix + example


def load_memory_from_results_alfred(results_dir, eval_set, task_type=None,
                                     current_episode_num=None, max_success=3, max_failure=3):
    """
    ALFRED 이전 실행 결과에서 메모리 로드 (카테고리별로 필터링)
    
    Args:
        results_dir: 이전 실행 결과 디렉토리
        eval_set: 현재 eval_set
        task_type: 현재 task_type (카테고리별 메모리 로드를 위해, None이면 eval_set만 필터링)
        current_episode_num: 현재 실행 중인 episode 번호 (자기 자신 제외를 위해, None이면 제외 안 함)
        max_success: 최대 성공 예제 개수 (기본 3개)
        max_failure: 최대 실패 예제 개수 (기본 3개)
    
    Returns:
        {
            'success_examples': [예제1, 예제2, ...],  # 최대 max_success개
            'failure_examples': [예제1, 예제2, ...]   # 최대 max_failure개
        }
    """
    # 결과 로드
    episode_results = load_episode_results_alfred(results_dir)
    
    # 같은 eval_set 필터링
    eval_set_tasks = get_tasks_by_eval_set(episode_results, eval_set)
    
    # task_type이 제공된 경우 같은 task_type만 필터링 (카테고리별 메모리)
    if task_type is not None:
        eval_set_tasks = get_tasks_by_task_type(eval_set_tasks, task_type)
    
    # 자기 자신(같은 episode_num) 제외
    if current_episode_num is not None:
        eval_set_tasks = [
            task for task in eval_set_tasks 
            if task.get('episode_num') != current_episode_num
        ]
    
    success_examples = []
    failure_examples = []
    
    for task in eval_set_tasks:
        if task['task_success'] == 1 and len(success_examples) < max_success:
            example = create_memory_example_alfred(task, is_success=True)
            if example:
                success_examples.append(example)
        elif task['task_success'] == 0 and len(failure_examples) < max_failure:
            example = create_memory_example_alfred(task, is_success=False)
            if example:
                failure_examples.append(example)
    
    return {
        'success_examples': success_examples,
        'failure_examples': failure_examples
    }

