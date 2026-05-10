import os
import click
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from .models import db, UsuarioAdmin, Configuracao
from config import config

migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, "uploads"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str) -> UsuarioAdmin | None:
        return UsuarioAdmin.query.get(int(user_id))

    # Blueprints
    from .routes.public import public_bp
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/admin/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Inicializa encodings cache
    with app.app_context():
        from . import encodings_cache
        encodings_cache.load_all()
        _limpar_fotos_antigas(app)

    # CLI commands
    _register_cli(app)

    return app


def _limpar_fotos_antigas(app: Flask) -> None:
    """Remove fotos de captura além da retenção configurada."""
    import glob
    from datetime import datetime, timedelta
    try:
        cfg = Configuracao.get()
        if not cfg.salvar_foto_captura:
            return
        cutoff = datetime.utcnow() - timedelta(days=cfg.retencao_fotos_dias)
        pattern = os.path.join(app.instance_path, "uploads", "capturas", "**", "*.jpg")
        for path in glob.glob(pattern, recursive=True):
            if datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
                os.remove(path)
    except Exception:
        pass


def _register_cli(app: Flask) -> None:
    @app.cli.command("criar-admin")
    @click.option("--username", prompt="Username")
    @click.option("--nome", prompt="Nome completo")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def criar_admin(username: str, nome: str, password: str) -> None:
        """Cria o primeiro (ou adicional) usuário administrador."""
        with app.app_context():
            if UsuarioAdmin.query.filter_by(username=username).first():
                click.echo(f"Erro: username '{username}' já existe.")
                return
            admin = UsuarioAdmin(username=username, nome=nome)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin '{username}' criado com sucesso.")

    @app.cli.command("seed")
    def seed() -> None:
        """Insere admin de teste e 3 funcionários fake (sem encoding)."""
        from datetime import date
        admin = UsuarioAdmin(username="admin", nome="Administrador")
        admin.set_password("admin123")
        db.session.add(admin)

        from .models import Funcionario
        for i in range(1, 4):
            f = Funcionario(
                nome=f"Funcionário Teste {i}",
                cpf=f"000.000.00{i}-0{i}",
                matricula=f"F00{i}",
                cargo="Operador",
                departamento="Produção",
                data_admissao=date(2023, 1, i),
            )
            db.session.add(f)

        db.session.commit()
        click.echo("Seed concluído: 1 admin + 3 funcionários fake inseridos.")
