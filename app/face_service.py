import base64
import json
import io
import numpy as np
from PIL import Image


class NenhumRostoError(Exception):
    pass


class MultiplosRostosError(Exception):
    pass


class ImagemInvalidaError(Exception):
    pass


def extrair_encoding_de_base64(base64_str: str) -> np.ndarray:
    """Decodifica imagem base64, exige exatamente 1 rosto, retorna encoding 128-dim."""
    import face_recognition

    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_array = np.array(img)
    except Exception as exc:
        raise ImagemInvalidaError("Não foi possível decodificar a imagem.") from exc

    locations = face_recognition.face_locations(img_array, model="hog")
    if len(locations) == 0:
        raise NenhumRostoError("Nenhum rosto detectado. Posicione-se em frente à câmera.")
    if len(locations) > 1:
        raise MultiplosRostosError("Mais de um rosto detectado. Apenas uma pessoa por vez.")

    encodings = face_recognition.face_encodings(img_array, known_face_locations=locations)
    if not encodings:
        raise NenhumRostoError("Não foi possível extrair o encoding facial.")

    return encodings[0]


def identificar_funcionario(
    encoding: np.ndarray,
    cache: dict,
    threshold: float = 0.6,
) -> int | None:
    """Retorna funcionario_id com menor distância média ou None se acima do threshold."""
    import face_recognition

    melhor_id = None
    melhor_distancia = float("inf")

    for func_id, encodings_list in cache.items():
        if not encodings_list:
            continue
        distancias = face_recognition.face_distance(encodings_list, encoding)
        media = float(np.mean(distancias))
        if media < melhor_distancia:
            melhor_distancia = media
            melhor_id = func_id

    if melhor_distancia <= threshold:
        return melhor_id
    return None


def serializar_encodings(lista: list) -> str:
    """list[ndarray] → JSON string."""
    return json.dumps([enc.tolist() for enc in lista])


def desserializar_encodings(json_str: str) -> list:
    """JSON string → list[ndarray]."""
    if not json_str:
        return []
    return [np.array(enc, dtype=np.float64) for enc in json.loads(json_str)]
