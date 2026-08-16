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
with open("config/local.json", "w") as f:
    json.dump(dev_local_config, f, indent=2)
print("Set up the local config. Now the database related object reside in volume/")

user_local_config = {"landing-directory": f"{os.environ['PWD']}/temp"}
with open("config/user.json", "w") as f:
    json.dump(user_local_config, f, indent=1)
print("Set up the user config. Now the landing directory is temp/")