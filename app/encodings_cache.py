import threading
import numpy as np

_cache: dict[int, list] = {}
_lock = threading.RLock()


def load_all() -> None:
    """Carrega todos os funcionários ativos no startup. Chamado pelo create_app."""
    from .models import Funcionario
    from .face_service import desserializar_encodings

    with _lock:
        _cache.clear()
        try:
            funcionarios = Funcionario.query.filter_by(ativo=True).all()
            for f in funcionarios:
                if f.face_encodings:
                    _cache[f.id] = desserializar_encodings(f.face_encodings)
        except Exception:
            pass  # Não falha startup se DB não existir ainda


def reload(funcionario_id: int) -> None:
    """Atualiza a entrada de um funcionário no cache (após cadastro/edição)."""
    from .models import Funcionario
    from .face_service import desserializar_encodings

    with _lock:
        f = Funcionario.query.get(funcionario_id)
        if f and f.ativo and f.face_encodings:
            _cache[funcionario_id] = desserializar_encodings(f.face_encodings)
        else:
            _cache.pop(funcionario_id, None)


def invalidate(funcionario_id: int) -> None:
    """Remove funcionário do cache (ao desativar)."""
    with _lock:
        _cache.pop(funcionario_id, None)


def get_all() -> dict:
    """Retorna cópia thread-safe do cache."""
    with _lock:
        return dict(_cache)
