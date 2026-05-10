from datetime import datetime, date, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Funcionario(db.Model):
    __tablename__ = "funcionarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)  # 000.000.000-00
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    cargo = db.Column(db.String(80))
    departamento = db.Column(db.String(80))
    data_admissao = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    face_encodings = db.Column(db.Text)  # JSON: list[list[float]] (5 arrays 128-dim)
    foto_perfil = db.Column(db.String(255))  # caminho relativo a instance/uploads/
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pontos = db.relationship("Ponto", backref="funcionario", lazy="dynamic")
    justificativas = db.relationship("Justificativa", backref="funcionario", lazy="dynamic")

    def __repr__(self):
        return f"<Funcionario {self.nome}>"


class Ponto(db.Model):
    __tablename__ = "pontos"
    __table_args__ = (
        db.Index("ix_pontos_func_data", "funcionario_id", "data_hora"),
        db.Index("ix_pontos_data_hora", "data_hora"),
    )

    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada' | 'saida'
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_hora_original = db.Column(db.DateTime)  # preenchido quando admin edita
    editado_por_admin = db.Column(db.Boolean, default=False)
    justificativa = db.Column(db.Text)
    foto_registro = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Ponto {self.tipo} {self.data_hora}>"


class Feriado(db.Model):
    __tablename__ = "feriados"
    __table_args__ = (db.Index("ix_feriados_data", "data"),)

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, unique=True, nullable=False)
    descricao = db.Column(db.String(120), nullable=False)
    recorrente_anual = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Feriado {self.data} {self.descricao}>"


class Justificativa(db.Model):
    __tablename__ = "justificativas"

    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # falta_justificada|atestado|folga|outro
    created_by = db.Column(db.Integer, db.ForeignKey("usuarios_admin.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("UsuarioAdmin", backref="justificativas_criadas")

    def __repr__(self):
        return f"<Justificativa {self.funcionario_id} {self.data}>"


class Configuracao(db.Model):
    __tablename__ = "configuracoes"

    id = db.Column(db.Integer, primary_key=True, default=1)
    horario_entrada = db.Column(db.Time, default=time(7, 0))
    horario_saida = db.Column(db.Time, default=time(17, 0))
    tolerancia_atraso_min = db.Column(db.Integer, default=10)
    limite_recuperacao_min = db.Column(db.Integer, default=120)
    dias_uteis = db.Column(db.String(20), default="1,2,3,4,5")  # 1=seg..5=sex
    nome_empresa = db.Column(db.String(120), default="")
    logo_empresa = db.Column(db.String(255))
    threshold_reconhecimento = db.Column(db.Float, default=0.6)
    salvar_foto_captura = db.Column(db.Boolean, default=False)
    retencao_fotos_dias = db.Column(db.Integer, default=30)

    @staticmethod
    def get():
        cfg = Configuracao.query.get(1)
        if cfg is None:
            cfg = Configuracao(id=1)
            db.session.add(cfg)
            db.session.commit()
        return cfg


class UsuarioAdmin(UserMixin, db.Model):
    __tablename__ = "usuarios_admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<UsuarioAdmin {self.username}>"


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios_admin.id"))
    acao = db.Column(db.String(80), nullable=False)
    detalhes = db.Column(db.Text)  # JSON string com contexto
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("UsuarioAdmin", backref="audit_logs")
