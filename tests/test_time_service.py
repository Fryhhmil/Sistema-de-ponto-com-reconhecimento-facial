from datetime import datetime, time, date
import pytest
from app.time_service import (
    ConfigSnapshot,
    StatusDia,
    calcular_dia,
    calcular_mes,
)

CFG = ConfigSnapshot(
    horario_entrada=time(7, 0),
    horario_saida=time(17, 0),
    tolerancia_min=10,
    limite_recuperacao_min=120,
    dias_uteis=frozenset({1, 2, 3, 4, 5}),
)

def dt(h, m):
    return datetime(2024, 1, 15, h, m)  # segunda-feira


class TestCalcularDia:
    def test_dia_completo(self):
        r = calcular_dia(dt(7, 0), dt(17, 0), CFG, False, None)
        assert r.status == StatusDia.COMPLETO
        assert r.horas_trabalhadas_min == 600
        assert r.saldo_min == 0

    def test_entrada_antecipada_nao_conta(self):
        r = calcular_dia(dt(6, 0), dt(17, 0), CFG, False, None)
        assert r.horas_trabalhadas_min == 600
        assert r.saldo_min == 0

    def test_atraso_dentro_tolerancia(self):
        r = calcular_dia(dt(7, 10), dt(17, 0), CFG, False, None)
        assert r.atraso_min == 10
        assert r.saldo_min == -10

    def test_atraso_recuperado(self):
        r = calcular_dia(dt(7, 30), dt(17, 30), CFG, False, None)
        assert r.horas_trabalhadas_min == 600
        assert r.saldo_min == 0
        assert r.status == StatusDia.COMPLETO

    def test_hora_extra_nao_conta(self):
        r = calcular_dia(dt(7, 0), dt(19, 0), CFG, False, None)
        assert r.horas_trabalhadas_min == 600
        assert r.saldo_min == 0

    def test_atraso_acima_tolerancia(self):
        r = calcular_dia(dt(7, 30), dt(17, 0), CFG, False, None)
        assert r.status == StatusDia.ATRASADO
        assert r.atraso_min == 30
        assert r.saldo_min == -30

    def test_feriado(self):
        r = calcular_dia(None, None, CFG, True, None)
        assert r.status == StatusDia.FERIADO
        assert r.horas_trabalhadas_min == 0

    def test_falta(self):
        r = calcular_dia(None, None, CFG, False, None)
        assert r.status == StatusDia.FALTA
        assert r.saldo_min == -600

    def test_falta_justificada(self):
        r = calcular_dia(None, None, CFG, False, "atestado")
        assert r.status == StatusDia.FALTA_JUSTIFICADA
        assert r.saldo_min == 0

    def test_saida_antecipada(self):
        r = calcular_dia(dt(7, 0), dt(16, 0), CFG, False, None)
        assert r.status == StatusDia.SAIDA_ANTECIPADA
        assert r.saldo_min == -60

    def test_recuperacao_limitada_a_2h(self):
        # Atraso 3h mas limite é 2h
        r = calcular_dia(dt(10, 0), dt(19, 0), CFG, False, None)
        assert r.horas_trabalhadas_min == 540
        assert r.saldo_min == -60

    def test_falta_sem_batidas(self):
        r = calcular_dia(None, None, CFG, False, None)
        assert r.status == StatusDia.FALTA
