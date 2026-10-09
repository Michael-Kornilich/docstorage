"""Defines the configuration object and its logic"""
import json
from pathlib import Path
import os
from platformdirs import user_config_path, user_data_path, user_documents_path


class Config:
    """Config class representing the configurator object.
    Resolves and populates the default config at init time

    Supports reads and writes into the config file via Config()[key] = value
    """

    def __init__(self):
        if os.environ.get("DOCSTORAGE_ENV") == "dev":
            self.env = "dev"
            config_path = Path(os.getcwd()).parent / "config"
        elif os.environ.get("DOCSTORAGE_ENV") == "test":
            self.env = "test"
            self._configpath = Path(os.environ["TEST_CONFIG_PATH"])
            return
        else:
            self.env = "prod"
            config_path: Path = user_config_path("docstorage") / "config"

        Path.mkdir(config_path, parents=True, exist_ok=True)
        self._configpath = config_path / "config.json"
        if self._configpath.exists():
            return

        if self.env == "dev":
            config = {
                "db-path": str(Path(os.environ['PWD']).parent.joinpath("./volume/index/index.sqlite").resolve()),
                "storage-path": str(Path(os.environ['PWD']).parent.joinpath("./volume/storage").resolve()),
                "landing-directory": str(Path(os.environ['PWD']).parent.joinpath("./landing-dir").resolve()),
            }
        else:
            try:
                landing_path = user_documents_path()
            except Exception as err:
                print(f"Documents path not found ({err}). Defaulting to home directory.")
                landing_path = Path.home()

            config = {
                "db-path": str(user_data_path("docstorage").joinpath("./volume/index/index.sqlite").resolve()),
                "storage-path": str(user_data_path("docstorage").joinpath("./volume/storage")),
                "landing-directory": str(landing_path / "docstorage-landing")
            }

        with open(self._configpath, "w") as f:
            json.dump(config, f)

    def _load_config(self):
        """Helper function to load the config"""
        with open(self._configpath, "r") as f:
            try:
                config = json.load(f)
            except Exception as err:
                msg = f"""
                Error while reading config file: {err}. 
                Try to remove config from the following directory: '{str(self._configpath)}'
                The app will then recreate a new (default) config.
                """.strip()
                raise ImportError(msg) from None
        return config

    def __getitem__(self, key: str) -> str:
        config = self._load_config()
        if key not in config:
            raise KeyError(f"The {key} is invalid. Available keys are: {list(config.keys())}")
        return config[key]

    def __setitem__(self, key: str, value: str) -> None:
        config = self._load_config()

        if key not in config:
            raise KeyError(f"The {key} is invalid. Available keys are: {list(config.keys())}")
        try:
            value = str(value)
        except Exception as err:
            raise TypeError(f"Cannot coerce '{value}' to string: {err}") from None

        config[key] = value
        with open(self._configpath, "w") as f:
            json.dump(config, f)
        return None

    def items(self):
        with open(self._configpath, "r") as f:
            config = json.load(f)
        for i in config.items():
            yield i
