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
