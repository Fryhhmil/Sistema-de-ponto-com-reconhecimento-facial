import io
import json
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import login_required, current_user
from ..models import db, Funcionario, Ponto, Configuracao, Justificativa, Feriado, AuditLog

admin_bp = Blueprint("admin", __name__)


@admin_bp.context_processor
def inject_globals():
    return {"config_empresa": Configuracao.get()}


@admin_bp.before_request
@login_required
def require_login():
    pass


@admin_bp.route("/")
def dashboard():
    hoje = date.today()
    total_ativos = Funcionario.query.filter_by(ativo=True).count()
    presentes_hoje = (db.session.query(Ponto.funcionario_id)
        .filter(db.func.date(Ponto.data_hora) == hoje, Ponto.tipo == "entrada")
        .distinct().count())
    ausentes_hoje = total_ativos - presentes_hoje
    ultimas_batidas = (Ponto.query.join(Funcionario)
        .filter(Funcionario.ativo.is_(True))
        .order_by(Ponto.data_hora.desc()).limit(10).all())
    pontos_30d = (db.session.query(
            db.func.date(Ponto.data_hora).label("dia"),
            db.func.count(Ponto.id).label("total"))
        .group_by("dia").order_by("dia")
        .limit(30).all())
    return render_template("admin/dashboard.html",
        total_ativos=total_ativos, presentes_hoje=presentes_hoje,
        ausentes_hoje=ausentes_hoje, ultimas_batidas=ultimas_batidas,
        pontos_30d=[{"dia": str(r.dia), "total": r.total} for r in pontos_30d])


@admin_bp.route("/funcionarios")
def listar_funcionarios():
    page = request.args.get("page", 1, type=int)
    busca = request.args.get("q", "").strip()
    depto = request.args.get("departamento", "")
    status = request.args.get("status", "ativo")

    q = Funcionario.query
    if busca:
        q = q.filter(Funcionario.nome.ilike(f"%{busca}%") | Funcionario.matricula.ilike(f"%{busca}%"))
    if depto:
        q = q.filter_by(departamento=depto)
    if status == "ativo":
        q = q.filter_by(ativo=True)
    elif status == "inativo":
        q = q.filter_by(ativo=False)

    departamentos = db.session.query(Funcionario.departamento).filter(
        Funcionario.departamento.isnot(None)).distinct().all()
    paginacao = q.order_by(Funcionario.nome).paginate(page=page, per_page=20, error_out=False)

    return render_template("admin/funcionarios/lista.html",
        paginacao=paginacao, busca=busca, depto=depto, status=status,
        departamentos=[d[0] for d in departamentos if d[0]])


@admin_bp.route("/funcionarios/novo", methods=["GET", "POST"])
def novo_funcionario():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf", "").strip()
        matricula = request.form.get("matricula", "").strip()
        cargo = request.form.get("cargo", "").strip()
        departamento = request.form.get("departamento", "").strip()
        data_admissao_str = request.form.get("data_admissao", "")

        erros = []
        if not nome:
            erros.append("Nome obrigatório.")
        if not cpf:
            erros.append("CPF obrigatório.")
        if not matricula:
            erros.append("Matrícula obrigatória.")
        if Funcionario.query.filter_by(cpf=cpf).first():
            erros.append("CPF já cadastrado.")
        if Funcionario.query.filter_by(matricula=matricula).first():
            erros.append("Matrícula já cadastrada.")

        if erros:
            for e in erros:
                flash(e, "danger")
            return render_template("admin/funcionarios/form.html", funcionario=None)

        data_admissao = None
        if data_admissao_str:
            try:
                data_admissao = date.fromisoformat(data_admissao_str)
            except ValueError:
                pass

        func = Funcionario(nome=nome, cpf=cpf, matricula=matricula,
                           cargo=cargo, departamento=departamento, data_admissao=data_admissao)
        db.session.add(func)
        db.session.commit()
        flash("Funcionário cadastrado! Agora capture as fotos do rosto.", "success")
        return redirect(url_for("admin.fotos_funcionario", func_id=func.id))

    return render_template("admin/funcionarios/form.html", funcionario=None)


