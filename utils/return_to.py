from flask import request, session, url_for
from urllib.parse import urlparse

def _is_safe(url: str) -> bool:
    if not url:
        return False
    p = urlparse(url)
    return p.scheme == "" and p.netloc == "" and url.startswith("/")

def remember_return_to(key: str, fallback_endpoint: str, **fallback_kwargs) -> None:
    """
    Store current URL (path+query) into session under `key`
    so subsequent pages can 'go back' here.
    """
    url = request.full_path.rstrip("?")
    if _is_safe(url):
        session[key] = url
    else:
        session[key] = url_for(fallback_endpoint, **fallback_kwargs)

def get_return_to(key: str, fallback_endpoint: str, **fallback_kwargs) -> str:
    url = session.get(key)
    if _is_safe(url):
        return url
    return url_for(fallback_endpoint, **fallback_kwargs)
