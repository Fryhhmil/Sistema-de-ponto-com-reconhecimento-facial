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


def _salvar_foto_captura(base64_str: str, agora) -> str | None:
    import base64 as b64lib
    import uuid
    import os
    try:
        raw = base64_str.split(",", 1)[1] if "," in base64_str else base64_str
        img_bytes = b64lib.b64decode(raw)
        from flask import current_app
        subfolder = os.path.join("capturas", agora.strftime("%Y/%m/%d"))
        folder = os.path.join(current_app.root_path, "..", "instance", "uploads", subfolder)
        os.makedirs(folder, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(folder, fname), "wb") as f:
            f.write(img_bytes)
        return os.path.join("uploads", subfolder, fname)
    except Exception:
        return None
