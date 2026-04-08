"""Local-only configuration for machine-specific paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LOCAL_CONFIG_FILE = ".pkls.local.json"
LOCAL_CONFIG_KEYS = {
    "device_name",
    "obsidian_vault_path",
    "raw_full_root",
    "raw_sync_root",
    "workspace_root",
}


class LocalConfigError(ValueError):
    """Raised when local configuration is invalid."""


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_local_config_path(root: Path | None = None) -> Path:
    base = root or get_repo_root()
    return base / LOCAL_CONFIG_FILE


def read_local_config(root: Path | None = None) -> dict[str, Any]:
    config_path = get_local_config_path(root)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise LocalConfigError("local config must be a JSON object")
    unknown_keys = set(data) - LOCAL_CONFIG_KEYS
    if unknown_keys:
        raise LocalConfigError(f"unknown local config keys: {sorted(unknown_keys)}")
    return data


def write_local_config(config: dict[str, Any], root: Path | None = None) -> Path:
    if not isinstance(config, dict):
        raise LocalConfigError("local config must be a JSON object")
    unknown_keys = set(config) - LOCAL_CONFIG_KEYS
    if unknown_keys:
        raise LocalConfigError(f"unknown local config keys: {sorted(unknown_keys)}")
    config_path = get_local_config_path(root)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
    return config_path


def set_obsidian_vault_path(path: str, root: Path | None = None) -> Path:
    return _set_directory_path("obsidian_vault_path", path, root)


def set_raw_full_root(path: str, root: Path | None = None) -> Path:
    return _set_directory_path("raw_full_root", path, root)


def set_raw_sync_root(path: str, root: Path | None = None) -> Path:
    return _set_directory_path("raw_sync_root", path, root)


def set_workspace_root(path: str, root: Path | None = None) -> Path:
    return _set_directory_path("workspace_root", path, root)


def set_device_name(name: str, root: Path | None = None) -> Path:
    if not isinstance(name, str) or not name.strip():
        raise LocalConfigError("device name must be a non-empty string")
    config = read_local_config(root)
    config["device_name"] = name.strip()
    return write_local_config(config, root)


def get_obsidian_vault_path(root: Path | None = None) -> Path | None:
    return _get_optional_path("obsidian_vault_path", root)


def get_raw_full_root(root: Path | None = None) -> Path | None:
    return _get_optional_path("raw_full_root", root)


def get_raw_sync_root(root: Path | None = None) -> Path | None:
    return _get_optional_path("raw_sync_root", root)


def get_workspace_root(root: Path | None = None) -> Path | None:
    return _get_optional_path("workspace_root", root)


def get_device_name(root: Path | None = None) -> str | None:
    config = read_local_config(root)
    value = config.get("device_name")
    if value in {None, ""}:
        return None
    if not isinstance(value, str):
        raise LocalConfigError("device_name must be a string")
    return value


def get_notes_publish_root(root: Path | None = None) -> Path:
    vault_path = get_obsidian_vault_path(root)
    if vault_path is not None:
        return vault_path
    workspace_root = get_workspace_root(root)
    if workspace_root is None:
        raise LocalConfigError("configure workspace_root or obsidian_vault_path before publishing notes")
    return workspace_root / "notes"


def _set_directory_path(key: str, path: str, root: Path | None = None) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise LocalConfigError(f"{key} must be a non-empty string")
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(resolved_path)
    if not resolved_path.is_dir():
        raise LocalConfigError(f"{key} must point to a directory")

    config = read_local_config(root)
    config[key] = str(resolved_path)
    return write_local_config(config, root)


def _get_optional_path(key: str, root: Path | None = None) -> Path | None:
    config = read_local_config(root)
    value = config.get(key)
    if value in {None, ""}:
        return None
    if not isinstance(value, str):
        raise LocalConfigError(f"{key} must be a string")
    return Path(value)
