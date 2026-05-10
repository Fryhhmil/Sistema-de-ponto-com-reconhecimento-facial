import threading
import numpy as np

_cache: dict[int, list] = {}
_lock = threading.RLock()


def load_all() -> None:
    """Stub: will be implemented in Task 5."""
    pass


def reload(funcionario_id: int) -> None:
    with _lock:
        pass


def invalidate(funcionario_id: int) -> None:
    with _lock:
        _cache.pop(funcionario_id, None)


def get_all() -> dict[int, list]:
    with _lock:
        return dict(_cache)
