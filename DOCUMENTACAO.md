# Documentação Técnica — Sistema de Ponto com Reconhecimento Facial

## Visão Geral

Aplicação web Flask para controle de ponto de funcionários via reconhecimento facial. O funcionário se posiciona diante de uma câmera conectada ao navegador; o rosto é identificado automaticamente e a batida (entrada ou saída) é registrada no banco de dados SQLite local.

---

## Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.x + Flask |
| Banco de dados | SQLite (via Flask-SQLAlchemy + Flask-Migrate) |
| Reconhecimento facial | `face_recognition` (dlib HOG/CNN) |
| Autenticação | Flask-Login |
| PDF | ReportLab |
| Excel | openpyxl |
| Frontend | Jinja2 + Tailwind CSS (CDN) |

---

## Estrutura de Arquivos

```
GranjaBarradas/
├── run.py                        # Ponto de entrada
├── requirements.txt
├── app/
│   ├── __init__.py               # Factory da aplicação, registro de blueprints
│   ├── models.py                 # Modelos SQLAlchemy
│   ├── face_service.py           # Extração e comparação de encodings faciais
│   ├── encodings_cache.py        # Cache em memória dos encodings ativos
│   ├── time_service.py           # Cálculo de horas, saldo, atrasos
│   ├── report_service.py         # Geração de PDF e Excel
│   ├── utils/helpers.py          # Upload de arquivos, salvar foto de captura
│   └── routes/
│       ├── public.py             # Rotas públicas (sem login)
│       ├── auth.py               # Login / logout / setup inicial
│       ├── admin.py              # Painel administrativo (requer login)
│       └── api.py                # API JSON (reconhecimento + consulta)
└── app/templates/
    ├── base_public.html / base_admin.html
    ├── public/  (index, ponto, consulta, privacidade)
    └── admin/   (dashboard, funcionarios, pontos, justificativas, feriados, relatorios, configuracoes)
```

---

## Banco de Dados — Modelos

### `funcionarios`
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer PK | |
| nome | String(120) | Nome completo |
| cpf | String(14) | Único, formato 000.000.000-00 |
| matricula | String(20) | Único |
| cargo | String(80) | Opcional |
| departamento | String(80) | Opcional |
| data_admissao | Date | Opcional |
| face_encodings | Text | JSON com array de vetores 128-dim (dlib) |
| foto_perfil | String(255) | Caminho relativo a `instance/uploads/` |
| ativo | Boolean | Controla acesso ao sistema |

### `pontos`
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer PK | |
| funcionario_id | FK → funcionarios | |
| tipo | String(10) | `'entrada'` ou `'saida'` |
| data_hora | DateTime | Momento da batida |
| data_hora_original | DateTime | Preenchido quando admin edita |
| editado_por_admin | Boolean | Flag de auditoria |
| justificativa | Text | Motivo da edição manual |
| foto_registro | String(255) | Foto salva na captura (opcional) |

### `feriados`
| Campo | Tipo | Descrição |
|---|---|---|
| data | Date | Único por data |
| descricao | String(120) | Ex.: "Natal" |
| recorrente_anual | Boolean | Se True, repete todo ano |

### `justificativas`
| Campo | Tipo | Descrição |
|---|---|---|
| funcionario_id | FK | |
| data | Date | Data da ausência |
| motivo | Text | Descrição |
| tipo | String(30) | `falta_justificada` / `atestado` / `folga` / `outro` |
| created_by | FK → usuarios_admin | |

### `configuracoes` (singleton, id=1)
| Campo | Tipo | Padrão |
|---|---|---|
| horario_entrada | Time | 07:00 |
| horario_saida | Time | 17:00 |
| tolerancia_atraso_min | Integer | 10 min |
| limite_recuperacao_min | Integer | 120 min |
| dias_uteis | String | "1,2,3,4,5" (Seg–Sex) |
| nome_empresa | String | — |
| logo_empresa | String | Caminho da imagem |
| threshold_reconhecimento | Float | 0.6 |
| salvar_foto_captura | Boolean | False |
| retencao_fotos_dias | Integer | 30 dias |

### `usuarios_admin`
Usuários do painel administrativo. Senha armazenada como hash (Werkzeug).

### `audit_log`
Registro de ações sensíveis: login, logout, edição/exclusão/adição manual de ponto.

---

## Blueprints e Rotas

### Public (`/`)
| Rota | Função |
|---|---|
| `GET /` | Página inicial |
| `GET /ponto` | Tela de reconhecimento facial para batida |
| `GET /consulta` | Tela de consulta de horas via face |
| `GET /privacidade` | Política de privacidade |

### Auth (`/admin/auth`)
| Rota | Função |
|---|---|
| `GET/POST /login` | Login do administrador |
| `POST /logout` | Logout |
| `GET/POST /setup` | Criação do primeiro admin (só acessível se não há admin cadastrado) |

