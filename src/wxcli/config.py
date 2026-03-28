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

CC_REGIONS = {
    "us1": "https://api.wxcc-us1.cisco.com",
    "eu1": "https://api.wxcc-eu1.cisco.com",
    "eu2": "https://api.wxcc-eu2.cisco.com",
    "anz1": "https://api.wxcc-anz1.cisco.com",
    "ca1": "https://api.wxcc-ca1.cisco.com",
    "jp1": "https://api.wxcc-jp1.cisco.com",
    "sg1": "https://api.wxcc-sg1.cisco.com",
}

def get_cc_base_url(path: Path = DEFAULT_CONFIG_PATH) -> str:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    region = profile.get("cc_region", "us1")
    return CC_REGIONS.get(region, CC_REGIONS["us1"])

def save_cc_region(region: str, path: Path = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(path)
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    profile["cc_region"] = region
    save_config(config, path)

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
