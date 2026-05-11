import sys
from unittest.mock import MagicMock
import numpy as np
import pytest

# Mock face_recognition BEFORE any import of face_service
_face_rec_mock = MagicMock()
sys.modules['face_recognition'] = _face_rec_mock

from app.face_service import (
    serializar_encodings,
    desserializar_encodings,
    identificar_funcionario,
    NenhumRostoError,
    MultiplosRostosError,
    ImagemInvalidaError,
)


def make_encoding(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(128).astype(np.float64)


class TestSerializacao:
    def test_roundtrip_encoding(self):
        enc = make_encoding(42)
        json_str = serializar_encodings([enc])
        resultado = desserializar_encodings(json_str)
        np.testing.assert_array_almost_equal(enc, resultado[0])

    def test_cinco_encodings_roundtrip(self):
        encs = [make_encoding(i) for i in range(5)]
        json_str = serializar_encodings(encs)
        resultado = desserializar_encodings(json_str)
        assert len(resultado) == 5
        for orig, res in zip(encs, resultado):
            np.testing.assert_array_almost_equal(orig, res)

    def test_vazio(self):
        assert desserializar_encodings("") == []


class TestIdentificarFuncionario:
    def test_identifica_correto(self):
        enc_ref = make_encoding(1)
        cache = {
            1: [enc_ref],
            2: [make_encoding(99)],
        }
        # Set up mock return values for each call to face_distance
        _face_rec_mock.face_distance.side_effect = [
            np.array([0.3]),  # distância para func 1
            np.array([0.8]),  # distância para func 2
        ]
        resultado = identificar_funcionario(enc_ref, cache, threshold=0.6)
        assert resultado == 1

    def test_retorna_none_se_distancia_acima_threshold(self):
        enc_ref = make_encoding(1)
        cache = {1: [make_encoding(99)]}
        _face_rec_mock.face_distance.side_effect = None
        _face_rec_mock.face_distance.return_value = np.array([0.8])
        resultado = identificar_funcionario(enc_ref, cache, threshold=0.6)
        assert resultado is None

    def test_cache_vazio_retorna_none(self):
        resultado = identificar_funcionario(make_encoding(0), {}, threshold=0.6)
        assert resultado is None
