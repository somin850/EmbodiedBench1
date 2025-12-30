import os
import hydra
from omegaconf import DictConfig, OmegaConf
import logging
import yaml

logger = logging.getLogger("EB_logger")
if not logger.hasHandlers():
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s] - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

link_path = os.path.join(os.path.dirname(__file__), 'envs/eb_habitat/data')
try:
    os.symlink(link_path, 'data')
except FileExistsError:
    pass 


# the corresponding evaluator class
class_names = {
    "eb-alf": "EB_AlfredEvaluator",
    "eb-hab": "EB_HabitatEvaluator",
    "eb-nav": "EB_NavigationEvaluator",
    "eb-man": "EB_ManipulationEvaluator"
}

# the evaluator file you want to use
module_names = {
    "eb-alf": "eb_alfred_evaluator",
    "eb-hab": "eb_habitat_evaluator",
    "eb-nav": "eb_navigation_evaluator",
    "eb-man": "eb_manipulation_evaluator_re"  # _re 버전 사용
}

def get_evaluator(env_name: str):

    if env_name not in module_names:
        raise ValueError(f"Unknown environment: {env_name}")
    
    module_name = f"embodiedbench.evaluator.{module_names[env_name]}"
    evaluator_name = class_names[env_name]
    
    module = __import__(module_name, fromlist=[evaluator_name])
    return getattr(module, evaluator_name)

@hydra.main(config_path="./configs", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    logging.getLogger().handlers.clear()
    
    if 'log_level' not in cfg or cfg.log_level == "INFO":
        logger.setLevel(logging.INFO)
    if 'log_level' in cfg and cfg.log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)

    env_name = cfg.env
    logger.info(f"Evaluating environment: {env_name}")
    
    # eb-man일 때는 eb-man_re.yaml 사용
    config_file = f"{env_name}_re.yaml" if env_name == "eb-man" else f"{env_name}.yaml"
    # 현재 디렉토리에 따라 경로 조정
    import os
    current_dir = os.getcwd()
    if current_dir.endswith('embodiedbench'):
        config_path = f"configs/{config_file}"
    else:
        config_path = f"embodiedbench/configs/{config_file}"
    with open(config_path, 'r') as f:
        base_config = yaml.safe_load(f)

    override_config = {
        k: v for k, v in OmegaConf.to_container(cfg).items() 
        if k != 'env' and v is not None
    }
    
    config = OmegaConf.merge(
        OmegaConf.create(base_config),
        override_config
    )

    print(config)
    logger.info("Starting evaluation")
    evaluator_class = get_evaluator(env_name)
    evaluator = evaluator_class(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()
    logger.info("Evaluation completed")

if __name__ == "__main__":
    main()