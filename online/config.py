import os


def get_app_mode() -> str:
    """Returns application mode: local (default) or online."""
    return (os.getenv("APP_MODE", "local") or "local").strip().lower()


def get_supabase_url() -> str:
    return (os.getenv("SUPABASE_URL", "") or "").strip()


def get_supabase_anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY", "") or "").strip()


def get_supabase_service_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_KEY", "") or "").strip()


def is_online_mode_enabled() -> bool:
    return get_app_mode() == "online"
