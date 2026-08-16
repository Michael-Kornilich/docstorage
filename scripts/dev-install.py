import json
import os
from pathlib import Path

if Path(os.environ["PWD"]).name != "docstorage":
    print("The scripts must be run from docstorage")
    quit()

Path("temp").mkdir(exist_ok=True)
Path("volume").mkdir(exist_ok=True)

dev_local_config = {
    "db-path": f"{os.environ['PWD']}/volume/index/index.db",
    "storage-path": f"{os.environ['PWD']}/volume/storage"
}
with open("config/local.json", "w") as f:
    json.dump(dev_local_config, f, indent=2)
print("Set up the local config. Now the database related object reside in volume/")

user_local_config = {"landing-directory": f"{os.environ['PWD']}/temp"}
with open("config/user.json", "w") as f:
    json.dump(user_local_config, f, indent=2)
print("Set up the user config. Now the landing directory is temp/")
