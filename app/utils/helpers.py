import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename: str, allowed: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_upload(file, subfolder: str = "fotos") -> str:
    """Salva upload com nome seguro + UUID. Retorna caminho relativo."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.root_path, "..", "instance", "uploads", subfolder)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return os.path.join("uploads", subfolder, filename)


def paginate_query(query, page: int, per_page: int = 20):
    return query.paginate(page=page, per_page=per_page, error_out=False)
