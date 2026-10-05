from fixtures import *
import pytest
from docstorage.config import Config


def test_unknown_config_key(setup_db_environment):
    with pytest.raises(KeyError):
        Config()["unknown"]


def test_set_good_config(setup_db_environment):
    config = Config()
    config["landing-directory"] = "new/direcotory"
    config["db-path"] = "new/direcotory"


def test_set_bad_config(setup_db_environment):
    with pytest.raises(KeyError):
        Config()["unknown"] = "new/directory"
