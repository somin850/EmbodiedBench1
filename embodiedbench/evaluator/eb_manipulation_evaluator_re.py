import re
import os
import numpy as np
from tqdm import tqdm
import json
import copy
import argparse
from embodiedbench.evaluator.config.system_prompts import eb_manipulation_system_prompt
from embodiedbench.envs.eb_manipulation.EBManEnv_re import EBManEnv, EVAL_SETS, ValidEvalSets
from embodiedbench.envs.eb_manipulation.eb_man_utils import form_object_coord_for_input, draw_bounding_boxes, draw_xyz_coordinate
from embodiedbench.planner.manip_planner_re import ManipPlanner
from embodiedbench.evaluator.config.eb_manipulation_example import vlm_examples_baseline, llm_examples, vlm_examples_ablation
from embodiedbench.main import logger

class EB_ManipulationEvaluator():
    def __init__(self, config):
        self.model_name = config['model_name']
        self.eval_set = ValidEvalSets[0]
        self.config = config
        self.env = None
        self.planner = None
        self.memory_mode = config.get('memory_mode', 'baseline')  
        # 'baseline', 'failure_only', 'success_and_failure', 'success_only'
        self.previous_results_dir = config.get('previous_results_dir', None)
        self.tasks_per_variation = config.get('tasks_per_variation', 5)
        self.task_selection_seed = config.get('task_selection_seed', 42)
        
        # 실험 구분자 설정 (파일명에 사용) - memory_mode 이름 그대로 사용
        self.exp_suffix = f'_{self.memory_mode}'

    def load_demonstration(self):
        all_examples = {}
        if self.config['language_only'] == 1:
            # visual icl baseline
            if self.config['visual_icl'] == 1:
                for variation in EVAL_SETS[self.eval_set]:
                    all_examples[variation] = vlm_examples_ablation[variation.split('_')[0]]
            # language only
            else:
                for variation in EVAL_SETS[self.eval_set]:
                    all_examples[variation] = llm_examples[variation.split('_')[0]]
        else:
            # main baseline
            if self.config['detection_box'] == 1 and self.config['multiview'] == 0 and self.config['visual_icl'] == 0 and self.config['multistep'] == 0:
                for variation in EVAL_SETS[self.eval_set]:
                    all_examples[variation] = vlm_examples_baseline[variation.split('_')[0]]
            # ablation study
            else:
                for variation in EVAL_SETS[self.eval_set]:
                    all_examples[variation] = vlm_examples_ablation[variation.split('_')[0]]

        return all_examples

    def load_dynamic_memory(self, task_variation):
        """이전 실행 결과에서 동적 메모리 로드"""
        if self.previous_results_dir is None or self.memory_mode == 'baseline':
            return [], []
        
        from embodiedbench.evaluator.memory_utils_re import load_memory_from_results
        
        # dataset_info는 사용하지 않음 (episode_results에서 직접 task_variation 읽음)
        memory = load_memory_from_results(
            self.previous_results_dir, 
            task_variation,
            dataset_info=None,  # episode_results에서 직접 task_variation 읽음
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

    def save_episode_metric(self, episode_info):
        filename = 'episode_{}_res{}.json'.format(self.env._current_episode_num, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            json.dump(episode_info, f, ensure_ascii=False, indent=2)
    
    def save_planner_outputs(self, reasoning_list):
        filename = 'planner_output_episode_{}{}.txt'.format(self.env._current_episode_num, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            for s in reasoning_list:
                f.write(s + "\n")
    
    def save_prompts(self, prompts_list):
        """실제 입력된 프롬프트 저장"""
        filename = 'prompts_episode_{}{}.txt'.format(self.env._current_episode_num, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            for i, prompt in enumerate(prompts_list):
                f.write(f"=== Step {i} ===\n")
                f.write(prompt)
                f.write("\n\n")
    
    def save_memory_info(self, task_variation):
        """사용된 메모리 정보 저장"""
        filename = 'memory_info_episode_{}{}.json'.format(self.env._current_episode_num, self.exp_suffix)
        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        
        memory_info = {
            'task_variation': task_variation,
            'memory_mode': self.memory_mode,
            'previous_results_dir': self.previous_results_dir,
            'used_memory': {
                'success_examples': self.planner.dynamic_success_examples.get(task_variation, []),
                'failure_examples': self.planner.dynamic_failure_examples.get(task_variation, [])
            },
            'num_success_examples': len(self.planner.dynamic_success_examples.get(task_variation, [])),
            'num_failure_examples': len(self.planner.dynamic_failure_examples.get(task_variation, []))
        }
        
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            json.dump(memory_info, f, ensure_ascii=False, indent=2)
    
    def print_task_eval_results(self, filename):
        folder_path = f"{self.log_path}/results"
        total_number_of_task = 0
        success_number_of_task = 0
        planner_steps = 0
        output_format_error = 0

        for file_name in sorted(os.listdir(folder_path)):
            if file_name.endswith(".json") and file_name.startswith("episode"):
                file_path = os.path.join(folder_path, file_name)
                
                # Open and load the JSON file
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    task_success = data["task_success"]
                    if data["planner_output_error"] > 0:    
                        output_format_error += 1
                    if task_success == 1:
                        success_number_of_task += 1
                    planner_steps += data["planner_steps"]
                    total_number_of_task += 1

        task_log = {}
        task_log['save_path'] = self.log_path
        task_log["total_num_tasks"] = total_number_of_task
        task_log["num_success"] = success_number_of_task
        task_log["success_rate"] = success_number_of_task / total_number_of_task
        task_log["avg_planner_steps"] = planner_steps / total_number_of_task
        task_log["output_format_error"] = output_format_error
        task_log["memory_mode"] = self.memory_mode
        task_log["tasks_per_variation"] = self.tasks_per_variation
        task_log["previous_results_dir"] = self.previous_results_dir

        res_path = os.path.join(self.env.log_path, 'results')
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        with open(os.path.join(res_path, filename), 'w', encoding='utf-8') as f:
            json.dump(task_log, f, ensure_ascii=False)

    def get_completed_episodes(self):
        """완료된 episode 번호 리스트 반환"""
        completed = []
        if self.env and self.env.log_path:
            results_path = os.path.join(self.env.log_path, 'results')
            if os.path.exists(results_path):
                for filename in os.listdir(results_path):
                    if filename.startswith('episode_') and '_res' in filename and filename.endswith('.json'):
                        try:
                            # episode_X_res{exp_suffix}.json 형식 파싱
                            parts = filename.replace('.json', '').split('_res')
                            episode_num = int(parts[0].split('_')[1])
                            completed.append(episode_num)
                        except:
                            continue
        return sorted(set(completed))
    
    def evaluate(self):
        # 완료된 episode 확인 및 스킵
        completed_episodes = self.get_completed_episodes()
        if completed_episodes:
            max_completed = max(completed_episodes)
            logger.info(f"[Resume] Found {len(completed_episodes)} completed episodes (up to episode {max_completed}). Skipping...")
            # 완료된 episode 다음부터 시작
            self.env._current_episode_num = max_completed + 1
            if self.env._current_episode_num >= self.env.number_of_episodes:
                logger.info(f"[Resume] All episodes already completed!")
                self.print_task_eval_results(filename="summary{}.json".format(self.exp_suffix))
                return
        
        progress_bar = tqdm(total=self.env.number_of_episodes, desc="Episodes", initial=self.env._current_episode_num)
        while self.env._current_episode_num < self.env.number_of_episodes:
            logger.info(f"Evaluating episode {self.env._current_episode_num} ...")
            episode_info = {'reward': [], 'action_success': [], 'executed_actions': [], 'step_task_success': []}
            image_history = []

            _, obs = self.env.reset()
            if self.config['multiview']:
                camera_views = ['front_rgb', 'wrist_rgb']
            else:
                camera_views = ['front_rgb']
            img_path_list = self.env.save_image(camera_views)

            avg_obj_coord, all_avg_point_list, camera_extrinsics_list, camera_intrinsics_list = form_object_coord_for_input(vars(copy.deepcopy(obs)), self.env.task_class, camera_views)
            if not self.config['language_only']:
                for i, img_path in enumerate(img_path_list):
                    if 'front_rgb' in img_path:
                        img_path_list[i] = draw_xyz_coordinate(img_path, self.config['resolution'])
            if self.config['detection_box'] and not self.config['language_only']:
                img_path_list = draw_bounding_boxes(img_path_list, all_avg_point_list, camera_extrinsics_list, camera_intrinsics_list)
            if self.config['multistep']:
                image_history.append(img_path_list[0])
            user_instruction = self.env.episode_language_instruction
            print(f"Instruction: {user_instruction}")
            self.planner.reset()
            done = False
            reasoning_list = []
            prompts_list = []  # 프롬프트 저장용

            while not done:
                if self.config['multistep']:
                    action, reasoning = self.planner.act(image_history, user_instruction, str(avg_obj_coord), self.env.current_task_variation)
                else:
                    action, reasoning = self.planner.act(img_path_list, user_instruction, str(avg_obj_coord), self.env.current_task_variation)
                print(f"Planner Output Action: {action}")
                reasoning_list.append(reasoning)
                # 프롬프트 저장
                if self.planner.last_prompt:
                    prompts_list.append(self.planner.last_prompt)
                if len(action) == 0:
                    episode_info['reward'].append(0)
                    episode_info['action_success'].append(0)
                    episode_info['executed_actions'].append([])
                    episode_info['step_task_success'].append(0)
                    info = {'task_success': 0, 'episode_elapsed_seconds': 0}
                    break
                else:
                    for action_single in action[:min(self.env._max_episode_steps - self.env._current_step, len(action))]:
                        obs, reward, done, info = self.env.step(action_single)
                        print(f"Executed action: {action_single}, Task success: {info['task_success']}")
                        logger.debug(f"reward: {reward}")
                        logger.debug(f"terminate: {done}\n")
                        self.planner.update_info(info)
                        img_path_list = self.env.save_image(camera_views)
                        for img_path in img_path_list:
                            if self.config['multistep']:
                                image_history.append(img_path)
                        episode_info['reward'].append(reward)
                        episode_info['action_success'].append(info['action_success'])
                        episode_info['executed_actions'].append(action_single)  # 실행된 액션 저장
                        episode_info['step_task_success'].append(info['task_success'])  # 각 스텝의 task_success 저장
                        if done:
                            break
                
                avg_obj_coord, all_avg_point_list, camera_extrinsics_list, camera_intrinsics_list = form_object_coord_for_input(copy.deepcopy(obs), self.env.task_class, camera_views)
                if not done:
                    if not self.config['language_only']:
                        for i, img_path in enumerate(img_path_list):
                            if 'front_rgb' in img_path:
                                img_path_list[i] = draw_xyz_coordinate(img_path, self.config['resolution'])
                    if self.config['detection_box'] and not self.config['language_only']:
                        img_path_list = draw_bounding_boxes(img_path_list, all_avg_point_list, camera_extrinsics_list, camera_intrinsics_list)
                        if self.config['multistep']:
                            if image_history[-1].split('.png')[0] in img_path_list[0]:
                                image_history.pop()
                                image_history.append(img_path_list[0])
            
            # evaluation metrics
            episode_info['instruction'] = user_instruction
            episode_info['avg_reward'] = np.mean(episode_info['reward'])
            episode_info['task_success'] = info['task_success']
            episode_info['num_steps'] = self.env._current_step
            episode_info['planner_steps'] = self.planner.planner_steps
            episode_info['planner_output_error'] = self.planner.output_json_error
            episode_info["episode_elapsed_seconds"] = info["episode_elapsed_seconds"]
            episode_info["task_variation"] = self.env.current_task_variation  # task_variation 추가
            self.save_episode_metric(episode_info)
            self.save_planner_outputs(reasoning_list)
            self.save_prompts(prompts_list)
            self.save_memory_info(self.env.current_task_variation)
            progress_bar.update()
        self.print_task_eval_results(filename="summary{}.json".format(self.exp_suffix))
        self.env.close()
    
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
            if "/" in self.model_name:
                real_model_name = self.model_name.split('/')[1]
            else:
                real_model_name = self.model_name
            if 'exp_name' not in self.config or self.config['exp_name'] is None:
                self.log_path = 'running/eb_manipulation/{}/n_shot={}_resolution={}_detection_box={}_multiview={}_multistep={}_visual_icl={}/{}'.format(
                                                                                                    real_model_name, 
                                                                                                    self.config['n_shots'], 
                                                                                                    self.config['resolution'], 
                                                                                                    self.config['detection_box'],
                                                                                                    self.config['multiview'],
                                                                                                    self.config['multistep'],
                                                                                                    self.config['visual_icl'],
                                                                                                    self.eval_set)
            else:
                # memory_mode에 따라 폴더명 생성: baseline4_re, failure4_re 등
                memory_mode_mapping = {
                    'baseline': 'baseline',
                    'failure_only': 'failure',
                    'success_and_failure': 'all',
                    'success_only': 'success'
                }
                memory_prefix = memory_mode_mapping.get(self.memory_mode, self.memory_mode)
                exp_name = self.config["exp_name"]
                # exp_name이 "4_re" 형식이면 "baseline4_re" 형식으로 조합
                folder_name = f"{memory_prefix}{exp_name}"
                self.log_path = 'running/eb_manipulation/{}/{}/{}'.format(real_model_name, folder_name, self.eval_set)
            self.env = EBManEnv(eval_set=self.eval_set, img_size=(self.config['resolution'], self.config['resolution']), down_sample_ratio=self.config["down_sample_ratio"], log_path=self.log_path, tasks_per_variation=self.tasks_per_variation, task_selection_seed=self.task_selection_seed)
            ic_examples = self.load_demonstration()
            self.planner = ManipPlanner(model_name=self.model_name,
                                        model_type=self.config['model_type'],
                                        system_prompt=eb_manipulation_system_prompt, 
                                        examples=ic_examples, 
                                        n_shot=self.config["n_shots"], 
                                        chat_history=self.config["chat_history"],
                                        language_only=self.config["language_only"],
                                        multiview=self.config["multiview"],
                                        multistep=self.config["multistep"],
                                        visual_icl=self.config["visual_icl"],
                                        tp=self.config["tp"])
            
            # 동적 메모리 추가 (각 task variation별로)
            if self.memory_mode != 'baseline':
                for variation in EVAL_SETS[self.eval_set]:
                    success_memory, failure_memory = self.load_dynamic_memory(variation)
                    if len(success_memory) > 0 or len(failure_memory) > 0:
                        self.planner.add_dynamic_memory(variation, success_memory, failure_memory)
                        logger.info(f"[Memory] Loaded {len(success_memory)} success + {len(failure_memory)} failure examples for {variation} (mode: {self.memory_mode})")
                    else:
                        logger.info(f"[Memory] No dynamic memory found for {variation} (mode: {self.memory_mode})")
            
            self.evaluate()
            with open(os.path.join(self.log_path, 'config.txt'), 'w') as f:
                f.write(str(self.config))
                
    def check_config_valid(self):
        if self.config['multiview'] + self.config['multistep'] + self.config['visual_icl'] + self.config['chat_history'] > 1:
            raise ValueError("Currently, we only support one of multiview, multistep, visual_icl, chat_history feature at a time.")
        
        if self.config['language_only']:
            if self.config['multiview'] or self.config['multistep']:
                logger.warning("Language only mode should not have multiview or multistep enabled. Setting these arguments to False ...")
                self.config['multiview'] = 0
                self.config['multistep'] = 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run evaluation with specified model name.")
    parser.add_argument('--model_name', type=str, required=True, help="Name of the model to evaluate.")
    parser.add_argument('--down_sample_ratio', type=float, default=1.0, help="Down sample ratio for the eval set.")
    parser.add_argument('--model_type', type=str, default='remote', help="Type of the model to evaluate.")
    parser.add_argument('--language_only', type=int, default=0, help="Whether to use language only.")
    parser.add_argument('--eval_sets', type=lambda s: s.split(','), help='Comma-separated list of evaluation sets.')
    parser.add_argument('--chat_history', type=int, default=0, help='Whether to use chat history.')
    parser.add_argument('--n_shots', type=int, default=10)
    parser.add_argument('--multiview', type=int, default=0)
    parser.add_argument('--detection_box', type=int, default=1)
    parser.add_argument('--multistep', type=int, default=0)
    parser.add_argument('--resolution', type=int, default=500)
    parser.add_argument('--exp_name', type=str)
    parser.add_argument('--visual_icl', type=int, default=0)
    parser.add_argument('--tp', type=int, default=1, help='number of tensor parallel splits of the model parameters')
    args = parser.parse_args()

    print("\n******** Evaluating eval set: {}, model: {} ********".format(args.eval_sets, args.model_name))
    config = {
        'model_name': args.model_name,
        'model_type': args.model_type,
        'eval_sets': args.eval_sets,
        'n_shots': args.n_shots,
        'resolution': args.resolution,
        'language_only': args.language_only,
        'down_sample_ratio': args.down_sample_ratio,
        'chat_history': args.chat_history,
        'detection_box': args.detection_box,
        'multiview': args.multiview,
        'multistep': args.multistep,
        'visual_icl': args.visual_icl,
        'exp_name': args.exp_name,
        'tp': args.tp,
        'selected_indexes': [0, 12]
    }
    print("printing config ...")
    for config_key in config:
        print(f"{config_key}: {config[config_key]}")
    evaluator = EB_ManipulationEvaluator(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()