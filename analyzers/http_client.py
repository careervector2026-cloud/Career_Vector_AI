import httpx

_client = None


def get_http_client():
    global _client

    if _client is None:
        _client = httpx.AsyncClient(
            timeout=10,
            limits=httpx.Limits(max_connections=100)
        )

    return _client