@admin_bp.route("/funcionarios/<int:func_id>/editar", methods=["GET", "POST"])
def editar_funcionario(func_id: int):
    func = Funcionario.query.get_or_404(func_id)

    if request.method == "POST":
        func.nome = request.form.get("nome", func.nome).strip()
        func.cargo = request.form.get("cargo", "").strip()
        func.departamento = request.form.get("departamento", "").strip()
        data_str = request.form.get("data_admissao", "")
        if data_str:
            try:
                func.data_admissao = date.fromisoformat(data_str)
            except ValueError:
                pass

        foto = request.files.get("foto_perfil")
        if foto and foto.filename:
            from ..utils.helpers import allowed_file, save_upload
            from flask import current_app
            if allowed_file(foto.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]):
                func.foto_perfil = save_upload(foto, "perfis")

        db.session.commit()
        flash("Dados atualizados com sucesso.", "success")
        return redirect(url_for("admin.listar_funcionarios"))

    return render_template("admin/funcionarios/form.html", funcionario=func)


@admin_bp.route("/funcionarios/<int:func_id>/fotos", methods=["GET", "POST"])
def fotos_funcionario(func_id: int):
    func = Funcionario.query.get_or_404(func_id)

    if request.method == "POST":
        from ..face_service import (extrair_encoding_de_base64, serializar_encodings,
                                     NenhumRostoError, MultiplosRostosError, ImagemInvalidaError)
        from ..utils.helpers import _salvar_foto_captura

        imagens = request.get_json(silent=True) or {}
        encodings = []
        for i in range(1, 6):
            b64 = imagens.get(f"foto_{i}", "")
            if not b64:
                return jsonify(ok=False, erro=f"Foto {i} não recebida."), 400
            try:
                enc = extrair_encoding_de_base64(b64)
                encodings.append(enc)
            except (NenhumRostoError, MultiplosRostosError, ImagemInvalidaError) as e:
                return jsonify(ok=False, erro=f"Foto {i}: {e}"), 400

        func.face_encodings = serializar_encodings(encodings)
        foto_path = _salvar_foto_captura(imagens.get("foto_1", ""), datetime.utcnow())
        if foto_path:
            func.foto_perfil = foto_path

        db.session.commit()
        from .. import encodings_cache
        encodings_cache.reload(func.id)
        return jsonify(ok=True, redirect=url_for("admin.listar_funcionarios"))

    return render_template("admin/funcionarios/fotos.html", func=func)


@admin_bp.route("/funcionarios/<int:func_id>/desativar", methods=["POST"])
def desativar_funcionario(func_id: int):
    func = Funcionario.query.get_or_404(func_id)
    func.ativo = False
    db.session.commit()
    from .. import encodings_cache
    encodings_cache.invalidate(func.id)
    flash(f"Funcionário {func.nome} desativado.", "warning")
    return redirect(url_for("admin.listar_funcionarios"))


@admin_bp.route("/pontos")
def listar_pontos():
    import calendar
    from datetime import date
    page = request.args.get("page", 1, type=int)
    func_id = request.args.get("funcionario_id", type=int)
    depto = request.args.get("departamento", "")
    hoje = date.today()
    mes = request.args.get("mes", hoje.month, type=int)
    ano = request.args.get("ano", hoje.year, type=int)

    _, ultimo_dia = calendar.monthrange(ano, mes)
    data_ini = date(ano, mes, 1)
    data_fim = date(ano, mes, ultimo_dia)

    q = (Ponto.query.join(Funcionario)
         .filter(Ponto.data_hora >= data_ini, Ponto.data_hora <= data_fim)
         .filter(Funcionario.ativo.is_(True)))
    if func_id:
        q = q.filter(Ponto.funcionario_id == func_id)
    if depto:
        q = q.filter(Funcionario.departamento == depto)

    paginacao = q.order_by(Ponto.data_hora.desc()).paginate(page=page, per_page=20, error_out=False)
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    departamentos = db.session.query(Funcionario.departamento).filter(
        Funcionario.departamento.isnot(None)).distinct().all()

    return render_template("admin/pontos/lista.html",
        paginacao=paginacao, func_id=func_id, depto=depto,
        mes=mes, ano=ano, funcionarios=funcionarios,
        departamentos=[d[0] for d in departamentos if d[0]])


