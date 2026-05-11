import json
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from ..models import db, UsuarioAdmin, AuditLog

auth_bp = Blueprint("auth", __name__)


def _log(admin_id: int, acao: str, detalhes: dict) -> None:
    db.session.add(AuditLog(usuario_id=admin_id, acao=acao, detalhes=json.dumps(detalhes, ensure_ascii=False)))
    db.session.commit()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if UsuarioAdmin.query.count() == 0:
        return redirect(url_for("auth.setup"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = UsuarioAdmin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin, remember=False)
            _log(admin.id, "login", {"username": username})
            return redirect(url_for("admin.dashboard"))
        flash("Usuário ou senha inválidos.", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    from flask_login import current_user
    _log(current_user.id, "logout", {})
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if UsuarioAdmin.query.count() > 0:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nome = request.form.get("nome", "").strip()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar", "")
        erros = []
        if not username:
            erros.append("Username obrigatório.")
        if not nome:
            erros.append("Nome obrigatório.")
        if len(password) < 8:
            erros.append("Senha deve ter no mínimo 8 caracteres.")
        if password != confirmar:
            erros.append("As senhas não coincidem.")
        if erros:
            for e in erros:
                flash(e, "danger")
        else:
            admin = UsuarioAdmin(username=username, nome=nome)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            login_user(admin)
            flash("Administrador criado com sucesso!", "success")
            return redirect(url_for("admin.dashboard"))
    return render_template("auth/setup.html")
