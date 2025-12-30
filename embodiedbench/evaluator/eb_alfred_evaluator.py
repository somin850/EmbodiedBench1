import os
import numpy as np
import random
from tqdm import tqdm
import time
import json
from embodiedbench.envs.eb_alfred.EBAlfEnv import EBAlfEnv, ValidEvalSets
from embodiedbench.planner.vlm_planner import VLMPlanner
from embodiedbench.evaluator.summarize_result import average_json_values
from embodiedbench.evaluator.evaluator_utils import load_saved_data, update_config_with_args
from embodiedbench.evaluator.config.system_prompts import alfred_system_prompt
from embodiedbench.main import logger

example_path = os.path.join(os.path.dirname(__file__), 'config/alfred_examples.json')
exploration_example_path = os.path.join(os.path.dirname(__file__), 'config/alfred_long_horizon_examples.json')
system_prompt = alfred_system_prompt

class EB_AlfredEvaluator():
    def __init__(self, config):
        self.model_name = config['model_name']
        self.eval_set = ValidEvalSets[0]
        self.config = config
        self.env = None
        self.planner = None
        self.memory_mode = config.get('memory_mode', 'baseline')  
        # 'baseline', 'failure_only', 'success_and_failure', 'success_only'
        self.previous_results_dir = config.get('previous_results_dir', None)
        
        # 실험 구분자 설정 (파일명에 사용) - memory_mode 이름 그대로 사용
        self.exp_suffix = f'_{self.memory_mode}' if self.memory_mode != 'baseline' else ''
        
        # 시드 고정 (재현성을 위해)
        self.seed = config.get('seed', 42)
        random.seed(self.seed)
        np.random.seed(self.seed)
        try:
            import torch
            torch.manual_seed(self.seed)
        except:
            pass

    def check_config_valid(self):
        if self.config['multistep'] + self.config['chat_history'] > 1:
            raise ValueError("Only one of multistep, chat_history can be enabled at a time.")
        
        if self.config['language_only']:
            if self.config['multistep']:
                logger.warning("Language only mode should not have multistep enabled. Setting these arguments to False ...")
                self.config['multistep'] = 0
        
    def save_episode_metric(self, episode_info):
        episode_idx = self.env._current_episode_num if not len(self.env.selected_indexes) else self.env.selected_indexes[self.env._current_episode_num - 1] + 1
        filename = 'episode_{}_final_res{}.json'.format(episode_idx, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            json.dump(episode_info, f, ensure_ascii=False, indent=2)
    
    def save_planner_outputs(self, reasoning_list):
        episode_idx = self.env._current_episode_num if not len(self.env.selected_indexes) else self.env.selected_indexes[self.env._current_episode_num - 1] + 1
        filename = 'planner_output_episode_{}{}.txt'.format(episode_idx, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            for s in reasoning_list:
                f.write(s + "\n")
    
    def save_prompts(self, prompts_list):
        """실제 입력된 프롬프트 저장"""
        episode_idx = self.env._current_episode_num if not len(self.env.selected_indexes) else self.env.selected_indexes[self.env._current_episode_num - 1] + 1
        filename = 'prompts_episode_{}{}.txt'.format(episode_idx, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            for i, prompt in enumerate(prompts_list):
                f.write(f"=== Step {i} ===\n")
                f.write(prompt)
                f.write("\n\n")
    
    def save_memory_info(self):
        """사용된 메모리 정보 저장"""
        episode_idx = self.env._current_episode_num if not len(self.env.selected_indexes) else self.env.selected_indexes[self.env._current_episode_num - 1] + 1
        filename = 'memory_info_episode_{}{}.json'.format(episode_idx, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        
        # 현재 episode의 task_type 가져오기
        current_task_type = ''
        if hasattr(self.env, 'episode_data') and self.env.episode_data is not None:
            current_task_type = self.env.episode_data.get('task_type', '')
        
        # task_type별 메모리 키
        memory_key = f"{self.eval_set}_{current_task_type}" if current_task_type else self.eval_set
        
        memory_info = {
            'eval_set': self.eval_set,
            'task_type': current_task_type,
            'memory_mode': self.memory_mode,
            'previous_results_dir': self.previous_results_dir,
            'used_memory': {
                'success_examples': self.planner.dynamic_success_examples.get(memory_key, []),
                'failure_examples': self.planner.dynamic_failure_examples.get(memory_key, [])
            },
            'num_success_examples': len(self.planner.dynamic_success_examples.get(memory_key, [])),
            'num_failure_examples': len(self.planner.dynamic_failure_examples.get(memory_key, []))
        }
        
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            json.dump(memory_info, f, ensure_ascii=False, indent=2)
    
    def load_dynamic_memory(self, eval_set, task_type=None):
        """이전 실행 결과에서 동적 메모리 로드 (base eval_set은 제외, task_type별로 카테고리화)"""
        if self.previous_results_dir is None or self.memory_mode == 'baseline' or eval_set == 'base':
            return [], []
        
        from embodiedbench.evaluator.memory_utils_re import load_memory_from_results_alfred
        
        memory = load_memory_from_results_alfred(
            self.previous_results_dir, 
            eval_set,
            task_type=task_type,  # task_type별로 필터링
            max_success=3,
            max_failure=3
        )
        
        if self.memory_mode == 'failure_only':
            return [], memory['failure_examples']
        elif self.memory_mode == 'success_and_failure':
            return memory['success_examples'], memory['failure_examples']
        elif self.memory_mode == 'success_only':
            return memory['success_examples'], []
        else:
            return [], []

    def evaluate_main(self):
        valid_eval_sets = self.config.get('eval_sets', ValidEvalSets)
        valid_eval_sets = list(valid_eval_sets)
        if type(valid_eval_sets) == list and len(valid_eval_sets) == 0:
            valid_eval_sets = ValidEvalSets

        for eval_set in valid_eval_sets:
            if self.env is not None:
                self.env.close()
            self.eval_set = eval_set
            logger.info(f'Current eval set: {eval_set}')
            
            # 각 eval_set별로 시드 재설정 (재현성 보장)
            random.seed(self.seed)
            np.random.seed(self.seed)
            try:
                import torch
                torch.manual_seed(self.seed)
            except:
                pass
            
            exp_name = f"{self.model_name.split('/')[-1]}_{self.config['exp_name']}/{eval_set}" if len(self.config['exp_name']) else f"{self.model_name.split('/')[-1]}/{eval_set}"
            task_selection_seed = self.config.get('task_selection_seed')
            if task_selection_seed is None:
                task_selection_seed = self.seed
            
            self.env = EBAlfEnv(eval_set=self.eval_set, down_sample_ratio=self.config['down_sample_ratio'], 
                                          exp_name=exp_name, selected_indexes=self.config.get('selected_indexes', []), 
                                          detection_box=self.config.get('detection_box', False),
                                          resolution=self.config.get('resolution', 500),
                                          tasks_per_task_type=self.config.get('tasks_per_task_type', None),
                                          task_selection_seed=task_selection_seed
                                          )
            examples = json.load(open(example_path, 'r+')) if self.eval_set != 'long_horizon' else json.load(open(exploration_example_path, 'r+'))
            model_type = self.config.get('model_type', 'remote')
            self.planner = VLMPlanner(self.model_name, model_type, self.env.language_skill_set, system_prompt, examples, n_shot=self.config['n_shots'], 
                                            obs_key='head_rgb', chat_history=self.config['chat_history'], language_only=self.config['language_only'],
                                            use_feedback=self.config.get('env_feedback', True), multistep=self.config.get('multistep', 0), tp=self.config.get('tp', 1))

            # 동적 메모리 추가 (base eval_set은 제외, task_type별로 카테고리화)
            if self.memory_mode != 'baseline' and self.eval_set != 'base':
                # ALFRED의 모든 task_type에 대해 메모리 로드
                task_types = ['pick_and_place_simple', 'pick_clean_then_place_in_recep', 'pick_heat_then_place_in_recep',
                             'pick_cool_then_place_in_recep', 'pick_two_obj_and_place', 'look_at_obj_in_light',
                             'pick_and_place_with_movable_recep']
                
                for task_type in task_types:
                    success_memory, failure_memory = self.load_dynamic_memory(self.eval_set, task_type)
                    if len(success_memory) > 0 or len(failure_memory) > 0:
                        # task_type을 key로 사용 (eval_set과 task_type 조합)
                        memory_key = f"{self.eval_set}_{task_type}"
                        self.planner.add_dynamic_memory(memory_key, success_memory, failure_memory)
                        logger.info(f"[EB_AlfredEvaluator] Loaded memory for eval_set={self.eval_set}, task_type={task_type}: success={len(success_memory)}, failure={len(failure_memory)}")

            self.evaluate()
            average_json_values(os.path.join(self.env.log_path, 'results'), output_file='summary.json')
            with open(os.path.join(self.env.log_path, 'config.txt'), 'w') as f:
                f.write(str(self.config))

    def evaluate(self):
        progress_bar = tqdm(total=self.env.number_of_episodes, desc="Episodes")
        while self.env._current_episode_num < self.env.number_of_episodes:
            logger.info(f"Evaluating episode {self.env._current_episode_num} ...")
            episode_info = {'reward': [], 'num_invalid_actions': 0, 'empty_plan': 0}
            obs = self.env.reset()
            img_path = self.env.save_image(obs)
            user_instruction = self.env.episode_language_instruction
            print(f"Instruction: {user_instruction}")
            
            # 현재 episode의 task_type 가져오기 (카테고리별 메모리 사용을 위해)
            current_task_type = ''
            if hasattr(self.env, 'episode_data') and self.env.episode_data is not None:
                current_task_type = self.env.episode_data.get('task_type', '')

            self.planner.reset()
            # update the action space for alfred due to dynamic objects
            self.planner.set_actions(self.env.language_skill_set)
            done = False
            reasoning_list = []
            prompts_list = []  # 프롬프트 저장용
            while not done:
                try: 
                    action, reasoning = self.planner.act(img_path, user_instruction, eval_set=self.eval_set, task_type=current_task_type)
                    print(f"Planner Output Action: {action}")
                    reasoning_list.append(reasoning)
                    # 프롬프트 저장
                    if self.planner.last_prompt:
                        prompts_list.append(self.planner.last_prompt)
                    if action == -2: # empty plan stop here
                        episode_info['empty_plan'] = 1
                        self.env.episode_log.append({
                            'last_action_success': 0.0,
                            'action_id': -2,
                            'action_description': 'empty plan',
                            'reasoning': reasoning,
                        })
                        info = {
                            'task_success': episode_info.get('task_success', 0),
                            'task_progress': episode_info.get("task_progress", 0),
                            'env_step': self.env._current_step,
                        }
                        break 
                    if action == -1:
                        self.env._cur_invalid_actions += 1
                        episode_info['reward'].append(-1)
                        episode_info['num_invalid_actions'] += 1
                        self.env.episode_log.append({
                            'last_action_success': 0.0,
                            'action_id': -1,
                            'action_description': 'invalid action',
                            'reasoning': reasoning,
                        })
                        info = {
                            'task_success': episode_info.get('task_success', 0),
                            'task_progress': episode_info.get("task_progress", 0),
                            'env_step': self.env._current_step,
                        }
                        if self.env._cur_invalid_actions >= self.env._max_invalid_actions:
                            break
                        continue
                    
                    # mutiple actions
                    if type(action) == list:
                        for action_single in action[:min(self.env._max_episode_steps - self.env._current_step, len(action))]:
                            obs, reward, done, info = self.env.step(action_single, reasoning=reasoning)
                            action_str = action_single if type(action_single) == str else self.env.language_skill_set[action_single]
                            print(f"Executed action: {action_str}, Task success: {info['task_success']}")
                            logger.debug(f"reward: {reward}")
                            logger.debug(f"terminate: {done}\n")
                            self.planner.update_info(info)
                            img_path = self.env.save_image(obs)
                            episode_info['reward'].append(reward)
                            episode_info['num_invalid_actions'] += (info['last_action_success'] == 0)
                            if done or not info['last_action_success']:
                                # stop or replanning
                                print("Invalid action or task complete. If invalid then Replanning.")
                                break
                    else: # single action
                        obs, reward, done, info = self.env.step(action, reasoning=reasoning)
                        action_str = action if type(action) == str else self.env.language_skill_set[action]
                        print(f"Executed action: {action_str}, Task success: {info['task_success']}")
                        logger.debug(f"reward: {reward}")
                        logger.debug(f"terminate: {done}\n")
                        
                        self.planner.update_info(info)
                        img_path = self.env.save_image(obs)
                        episode_info['reward'].append(reward)
                        episode_info['num_invalid_actions'] += (info['last_action_success'] == 0)
                
                except Exception as e: 
                    print(e)
                    time.sleep(30)

            # evaluation metrics
            episode_info['instruction'] = user_instruction
            episode_info['reward'] = np.mean(episode_info['reward'])
            episode_info['task_success'] = info['task_success']
            episode_info["task_progress"] = info['task_progress']
            episode_info['num_steps'] = info["env_step"]
            episode_info['planner_steps'] = self.planner.planner_steps
            episode_info['planner_output_error'] = self.planner.output_json_error
            episode_info["num_invalid_actions"] = episode_info['num_invalid_actions']
            episode_info["num_invalid_action_ratio"] = episode_info['num_invalid_actions'] / info["env_step"] if info['env_step'] > 0 else 0
            episode_info["episode_elapsed_seconds"] = info.get("episode_elapsed_seconds", time.time() - self.env._episode_start_time)
            episode_info["eval_set"] = self.eval_set  # eval_set 추가
            # task_type 추가 (카테고리별 메모리 로드를 위해)
            if hasattr(self.env, 'episode_data') and self.env.episode_data is not None:
                episode_info["task_type"] = self.env.episode_data.get('task_type', '')
            else:
                episode_info["task_type"] = ''

            self.env.save_episode_log()
            self.save_episode_metric(episode_info)
            self.save_planner_outputs(reasoning_list)
            self.save_prompts(prompts_list)
            self.save_memory_info()
            progress_bar.update()


if __name__ == '__main__':
    import argparse
    def parse_arguments():
        parser = argparse.ArgumentParser(description='Change configuration parameters.')
        parser.add_argument('--model_name', type=str, help='Name of the model.')
        parser.add_argument('--n_shots', type=int, help='Number of examples')
        parser.add_argument('--down_sample_ratio', type=float, help='Down sample ratio.')
        parser.add_argument('--model_type', type=str, help='Type of the model.')
        parser.add_argument('--language_only', type=int, help='Set to True for language only mode.')
        parser.add_argument('--exp_name', type=str, help='Name of the experiment.')
        parser.add_argument('--chat_history', type=int, help='Set to True to enable chat history.')
        parser.add_argument('--detection_box', type=int, help='Set to True to enable detection.')
        parser.add_argument('--eval_sets', type=lambda s: s.split(','), help='Comma-separated list of evaluation sets.')
        parser.add_argument('--multistep', type=int, help='Number of steps for multi-step reasoning.')
        parser.add_argument('--resolution', type=int, help='Resolution for processing.')
        parser.add_argument('--env_feedback', type=int, help='Set to True to enable environment feedback.')
        parser.add_argument('--tp', type=int, help='number of tensor parallel splits of the model parameters')
        parser.add_argument('--memory_mode', type=str, default='baseline', help='Memory mode: baseline, failure_only, success_and_failure, success_only')
        parser.add_argument('--previous_results_dir', type=str, default=None, help='Directory path to previous results for memory loading')
        parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
        parser.add_argument('--tasks_per_task_type', type=int, default=None, help='Number of tasks to select per task_type (None for all tasks)')
        parser.add_argument('--task_selection_seed', type=int, default=None, help='Seed for task selection (defaults to seed if not specified)')
        return parser.parse_args()


    config = {
        'model_name': 'gpt-4o-mini', # 'Qwen/Qwen2-VL-7B-Instruct',
        'n_shots': 10,
        'down_sample_ratio': 1.0,
        'model_type': 'remote', # 'local', 
        'language_only': 0,
        'exp_name': 'vlm_10shots_imgsize500',
        'chat_history': 0, 
        'detection_box': 0,
        'eval_sets': ['base'], 
        'selected_indexes': [], 
        'multistep':0, 
        'resolution': 500, 
        'env_feedback': 1,
        'tp': 1,
        'memory_mode': 'baseline',  # 'baseline', 'failure_only', 'success_and_failure', 'success_only'
        'previous_results_dir': None,  # 이전 실행 결과 디렉토리 경로
        'seed': 42,  # 재현성을 위한 시드
        'tasks_per_task_type': None,  # 각 task_type당 선택할 task 개수 (None이면 전체 사용)
        'task_selection_seed': None,  # task 선택 시 사용할 시드 (None이면 seed 사용)
    }

    args = parse_arguments()
    update_config_with_args(config, args)

    evaluator = EB_AlfredEvaluator(config)
    evaluator.evaluate_main()




