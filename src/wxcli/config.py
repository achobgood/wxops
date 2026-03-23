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

def get_org_id(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_id")

def get_org_name(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_name")

def save_org(org_id: str | None, org_name: str | None, path: Path = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(path)
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    if org_id:
        profile["org_id"] = org_id
        profile["org_name"] = org_name
    else:
        profile.pop("org_id", None)
        profile.pop("org_name", None)
    save_config(config, path)
