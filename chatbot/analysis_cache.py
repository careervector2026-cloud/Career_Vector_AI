import time

ANALYSIS_CACHE = {}
CACHE_TTL = 600  # seconds


def get_cached_analysis(key):

    item = ANALYSIS_CACHE.get(key)

    if not item:
        return None

    data, timestamp = item

    if time.time() - timestamp > CACHE_TTL:
        del ANALYSIS_CACHE[key]
        return None

    return data


def store_analysis(key, value):

    ANALYSIS_CACHE[key] = (value, time.time())