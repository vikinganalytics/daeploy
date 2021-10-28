from pathlib import Path
import json
from typing import List

CONFIG_DIR = Path.home() / ".config" / "daeploy"
CONFIG_FILE = CONFIG_DIR / "daeployconfig.json"


class CliState:
    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = config_file

        if not self.config_file.exists():
            CONFIG_DIR.mkdir(exist_ok=True, parents=True)
            self._state = {"active_host": None, "access_tokens": {}}
            self.save_state()
        else:
            with open(self.config_file, "r") as file_handle:
                self._state = json.load(file_handle)

    def active_host(self) -> str:
        return self._state["active_host"]

    def host_token(self, host: str) -> str:
        return self._state["access_tokens"].get(host, "")

    def active_host_token(self) -> str:
        return self.host_token(self.active_host())

    def list_hosts(self) -> List[str]:
        return list(self._state["access_tokens"].keys())

    def add_host(self, host: str, access_token: str):
        self._state["access_tokens"][host] = access_token
        self.save_state()

    def activate_host(self, host: str):
        if host not in self.list_hosts():
            raise KeyError("Unregistered host")
        self._state["active_host"] = host
        self.save_state()

    def save_state(self):
        with self.config_file.open("w+") as file_handle:
            json.dump(self._state, file_handle)


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