@admin_bp.route("/pontos/<int:ponto_id>/editar", methods=["POST"])
def editar_ponto(ponto_id: int):
    ponto = Ponto.query.get_or_404(ponto_id)
    nova_data_hora_str = request.form.get("data_hora", "")
    justificativa_txt = request.form.get("justificativa", "").strip()

    if not nova_data_hora_str or not justificativa_txt:
        flash("Data/hora e justificativa são obrigatórios.", "danger")
        return redirect(request.referrer or url_for("admin.listar_pontos"))

    try:
        nova_dt = datetime.strptime(nova_data_hora_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Formato de data/hora inválido.", "danger")
        return redirect(request.referrer or url_for("admin.listar_pontos"))

    ponto.data_hora_original = ponto.data_hora
    ponto.data_hora = nova_dt
    ponto.editado_por_admin = True
    ponto.justificativa = justificativa_txt
    db.session.commit()

    db.session.add(AuditLog(usuario_id=current_user.id, acao="editar_ponto",
        detalhes=json.dumps({"ponto_id": ponto_id,
                             "data_hora_original": str(ponto.data_hora_original),
                             "nova_data_hora": str(nova_dt),
                             "justificativa": justificativa_txt})))
    db.session.commit()

    flash("Ponto editado com sucesso.", "success")
    return redirect(request.referrer or url_for("admin.listar_pontos"))


@admin_bp.route("/pontos/adicionar", methods=["POST"])
def adicionar_ponto():
    func_id = request.form.get("funcionario_id", type=int)
    tipo = request.form.get("tipo", "")
    data_hora_str = request.form.get("data_hora", "")
    justificativa_txt = request.form.get("justificativa", "").strip()

    if not all([func_id, tipo in ("entrada", "saida"), data_hora_str, justificativa_txt]):
        flash("Todos os campos são obrigatórios.", "danger")
        return redirect(request.referrer or url_for("admin.listar_pontos"))

    try:
        data_hora = datetime.strptime(data_hora_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Formato de data/hora inválido.", "danger")
        return redirect(request.referrer or url_for("admin.listar_pontos"))

    ponto = Ponto(funcionario_id=func_id, tipo=tipo, data_hora=data_hora,
                  editado_por_admin=True, justificativa=justificativa_txt)
    db.session.add(ponto)
    db.session.commit()

    db.session.add(AuditLog(usuario_id=current_user.id, acao="adicionar_ponto_manual",
        detalhes=json.dumps({"funcionario_id": func_id, "tipo": tipo,
                             "data_hora": str(data_hora)})))
    db.session.commit()

    flash("Batida manual adicionada.", "success")
    return redirect(request.referrer or url_for("admin.listar_pontos"))


@admin_bp.route("/pontos/<int:ponto_id>/excluir", methods=["POST"])
def excluir_ponto(ponto_id: int):
    ponto = Ponto.query.get_or_404(ponto_id)
    db.session.add(AuditLog(usuario_id=current_user.id, acao="excluir_ponto",
        detalhes=json.dumps({"ponto_id": ponto_id, "funcionario_id": ponto.funcionario_id,
                             "tipo": ponto.tipo, "data_hora": str(ponto.data_hora)})))
    db.session.delete(ponto)
    db.session.commit()
    flash("Batida excluída.", "success")
    return redirect(request.referrer or url_for("admin.listar_pontos"))


@admin_bp.route("/justificativas")
def listar_justificativas():
    import calendar
    from datetime import date
    hoje = date.today()
    mes = request.args.get("mes", hoje.month, type=int)
    ano = request.args.get("ano", hoje.year, type=int)
    func_id = request.args.get("funcionario_id", type=int)

    _, ultimo_dia = calendar.monthrange(ano, mes)
    data_ini = date(ano, mes, 1)
    data_fim = date(ano, mes, ultimo_dia)

    justificativas_q = Justificativa.query.filter(
        Justificativa.data >= data_ini, Justificativa.data <= data_fim)
    if func_id:
        justificativas_q = justificativas_q.filter_by(funcionario_id=func_id)
    justificativas_list = justificativas_q.order_by(Justificativa.data.desc()).all()

    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    return render_template("admin/justificativas/lista.html",
        justificativas=justificativas_list, funcionarios=funcionarios,
        mes=mes, ano=ano, func_id=func_id)


@admin_bp.route("/justificativas/nova", methods=["POST"])
def nova_justificativa():
    from datetime import date
    func_id = request.form.get("funcionario_id", type=int)
    data_str = request.form.get("data", "")
    motivo = request.form.get("motivo", "").strip()
    tipo = request.form.get("tipo", "")

    TIPOS_VALIDOS = {"falta_justificada", "atestado", "folga", "outro"}
    if not all([func_id, data_str, motivo, tipo in TIPOS_VALIDOS]):
        flash("Todos os campos são obrigatórios.", "danger")
        return redirect(request.referrer or url_for("admin.listar_justificativas"))

    try:
        data = date.fromisoformat(data_str)
    except ValueError:
        flash("Data inválida.", "danger")
        return redirect(request.referrer or url_for("admin.listar_justificativas"))

    Justificativa.query.filter_by(funcionario_id=func_id, data=data).delete()
    just = Justificativa(funcionario_id=func_id, data=data, motivo=motivo,
                         tipo=tipo, created_by=current_user.id)
    db.session.add(just)
    db.session.commit()
    flash("Justificativa registrada com sucesso.", "success")
    return redirect(request.referrer or url_for("admin.listar_justificativas"))


@admin_bp.route("/justificativas/<int:just_id>/excluir", methods=["POST"])
def excluir_justificativa(just_id: int):
    just = Justificativa.query.get_or_404(just_id)
    db.session.delete(just)
    db.session.commit()
    flash("Justificativa removida.", "success")
    return redirect(request.referrer or url_for("admin.listar_justificativas"))


@admin_bp.route("/feriados")
def listar_feriados():
    feriados = Feriado.query.order_by(Feriado.data).all()
    return render_template("admin/feriados/lista.html", feriados=feriados)


@admin_bp.route("/feriados/novo", methods=["POST"])
def novo_feriado():
    from datetime import date
    data_str = request.form.get("data", "")
    descricao = request.form.get("descricao", "").strip()
    recorrente = request.form.get("recorrente_anual") == "on"

    if not data_str or not descricao:
        flash("Data e descrição são obrigatórios.", "danger")
        return redirect(url_for("admin.listar_feriados"))

    try:
        data = date.fromisoformat(data_str)
    except ValueError:
        flash("Data inválida.", "danger")
        return redirect(url_for("admin.listar_feriados"))

    if Feriado.query.filter_by(data=data).first():
        flash("Já existe um feriado nesta data.", "warning")
        return redirect(url_for("admin.listar_feriados"))

    db.session.add(Feriado(data=data, descricao=descricao, recorrente_anual=recorrente))
    db.session.commit()
    flash("Feriado cadastrado.", "success")
    return redirect(url_for("admin.listar_feriados"))


@admin_bp.route("/feriados/<int:feriado_id>/excluir", methods=["POST"])
def excluir_feriado(feriado_id: int):
    f = Feriado.query.get_or_404(feriado_id)
    db.session.delete(f)
    db.session.commit()
    flash("Feriado removido.", "success")
    return redirect(url_for("admin.listar_feriados"))


@admin_bp.route("/relatorios")
def relatorios():
    from datetime import datetime as dt
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    departamentos = db.session.query(Funcionario.departamento).filter(
        Funcionario.departamento.isnot(None)).distinct().all()
    return render_template("admin/relatorios/index.html",
        funcionarios=funcionarios,
        departamentos=[d[0] for d in departamentos if d[0]],
        now=dt.utcnow())


@admin_bp.route("/relatorios/pdf")
def relatorio_pdf():
    import calendar
    from datetime import date as dt_date
    from ..time_service import ConfigSnapshot, calcular_dia, calcular_mes, StatusDia, ResultadoDia
    from ..report_service import gerar_pdf_espelho

    func_id = request.args.get("funcionario_id", type=int)
    mes = request.args.get("mes", datetime.utcnow().month, type=int)
    ano = request.args.get("ano", datetime.utcnow().year, type=int)

    if not func_id:
        flash("Selecione um funcionário.", "danger")
        return redirect(url_for("admin.relatorios"))

    func = Funcionario.query.get_or_404(func_id)
    cfg = ConfigSnapshot.from_model(Configuracao.get())
    nome_empresa = Configuracao.get().nome_empresa or ""

    _, total_dias = calendar.monthrange(ano, mes)
    dias_do_mes = [dt_date(ano, mes, d) for d in range(1, total_dias + 1)]
    dias_uteis_count = sum(1 for d in dias_do_mes if d.isoweekday() in cfg.dias_uteis)

    pontos_mes = (Ponto.query
        .filter(Ponto.funcionario_id == func_id,
                db.extract("month", Ponto.data_hora) == mes,
                db.extract("year", Ponto.data_hora) == ano)
        .order_by(Ponto.data_hora).all())

    pontos_por_dia = {}
    for p in pontos_mes:
        pontos_por_dia.setdefault(p.data_hora.date(), []).append(p)

    feriados_set = {f.data for f in Feriado.query.filter(
        db.extract("month", Feriado.data) == mes,
        db.extract("year", Feriado.data) == ano).all()}
    for fr in Feriado.query.filter_by(recorrente_anual=True).all():
        try:
            feriados_set.add(dt_date(ano, fr.data.month, fr.data.day))
        except ValueError:
            pass

    just_por_dia = {j.data: j.tipo for j in Justificativa.query.filter(
        Justificativa.funcionario_id == func_id,
        db.extract("month", Justificativa.data) == mes,
        db.extract("year", Justificativa.data) == ano).all()}

    agora_local = datetime.now()
    hoje_local = agora_local.date()
    resultados = []
    for dia in dias_do_mes:
        if dia > hoje_local or (dia == hoje_local and agora_local.time() < cfg.horario_entrada):
            continue
        if func.data_admissao and dia < func.data_admissao:
            continue
        if dia.isoweekday() not in cfg.dias_uteis:
            resultados.append(ResultadoDia(data=dia, entrada=None, saida=None,
                horas_trabalhadas_min=0, saldo_min=0, atraso_min=0,
                recuperado_min=0, status=StatusDia.FOLGA))
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
    pdf_bytes = gerar_pdf_espelho(func, resultados, resumo, mes, ano, nome_empresa)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"espelho_{func.matricula}_{mes:02d}_{ano}.pdf",
    )


@admin_bp.route("/relatorios/excel")
def relatorio_excel():
    import calendar
    from datetime import date as dt_date
    from ..time_service import ConfigSnapshot, calcular_dia, calcular_mes, StatusDia, ResultadoDia
    from ..report_service import gerar_excel_consolidado

    mes = request.args.get("mes", datetime.utcnow().month, type=int)
    ano = request.args.get("ano", datetime.utcnow().year, type=int)
    depto = request.args.get("departamento", "")

    cfg = ConfigSnapshot.from_model(Configuracao.get())
    nome_empresa = Configuracao.get().nome_empresa or ""
    _, total_dias = calendar.monthrange(ano, mes)
    dias_do_mes = [dt_date(ano, mes, d) for d in range(1, total_dias + 1)]
    dias_uteis_count = sum(1 for d in dias_do_mes if d.isoweekday() in cfg.dias_uteis)

    feriados_db = Feriado.query.filter(
        db.extract("month", Feriado.data) == mes,
        db.extract("year", Feriado.data) == ano).all()
    feriados_set = {f.data for f in feriados_db}
    for fr in Feriado.query.filter_by(recorrente_anual=True).all():
        try:
            feriados_set.add(dt_date(ano, fr.data.month, fr.data.day))
        except ValueError:
            pass

    q = Funcionario.query.filter_by(ativo=True)
    if depto:
        q = q.filter_by(departamento=depto)
    funcionarios = q.order_by(Funcionario.nome).all()

    agora_local = datetime.now()
    hoje_local = agora_local.date()
    dados_consolidados = []
    for func in funcionarios:
        pontos_mes = (Ponto.query
            .filter(Ponto.funcionario_id == func.id,
                    db.extract("month", Ponto.data_hora) == mes,
                    db.extract("year", Ponto.data_hora) == ano)
            .order_by(Ponto.data_hora).all())

        pontos_por_dia = {}
        for p in pontos_mes:
            pontos_por_dia.setdefault(p.data_hora.date(), []).append(p)

        just_por_dia = {j.data: j.tipo for j in Justificativa.query.filter(
            Justificativa.funcionario_id == func.id,
            db.extract("month", Justificativa.data) == mes,
            db.extract("year", Justificativa.data) == ano).all()}

        resultados = []
        for dia in dias_do_mes:
            if dia > hoje_local or (dia == hoje_local and agora_local.time() < cfg.horario_entrada):
                continue
            if func.data_admissao and dia < func.data_admissao:
                continue
            if dia.isoweekday() not in cfg.dias_uteis:
                resultados.append(ResultadoDia(data=dia, entrada=None, saida=None,
                    horas_trabalhadas_min=0, saldo_min=0, atraso_min=0,
                    recuperado_min=0, status=StatusDia.FOLGA))
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
        dias_trab = sum(1 for r in resultados if r.horas_trabalhadas_min > 0)
        dados_consolidados.append({
            "matricula": func.matricula, "nome": func.nome,
            "departamento": func.departamento or "",
            "dias_trabalhados": dias_trab,
            "total_trabalhado_min": resumo.total_trabalhado_min,
            "total_previsto_min": resumo.total_previsto_min,
            "saldo_min": resumo.saldo_min,
            "atrasos": resumo.atrasos, "faltas": resumo.faltas,
            "faltas_justificadas": resumo.faltas_justificadas,
        })

    excel_bytes = gerar_excel_consolidado(dados_consolidados, mes, ano, nome_empresa, feriados_db)
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"consolidado_{mes:02d}_{ano}.xlsx",
    )


