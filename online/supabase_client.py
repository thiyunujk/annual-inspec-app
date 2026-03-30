from typing import Optional

from .config import get_supabase_anon_key, get_supabase_url


def create_client_or_none() -> Optional[object]:
    """
    Returns a Supabase client when configuration and dependency are available.
    Returns None otherwise so current local mode remains unaffected.
    """
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        return None

    try:
        from supabase import create_client  # type: ignore
    except Exception:
        return None

    return create_client(url, key)
