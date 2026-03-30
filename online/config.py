import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def _load_env_file() -> None:
    """
    Lightweight .env loader to avoid extra dependency.
    Existing OS environment variables are not overwritten.
    """
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().lstrip("﻿")
        value = value.strip().strip('"').strip("'")
        if key:
            # For this app, .env should take precedence over inherited shell vars.
            os.environ[key] = value


_load_env_file()


def get_app_mode() -> str:
    """Returns application mode: local (default) or online."""
    mode = (os.getenv("APP_MODE", "local") or "local").strip().lower()
    return mode if mode in {"local", "online"} else "local"


def get_supabase_url() -> str:
    return (os.getenv("SUPABASE_URL", "") or "").strip()


def get_supabase_anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY", "") or "").strip()


def get_supabase_service_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_KEY", "") or "").strip()


def is_online_mode_enabled() -> bool:
    return get_app_mode() == "online"