@admin_bp.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    from datetime import time as dtime
    cfg = Configuracao.get()

    if request.method == "POST":
        acao = request.form.get("acao", "config")

        if acao == "config":
            def parse_time(s: str):
                try:
                    h, m = map(int, s.split(":"))
                    return dtime(h, m)
                except Exception:
                    return None

            he = parse_time(request.form.get("horario_entrada", "07:00"))
            hs = parse_time(request.form.get("horario_saida", "17:00"))
            if he:
                cfg.horario_entrada = he
            if hs:
                cfg.horario_saida = hs
            cfg.tolerancia_atraso_min = int(request.form.get("tolerancia_atraso_min", 10))
            cfg.limite_recuperacao_min = int(request.form.get("limite_recuperacao_min", 120))
            cfg.dias_uteis = request.form.get("dias_uteis", "1,2,3,4,5")
            cfg.nome_empresa = request.form.get("nome_empresa", "").strip()
            cfg.threshold_reconhecimento = float(request.form.get("threshold_reconhecimento", 0.6))
            cfg.salvar_foto_captura = request.form.get("salvar_foto_captura") == "on"
            cfg.retencao_fotos_dias = int(request.form.get("retencao_fotos_dias", 30))

            logo = request.files.get("logo_empresa")
            if logo and logo.filename:
                from ..utils.helpers import allowed_file, save_upload
                from flask import current_app
                if allowed_file(logo.filename, current_app.config["ALLOWED_LOGO_EXTENSIONS"]):
                    cfg.logo_empresa = save_upload(logo, "logo")

            db.session.commit()
            flash("Configurações salvas.", "success")

        elif acao == "senha":
            senha_atual = request.form.get("senha_atual", "")
            nova = request.form.get("nova_senha", "")
            confirmar = request.form.get("confirmar_senha", "")
            if not current_user.check_password(senha_atual):
                flash("Senha atual incorreta.", "danger")
            elif len(nova) < 8:
                flash("Nova senha deve ter no mínimo 8 caracteres.", "danger")
            elif nova != confirmar:
                flash("As senhas não coincidem.", "danger")
            else:
                current_user.set_password(nova)
                db.session.commit()
                flash("Senha alterada com sucesso.", "success")

        return redirect(url_for("admin.configuracoes"))

    return render_template("admin/configuracoes/index.html", cfg=cfg)


@admin_bp.route("/configuracoes/backup")
def backup():
    import os
    from flask import current_app
    db_path = os.path.join(current_app.instance_path, "ponto.db")
    hoje = datetime.utcnow().strftime("%Y-%m-%d")
    return send_file(db_path, as_attachment=True,
                     download_name=f"ponto_backup_{hoje}.db",
                     mimetype="application/octet-stream")
