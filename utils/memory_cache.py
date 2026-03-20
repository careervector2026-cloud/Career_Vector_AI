#memory_cache.py
from collections import OrderedDict

MAX_CACHE_SIZE = 500

class LRUCache:
    def __init__(self, capacity=MAX_CACHE_SIZE):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)

        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


# global instance
analysis_cache_memory = LRUCache()