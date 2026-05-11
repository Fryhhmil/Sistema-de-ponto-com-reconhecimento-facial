from flask import Blueprint, render_template
from ..models import Configuracao

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def index():
    return render_template("public/index.html", cfg=Configuracao.get())

@public_bp.route("/privacidade")
def privacidade():
    return render_template("public/privacidade.html", cfg=Configuracao.get())

@public_bp.route("/ponto")
def ponto():
    return render_template("public/ponto.html", cfg=Configuracao.get())

@public_bp.route("/consulta")
def consulta():
    return render_template("public/consulta.html", cfg=Configuracao.get())
