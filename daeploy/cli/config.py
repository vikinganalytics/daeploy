from pathlib import Path
import json

CONFIG_DIR = Path.home() / ".config" / "daeploy"
CONFIG_FILE = CONFIG_DIR / "daeployconfig.json"


def read_cli_configuration():
    with CONFIG_FILE.open("r") as file_handle:
        config = json.load(file_handle)
    return config


def save_cli_configuration(config):
    with CONFIG_FILE.open("w+") as file_handle:
        json.dump(config, file_handle)


def initialize_cli_configuration():
    CONFIG_DIR.mkdir(exist_ok=True, parents=True)
    config = {"active_host": None, "access_tokens": dict()}
    save_cli_configuration(config)
