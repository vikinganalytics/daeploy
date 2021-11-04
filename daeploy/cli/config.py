from pathlib import Path
import json
from typing import List

CONFIG_DIR = Path.home() / ".config" / "daeploy"
CONFIG_FILE = CONFIG_DIR / "daeployconfig.json"


class CliState:
    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = Path(config_file)

        if not self.config_file.exists():
            CONFIG_DIR.mkdir(exist_ok=True, parents=True)
            self._state = {"active_host": None, "access_tokens": {}}
            self.save_state()
        else:
            with open(self.config_file, "r", encoding="utf-8") as file_handle:
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

    def logout(self, host: str):
        if host not in self.list_hosts():
            raise KeyError("Unregistered host")

        if host == self.active_host():
            self._state["active_host"] = None

        del self._state["access_tokens"][host]
        self.save_state()

    def activate_host(self, host: str):
        if host not in self.list_hosts():
            raise KeyError("Unregistered host")
        self._state["active_host"] = host
        self.save_state()

    def save_state(self):
        with open(self.config_file, "w+", encoding="utf-8") as file_handle:
            json.dump(self._state, file_handle)
