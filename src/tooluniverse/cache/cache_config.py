"""Cache configuration helpers for ToolUniverse startup."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_TRUTHY_VALUES = {"true", "1", "yes"}


@dataclass(frozen=True)
class CacheConfig:
    """Resolved cache settings for ``ResultCacheManager``."""

    enabled: bool
    persistence_enabled: bool
    memory_size: int
    default_ttl: Optional[int]
    singleflight_enabled: bool
    persistent_path: Optional[str]


def _env_truthy(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in _TRUTHY_VALUES


def build_cache_config() -> CacheConfig:
    """Resolve cache-related environment variables into one startup object."""

    cache_enabled = _env_truthy("TOOLUNIVERSE_CACHE_ENABLED")
    persistence_enabled = _env_truthy("TOOLUNIVERSE_CACHE_PERSIST")
    memory_size = int(os.getenv("TOOLUNIVERSE_CACHE_MEMORY_SIZE", "256"))
    default_ttl_env = os.getenv("TOOLUNIVERSE_CACHE_DEFAULT_TTL")
    default_ttl = int(default_ttl_env) if default_ttl_env else None
    singleflight_enabled = _env_truthy("TOOLUNIVERSE_CACHE_SINGLEFLIGHT")

    cache_path = os.getenv("TOOLUNIVERSE_CACHE_PATH")
    if not cache_path and persistence_enabled:
        base_dir = os.getenv("TOOLUNIVERSE_CACHE_DIR")
        if not base_dir:
            base_dir = os.path.join(str(Path.home()), ".tooluniverse")
        os.makedirs(base_dir, exist_ok=True)
        if not os.access(base_dir, os.W_OK) and not os.getenv("TOOLUNIVERSE_CACHE_DIR"):
            base_dir = os.path.join(tempfile.gettempdir(), "tooluniverse")
            os.makedirs(base_dir, exist_ok=True)
        cache_path = os.path.join(base_dir, "cache.sqlite")

    return CacheConfig(
        enabled=cache_enabled,
        persistence_enabled=persistence_enabled,
        memory_size=memory_size,
        default_ttl=default_ttl,
        singleflight_enabled=singleflight_enabled,
        persistent_path=cache_path if persistence_enabled else None,
    )
