from datetime import datetime
from flask import Blueprint, request, jsonify
from ..models import db, Funcionario, Ponto, Configuracao
from ..face_service import (
    extrair_encoding_de_base64, identificar_funcionario,
    NenhumRostoError, MultiplosRostosError, ImagemInvalidaError,
)
from .. import encodings_cache

api_bp = Blueprint("api", __name__)


def _tipo_batida(funcionario_id: int) -> str:
    hoje = datetime.utcnow().date()
    ultima = (
        Ponto.query
        .filter(Ponto.funcionario_id == funcionario_id,
                db.func.date(Ponto.data_hora) == hoje)
        .order_by(Ponto.data_hora.desc()).first()
    )
    return "saida" if (ultima and ultima.tipo == "entrada") else "entrada"


@api_bp.route("/reconhecer", methods=["POST"])
def reconhecer():
    data = request.get_json(silent=True) or {}
    imagem = data.get("imagem", "")
    modo = data.get("modo", "ponto")
    if not imagem:
        return jsonify(ok=False, erro="Imagem não recebida."), 400
    try:
        encoding = extrair_encoding_de_base64(imagem)
    except NenhumRostoError as e:
        return jsonify(ok=False, erro=str(e)), 400
    except MultiplosRostosError as e:
        return jsonify(ok=False, erro=str(e)), 400
    except ImagemInvalidaError as e:
        return jsonify(ok=False, erro=str(e)), 400

    cfg = Configuracao.get()
    func_id = identificar_funcionario(encoding, encodings_cache.get_all(),
                                      threshold=cfg.threshold_reconhecimento)
    if func_id is None:
        return jsonify(ok=False, erro="Funcionário não reconhecido. Procure o RH."), 404

    func = Funcionario.query.get(func_id)
    if not func or not func.ativo:
        return jsonify(ok=False, erro="Funcionário inativo."), 403

    if modo == "consulta":
        return jsonify(ok=True, funcionario_id=func.id, nome=func.nome,
                       foto_perfil=func.foto_perfil, cargo=func.cargo or "")

    tipo = _tipo_batida(func.id)
    agora = datetime.utcnow()
    ponto = Ponto(funcionario_id=func.id, tipo=tipo, data_hora=agora)
    if cfg.salvar_foto_captura:
        from ..utils.helpers import _salvar_foto_captura
        ponto.foto_registro = _salvar_foto_captura(imagem, agora)
    db.session.add(ponto)
    db.session.commit()

    return jsonify(ok=True, nome=func.nome, foto_perfil=func.foto_perfil, tipo=tipo,
                   data_hora=agora.strftime("%d/%m/%Y %H:%M:%S"))


@api_bp.route("/dados-funcionario", methods=["POST"])
def dados_funcionario():
    import calendar
    from datetime import date
    from ..time_service import ConfigSnapshot, calcular_dia, calcular_mes, StatusDia, ResultadoDia
    from ..models import Justificativa, Feriado

    data = request.get_json(silent=True) or {}
    func_id = data.get("funcionario_id")
    hoje = date.today()
    mes = int(data.get("mes", hoje.month))
    ano = int(data.get("ano", hoje.year))

    if not func_id:
        return jsonify(ok=False, erro="funcionario_id obrigatório."), 400
    func = Funcionario.query.get(func_id)
    if not func:
        return jsonify(ok=False, erro="Funcionário não encontrado."), 404

    cfg = ConfigSnapshot.from_model(Configuracao.get())
    _, total_dias = calendar.monthrange(ano, mes)
    dias_do_mes = [date(ano, mes, d) for d in range(1, total_dias + 1)]
    dias_uteis_count = sum(1 for d in dias_do_mes if d.isoweekday() in cfg.dias_uteis)

    pontos_mes = (Ponto.query
        .filter(Ponto.funcionario_id == func_id,
                db.extract("month", Ponto.data_hora) == mes,
                db.extract("year", Ponto.data_hora) == ano)
        .order_by(Ponto.data_hora).all())

    pontos_por_dia = {}
    for p in pontos_mes:
        pontos_por_dia.setdefault(p.data_hora.date(), []).append(p)

    feriados_db = Feriado.query.filter(
        db.extract("month", Feriado.data) == mes,
        db.extract("year", Feriado.data) == ano).all()
    feriados_set = {f.data for f in feriados_db}
    for fr in Feriado.query.filter_by(recorrente_anual=True).all():
        try:
            feriados_set.add(date(ano, fr.data.month, fr.data.day))
        except ValueError:
            pass

    just_por_dia = {j.data: j.tipo for j in
        Justificativa.query.filter(
            Justificativa.funcionario_id == func_id,
            db.extract("month", Justificativa.data) == mes,
            db.extract("year", Justificativa.data) == ano).all()}

    DIAS_PT = ["", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    def fmt(m: int) -> str:
        s = "-" if m < 0 else ""
        m = abs(m)
        return f"{s}{m // 60:02d}h{m % 60:02d}min"

    agora_local = datetime.now()
    hoje_local = agora_local.date()
    resultados = []
    for dia in dias_do_mes:
        if dia > hoje_local or (dia == hoje_local and agora_local.time() < cfg.horario_entrada):
            continue
        if func.data_admissao and dia < func.data_admissao:
            continue
        if dia.isoweekday() not in cfg.dias_uteis:
            resultados.append(ResultadoDia(
                data=dia, entrada=None, saida=None,
                horas_trabalhadas_min=0, saldo_min=0,
                atraso_min=0, recuperado_min=0, status=StatusDia.FOLGA))
            continue
        ps = pontos_por_dia.get(dia, [])
        entradas = [p.data_hora for p in ps if p.tipo == "entrada"]
        saidas = [p.data_hora for p in ps if p.tipo == "saida"]
        resultados.append(calcular_dia(
            entrada=entradas[0] if entradas else None,
            saida=saidas[-1] if saidas else None,
            cfg=cfg, feriado=dia in feriados_set,
            justificativa=just_por_dia.get(dia), data=dia))

    resumo = calcular_mes(resultados, dias_uteis_count)
    dias_json = [
        {"data": r.data.strftime("%d/%m"),
         "dia_semana": DIAS_PT[r.data.isoweekday()],
         "entrada": r.entrada.strftime("%H:%M") if r.entrada else "-",
         "saida": r.saida.strftime("%H:%M") if r.saida else "-",
         "horas": fmt(r.horas_trabalhadas_min),
         "saldo": fmt(r.saldo_min),
         "status": r.status.value}
        for r in resultados
    ]

    return jsonify(
        ok=True, nome=func.nome, foto_perfil=func.foto_perfil, cargo=func.cargo or "",
        resumo={
            "total_trabalhado": fmt(resumo.total_trabalhado_min),
            "total_previsto": fmt(resumo.total_previsto_min),
            "saldo": fmt(resumo.saldo_min),
            "atrasos": resumo.atrasos,
            "faltas": resumo.faltas,
            "faltas_justificadas": resumo.faltas_justificadas,
        },
        dias=dias_json)
