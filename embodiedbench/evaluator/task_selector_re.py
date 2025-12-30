"""
Task selection utility for limiting tasks per variation
"""
import random
from collections import defaultdict


def select_tasks_per_variation(dataset, tasks_per_variation=10, seed=None):
    """
    Task variation별로 지정된 개수만큼 선택
    
    Args:
        dataset: EBManEnv의 dataset 리스트
                 각 요소는 (task_to_use, task_base, waypoint_sets, config, task_file)
                 task_file이 task_variation (예: "pick_cube_shape")
        tasks_per_variation: 각 variation당 선택할 task 개수 (기본 10개)
        seed: 랜덤 시드 (재현성을 위해)
    
    Returns:
        selected_indexes: 선택된 인덱스 리스트
        variation_mapping: {task_variation: [indexes]} 매핑 (참고용)
    """
    if seed is not None:
        random.seed(seed)
    
    # Task variation별로 그룹화
    variation_to_indices = defaultdict(list)
    for idx, item in enumerate(dataset):
        task_variation = item[-1]  # task_file이 마지막 요소
        variation_to_indices[task_variation].append(idx)
    
    selected_indexes = []
    variation_mapping = {}
    
    # 각 variation별로 tasks_per_variation개씩 선택
    for task_variation, indices in variation_to_indices.items():
        # 이미 tasks_per_variation개 이하면 모두 선택
        if len(indices) <= tasks_per_variation:
            selected = indices
        else:
            # 랜덤하게 tasks_per_variation개 선택
            selected = random.sample(indices, tasks_per_variation)
        
        selected_indexes.extend(selected)
        variation_mapping[task_variation] = sorted(selected)
    
    # 인덱스를 정렬하여 반환 (원래 순서 유지)
    selected_indexes = sorted(selected_indexes)
    
    return selected_indexes, variation_mapping


def select_tasks_per_task_type_alfred(dataset, data_path=None, tasks_per_task_type=5, seed=None):
    """
    ALFRED task_type별로 지정된 개수만큼 선택
    
    Args:
        dataset: ALFRED dataset 리스트 (task dict 리스트)
        data_path: ALFRED 데이터 경로 (task JSON 파일 로드용, 사용하지 않음 - 하위 호환성)
        tasks_per_task_type: 각 task_type당 선택할 task 개수 (기본 5개)
        seed: 랜덤 시드 (재현성을 위해)
    
    Returns:
        selected_indexes: 선택된 인덱스 리스트
        task_type_mapping: {task_type: [indexes]} 매핑 (참고용)
    """
    if seed is not None:
        random.seed(seed)
    
    # task_type별로 그룹화
    from embodiedbench.envs.eb_alfred import utils
    task_type_to_indices = defaultdict(list)
    
    for idx, task in enumerate(dataset):
        try:
            # task JSON 파일에서 task_type 로드
            traj_data = utils.load_task_json(task)
            task_type = traj_data.get('task_type', '')
            if task_type:
                task_type_to_indices[task_type].append(idx)
        except Exception as e:
            # task_type을 가져올 수 없으면 스킵
            continue
    
    selected_indexes = []
    task_type_mapping = {}
    
    # 각 task_type별로 tasks_per_task_type개씩 선택
    for task_type, indices in task_type_to_indices.items():
        # 이미 tasks_per_task_type개 이하면 모두 선택
        if len(indices) <= tasks_per_task_type:
            selected = indices
        else:
            # 랜덤하게 tasks_per_task_type개 선택
            selected = random.sample(indices, tasks_per_task_type)
        
        selected_indexes.extend(selected)
        task_type_mapping[task_type] = sorted(selected)
    
    # 인덱스를 정렬하여 반환 (원래 순서 유지)
    selected_indexes = sorted(selected_indexes)
    
    return selected_indexes, task_type_mapping

