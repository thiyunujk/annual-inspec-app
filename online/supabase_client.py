from functools import lru_cache

from .config import get_supabase_anon_key, get_supabase_url


@lru_cache(maxsize=1)
def _create_cached_client():
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        return None

    try:
        from supabase import create_client  # type: ignore
    except Exception:
        return None

    return create_client(url, key)


def create_client_or_none():
    """Returns Supabase client or None if configuration/dependency is missing."""
    return _create_cached_client()


def get_client_or_raise():
    client = _create_cached_client()
    if client is None:
        raise RuntimeError(
            "Supabase client is unavailable. Set SUPABASE_URL and SUPABASE_ANON_KEY, "
            "and install supabase package."
        )
    return client
