import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".wxcli" / "config.json"

def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {"profiles": {}}
    with open(path) as f:
        return json.load(f)

def save_config(data: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_token(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("token")

def get_expires_at(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("expires_at")