### API (`/api`) — JSON, sem login
| Rota | Payload | Retorno |
|---|---|---|
| `POST /reconhecer` | `{imagem: base64, modo: "ponto"/"consulta"}` | Nome, tipo de batida, data_hora |
| `POST /dados-funcionario` | `{funcionario_id, mes, ano}` | Espelho de ponto do mês em JSON |

### Admin (`/admin`) — requer login
| Rota | Função |
|---|---|
| `GET /` | Dashboard (totais, últimas batidas, gráfico 30 dias) |
| `GET /funcionarios` | Listagem com busca, filtro depto/status, paginação |
| `GET/POST /funcionarios/novo` | Cadastro de funcionário |
| `GET/POST /funcionarios/<id>/editar` | Edição de dados e foto de perfil |
| `GET/POST /funcionarios/<id>/fotos` | Captura de 5 fotos para treinar reconhecimento |
| `POST /funcionarios/<id>/desativar` | Desativa funcionário e invalida cache |
| `GET /pontos` | Listagem de batidas filtrada por mês/ano/funcionário/depto |
| `POST /pontos/<id>/editar` | Edita batida (registra audit log) |
| `POST /pontos/adicionar` | Adiciona batida manual (registra audit log) |
| `POST /pontos/<id>/excluir` | Exclui batida (registra audit log) |
| `GET /justificativas` | Listagem de justificativas |
| `POST /justificativas/nova` | Cria justificativa (sobrescreve se já existe no mesmo dia) |
| `POST /justificativas/<id>/excluir` | Remove justificativa |
| `GET /feriados` | Listagem de feriados |
| `POST /feriados/novo` | Cadastra feriado |
| `POST /feriados/<id>/excluir` | Remove feriado |
| `GET /relatorios` | Tela de geração de relatórios |
| `GET /relatorios/pdf` | Download do espelho de ponto (PDF, por funcionário/mês) |
| `GET /relatorios/excel` | Download do consolidado mensal (Excel, todos/depto) |
| `GET/POST /configuracoes` | Configurações gerais e troca de senha |
| `GET /configuracoes/backup` | Download do arquivo `ponto.db` |

---

## Serviços Internos

### `face_service.py`
- `extrair_encoding_de_base64(b64)` → decodifica imagem PNG/JPEG em base64, detecta rosto com dlib HOG, retorna vetor 128-dim. Lança `NenhumRostoError`, `MultiplosRostosError` ou `ImagemInvalidaError`.
- `identificar_funcionario(encoding, encodings_cache, threshold)` → compara com todos os encodings em memória; retorna `funcionario_id` ou `None`.
- `serializar_encodings / deserializar_encodings` → JSON ↔ lista de numpy arrays.

### `encodings_cache.py`
Cache em memória (`dict[int, list[np.ndarray]]`) carregado na inicialização. Métodos: `get_all()`, `reload(func_id)`, `invalidate(func_id)`.

### `time_service.py`
- `ConfigSnapshot` — snapshot imutável das configurações de jornada.
- `calcular_dia(entrada, saida, cfg, feriado, justificativa, data)` → `ResultadoDia` com horas trabalhadas, saldo, atraso, status (`PRESENTE`, `FALTA`, `FERIADO`, `FOLGA`, `FALTA_JUSTIFICADA`, `ATESTADO`).
- `calcular_mes(resultados, dias_uteis_count)` → `ResumoMes` com totais.

### `report_service.py`
- `gerar_pdf_espelho(func, resultados, resumo, mes, ano, nome_empresa)` → bytes do PDF (espelho individual).
- `gerar_excel_consolidado(dados, mes, ano, nome_empresa, feriados)` → bytes do XLSX (todos os funcionários).

---

## Fluxo de Reconhecimento Facial

```
Navegador captura frame da câmera
    → envia base64 via POST /api/reconhecer
        → face_service extrai encoding
        → compara com encodings_cache
        → identifica funcionario_id
        → determina tipo (entrada/saida) pelo último ponto do dia
        → salva Ponto no banco
        → retorna nome, tipo, data_hora
            → navegador exibe confirmação
```

---

## Configuração e Inicialização

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar .env
FLASK_APP=run.py
SECRET_KEY=<chave-secreta>

# 3. Criar tabelas
flask db upgrade

# 4. Iniciar
flask run
# ou
python run.py

# 5. Primeiro acesso → /admin/auth/setup para criar o administrador
```

---

## Considerações de Segurança

- Todas as rotas `/admin/*` exigem autenticação via Flask-Login.
- Ações sensíveis (editar/excluir/adicionar ponto) são gravadas em `audit_log` com usuário, ação e contexto JSON.
- A câmera só funciona via `http://localhost` ou HTTPS (restrição do navegador).
- Threshold de reconhecimento configurável (padrão 0.6); valores menores = mais restritivo.
- Senhas armazenadas com hash Werkzeug (PBKDF2-SHA256).
