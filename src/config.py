"""Defines configuration logic"""
import json
from pathlib import Path
import os
from platformdirs import user_config_path, user_data_path, user_documents_path


class Config:
    """Config class representing the configurator object.
    Resolves and populates the default config at init time
    Methods: get and set item
    """

    def __init__(self):
        if os.environ.get("DOCSTORAGE_ENV") == "dev":
            self.env = "dev"
            print("Warning: the scripts assumes that the development is ran from the project root.")
            config_path = Path(os.getcwd()) / "config"
        elif os.environ.get("DOCSTORAGE_ENV") == "test":
            self.env = "test"
            self._configpath = Path(os.environ["TEST_CONFIG_PATH"]) / "./config/config.json"
            return
        else:
            self.env = "prod"
            config_path: Path = user_config_path("docstorage") / "config"

        Path.mkdir(config_path, parents=True, exist_ok=True)
        self._configpath = config_path / "config.json"
        if self._configpath.exists():
            return

        config = {
            "db-path": Path(os.environ['PWD'] if self.env == "dev" else user_data_path("docstorage")).joinpath(
                "./volume/index/index.db"),
            "storage-path": Path(os.environ['PWD'] if self.env == "dev" else user_data_path("docstorage")).joinpath(
                "./volume/storage"),
            "landing-directory": Path(
                os.environ['PWD'] if self.env == "dev" else user_documents_path()) / "docstorage-landing"
        }
        with open(self._configpath, "w") as f:
            json.dump(config, f, indent=2)

    def __getitem__(self, key: str) -> str:
        with open(self._configpath, "r") as f:
            config = json.load(f)
        if key not in config:
            raise KeyError(f"The {key} is invalid.")
        return config[key]

    def __setitem__(self, key: str, value: str) -> None:
        with open(self._configpath, "w") as f:
            config = json.load(f)
        if key not in config:
            raise KeyError(f"The {key} is invalid.")
        config[key] = value
        return None
