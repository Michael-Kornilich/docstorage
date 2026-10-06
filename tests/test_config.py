from fixtures import *
import pytest
from docstorage.config import Config
import json


def try_reading_config(path: Path):
    with open(path, "r") as f:
        try:
            json.load(f)
        except Exception as err:
            got_config = path.read_text()
            print(got_config)
            pytest.fail(f"Failed to load config: {err}")


def test_unknown_config_key(setup_db_environment):
    with pytest.raises(KeyError):
        Config()["unknown"]

    try_reading_config(setup_db_environment / "config" / "config.json")


def test_set_good_config(setup_db_environment):
    config = Config()
    config["landing-directory"] = "new/direcotory"
    config["db-path"] = "new/direcotory"

    try_reading_config(setup_db_environment / "config" / "config.json")


def test_set_bad_config(setup_db_environment):
    with pytest.raises(KeyError):
        Config()["unknown"] = "new/directory"

    try_reading_config(setup_db_environment / "config" / "config.json")
