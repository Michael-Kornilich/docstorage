import json
import os
from pathlib import Path

Path("temp").mkdir(exist_ok=True)
Path("volume").mkdir(exist_ok=True)

if Path(os.environ["PWD"]).name != "docstorage":
    raise RuntimeError("Launch the script from the project root")

dev_local_config = {
    "db-path": f"{os.environ['PWD']}/volume/index/index.db",
    "storage-path": f"{os.environ['PWD']}/volume/storage"
}
with open("config/local.json", "r") as f:
    json.dump(dev_local_config, f)

user_local_config = {"landing-directory": f"{os.environ['PWD']}/temp"}
with open("config/user.json", "r") as f:
    json.dump(user_local_config, f)
