import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the source tree is importable even when tests are invoked without
# an editable install.  Several test files duplicated this boilerplate;
# doing it once here avoids the repetition.
# ---------------------------------------------------------------------------
_SRC_PATH = str(Path(__file__).resolve().parents[1] / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> None:
    os.environ.setdefault("PYTHONHASHSEED", "0")
    os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")
    # Avoid accidental network in unit tests unless explicitly marked
    os.environ.setdefault("TOOLUNIVERSE_TESTING", "1")


# ---------------------------------------------------------------------------
# Shared cache-related fixtures (used by test_cache_*, test_tooluniverse_cache_*)
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_cache_manager():
    """Create an in-memory-only ResultCacheManager (no persistence)."""
    from tooluniverse.cache.result_cache_manager import ResultCacheManager

    mgr = ResultCacheManager(
        memory_size=4,
        persistent_path=None,
        enabled=True,
        persistence_enabled=False,
        singleflight=False,
    )
    yield mgr
    mgr.close()


@pytest.fixture
def cache_env(tmp_path, monkeypatch):
    """Set cache-related environment variables for the duration of a test.

    Yields the path to the SQLite cache file.
    """
    cache_path = str(tmp_path / "cache.sqlite")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_ENABLED", "true")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "true")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_MEMORY_SIZE", "4")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PATH", cache_path)
    return cache_path
