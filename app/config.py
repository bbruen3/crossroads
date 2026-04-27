import yaml
import os
import re
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)

CONFIG_PATH = "/app/config.yaml"

logging.debug("config.py loaded, CONFIG_PATH={CONFIG_PATH}")
logging.debug("file exists: {os.path.exists(CONFIG_PATH)}")
logging.debug("/app contents: {os.listdir('/app')}")

def _expand_env_vars(value):
    if isinstance(value, str):
        def replacer(match):
            return os.environ.get(match.group(1), "")
        return re.sub(r'\$\{(\w+)\}', replacer, value)
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(i) for i in value]
    return value

_config_cache = None

def get_config() -> dict:
    global _config_cache
    if _config_cache is None:
        logging.debug("attempting open: {CONFIG_PATH}")
        with open(CONFIG_PATH) as f:
            raw = yaml.safe_load(f)
        _config_cache = _expand_env_vars(raw)
    return _config_cache
