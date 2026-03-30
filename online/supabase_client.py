from .config import get_supabase_anon_key, get_supabase_url


def create_client_or_none():
    """
    Returns a lightweight client config dict or None if env is incomplete.
    We use direct PostgREST HTTP calls to avoid heavy SDK dependencies.
    """
    url = get_supabase_url().rstrip("/")
    key = get_supabase_anon_key().strip()
    if not url or not key:
        return None

    return {
        "url": url,
        "key": key,
    }


def get_client_or_raise():
    client = create_client_or_none()
    if client is None:
        raise RuntimeError(
            "Supabase config is missing. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env."
        )
    return client
