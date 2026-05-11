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
