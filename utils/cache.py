"""
utils/cache.py
Flask-Caching configurável via variáveis de ambiente.
Dev: SimpleCache (in-process)
Prod: RedisCache (recomendado para múltiplos workers Gunicorn)
"""

import os
from flask_caching import Cache

CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT_SECONDS", 300))  # 5 minutos para desenvolvimento


def configure_cache(server) -> Cache:
    cache_type = os.getenv("CACHE_TYPE", "SimpleCache")
    config     = {
        "CACHE_TYPE":            cache_type,
        "CACHE_DEFAULT_TIMEOUT": CACHE_TIMEOUT,
    }
    if cache_type == "RedisCache":
        config["CACHE_REDIS_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    cache = Cache(config=config)
    cache.init_app(server)
    return cache
