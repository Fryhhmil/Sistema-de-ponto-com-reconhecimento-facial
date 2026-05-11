from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from enum import Enum


@dataclass(frozen=True)
class ConfigSnapshot:
    horario_entrada: time
    horario_saida: time
    tolerancia_min: int
    limite_recuperacao_min: int
    dias_uteis: frozenset  # 1=seg...7=dom (isoweekday)

    @classmethod
    def from_model(cls, cfg) -> "ConfigSnapshot":
        dias = frozenset(int(d) for d in cfg.dias_uteis.split(",") if d.strip())
        return cls(
            horario_entrada=cfg.horario_entrada,
            horario_saida=cfg.horario_saida,
            tolerancia_min=cfg.tolerancia_atraso_min,
            limite_recuperacao_min=cfg.limite_recuperacao_min,
            dias_uteis=dias,
        )


class StatusDia(str, Enum):
    COMPLETO = "completo"
    ATRASADO = "atrasado"
    SAIDA_ANTECIPADA = "saida_antecipada"
    INCOMPLETO = "incompleto"
    FALTA = "falta"
    FALTA_JUSTIFICADA = "falta_justificada"
    FERIADO = "feriado"
    FOLGA = "folga"


@dataclass
class ResultadoDia:
    data: date
    entrada: datetime | None
    saida: datetime | None
    horas_trabalhadas_min: int
    saldo_min: int
    atraso_min: int
    recuperado_min: int
    status: StatusDia


@dataclass
class ResumoMes:
    total_trabalhado_min: int
    total_previsto_min: int
    saldo_min: int
    dias_completos: int
    atrasos: int
    faltas: int
    faltas_justificadas: int
    feriados: int


def _time_to_dt(ref: datetime, t: time) -> datetime:
    return ref.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)


def calcular_dia(
    entrada: datetime | None,
    saida: datetime | None,
    cfg: ConfigSnapshot,
    feriado: bool,
    justificativa: str | None,
    data: date | None = None,
) -> ResultadoDia:
    """Calcula resultado de um dia de trabalho conforme regras da empresa."""
    data = data or (entrada.date() if entrada else date.today())

    # --- Feriado ---
    if feriado:
        return ResultadoDia(
            data=data, entrada=entrada, saida=saida,
            horas_trabalhadas_min=0, saldo_min=0,
            atraso_min=0, recuperado_min=0,
            status=StatusDia.FERIADO,
        )

    # --- Sem batidas ---
    if entrada is None and saida is None:
        if justificativa:
            return ResultadoDia(
                data=data, entrada=None, saida=None,
                horas_trabalhadas_min=0, saldo_min=0,
                atraso_min=0, recuperado_min=0,
                status=StatusDia.FALTA_JUSTIFICADA,
            )
        previsto = 600
        return ResultadoDia(
            data=data, entrada=None, saida=None,
            horas_trabalhadas_min=0, saldo_min=-previsto,
            atraso_min=0, recuperado_min=0,
            status=StatusDia.FALTA,
        )

    # --- Batida incompleta ---
    if entrada is None or saida is None:
        return ResultadoDia(
            data=data, entrada=entrada, saida=saida,
            horas_trabalhadas_min=0, saldo_min=-600,
            atraso_min=0, recuperado_min=0,
            status=StatusDia.INCOMPLETO,
        )

    # --- Dia com entrada e saída ---
    # Reference datetimes for entrada/saida schedule
    entrada_ref = _time_to_dt(entrada, cfg.horario_entrada)
    saida_ref = _time_to_dt(saida, cfg.horario_saida)

    # Atraso: how many minutes late (0 if on time or early)
    atraso_min = max(0, int((entrada - entrada_ref).total_seconds() / 60))

    # How much of that atraso can be recovered (capped by limite)
    recuperavel_min = min(atraso_min, cfg.limite_recuperacao_min)

    # Effective start: no early-bird credit
    inicio_efetivo = max(entrada, entrada_ref)

    # Effective end: cannot count past saida_ref + recuperavel (and not past actual saida)
    fim_limite = saida_ref + timedelta(minutes=recuperavel_min)
    fim_efetivo = min(saida, fim_limite)

    # Hours worked (minutes)
    horas_min = max(0, int((fim_efetivo - inicio_efetivo).total_seconds() / 60))

    # Previsto always 600 (8h workday doesn't change)
    previsto_min = 600
    saldo_min = horas_min - previsto_min

    # Minutes recovered beyond saida_ref
    recuperado_min = max(0, int((fim_efetivo - saida_ref).total_seconds() / 60))

    # --- Status ---
    if saldo_min >= 0:
        status = StatusDia.COMPLETO
    elif atraso_min > cfg.tolerancia_min:
        # Late beyond tolerance — check if left early too
        if saida < saida_ref:
            # Both late AND left early → ATRASADO (dominant)
            status = StatusDia.ATRASADO
        else:
            status = StatusDia.ATRASADO
    elif saida < saida_ref:
        status = StatusDia.SAIDA_ANTECIPADA
    else:
        # Within tolerance, didn't leave early, but still negative (shouldn't happen often)
        status = StatusDia.ATRASADO

    return ResultadoDia(
        data=data, entrada=entrada, saida=saida,
        horas_trabalhadas_min=horas_min,
        saldo_min=saldo_min,
        atraso_min=atraso_min,
        recuperado_min=recuperado_min,
        status=status,
    )


def calcular_mes(dias: list, dias_uteis_no_mes: int) -> ResumoMes:
    total_trabalhado = sum(d.horas_trabalhadas_min for d in dias)
    total_previsto = dias_uteis_no_mes * 600
    saldo = sum(
        d.saldo_min for d in dias
        if d.status not in {StatusDia.FERIADO, StatusDia.FOLGA, StatusDia.FALTA_JUSTIFICADA}
    )
    return ResumoMes(
        total_trabalhado_min=total_trabalhado,
        total_previsto_min=total_previsto,
        saldo_min=saldo,
        dias_completos=sum(1 for d in dias if d.status == StatusDia.COMPLETO),
        atrasos=sum(1 for d in dias if d.status == StatusDia.ATRASADO),
        faltas=sum(1 for d in dias if d.status == StatusDia.FALTA),
        faltas_justificadas=sum(1 for d in dias if d.status == StatusDia.FALTA_JUSTIFICADA),
        feriados=sum(1 for d in dias if d.status == StatusDia.FERIADO),
    )
