# Sistema de Ponto com Reconhecimento Facial

Aplicação Flask para controle de ponto via reconhecimento facial. Modo totem/quiosque local em Windows.

## Pré-requisitos

- Python 3.10
- CMake (necessário para compilar dlib no Windows)
- Visual Studio Build Tools 2022 com "Desenvolvimento para desktop com C++"

### Instalação do dlib no Windows (parte mais crítica)

1. Instale CMake: https://cmake.org/download/
2. Instale Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/#build-tools
3. Abra o "Developer Command Prompt for VS 2022"
4. Execute: `pip install dlib` (pode levar 5–15 minutos)
5. Execute: `pip install face_recognition`

**Alternativa mais rápida — wheel pré-compilado:**
```
pip install https://github.com/jloh02/dlib/releases/download/v19.22/dlib-19.22.0-cp311-cp311-win_amd64.whl
pip install face_recognition
```

### Linux/Mac

```bash
sudo apt-get install cmake libopenblas-dev  # Ubuntu/Debian
pip install dlib face_recognition
```

## Instalação

```bash
git clone <repo-url>
cd ponto_facial
python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate      # Linux/Mac
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
# Editar .env e definir SECRET_KEY com valor aleatório seguro
```

## Inicializar banco de dados

```bash
flask db upgrade
```

## Criar administrador inicial

```bash
flask criar-admin
# Ou acesse http://localhost:5000/admin/auth/setup no navegador
```

## Executar

```bash
# Desenvolvimento
flask run

# Produção local (Windows, usa Waitress)
python run.py
```

## Dados de teste (seed)

```bash
flask seed
# Cria: admin/admin123 + 3 funcionários de teste (sem encoding facial)
```

## Backup

Admin → Configurações → "Baixar ponto.db" — ou acesse `/admin/configuracoes/backup`.

## Troubleshooting

**`No module named 'face_recognition'`**
→ Instale dlib primeiro (veja instruções acima).

**`OSError: [WinError 126]` ao importar dlib**
→ Instale o [Visual C++ Redistributable 2022](https://aka.ms/vs/17/release/vc_redist.x64.exe).

**Câmera não funciona no navegador**
→ Use `http://localhost:5000` — câmera só funciona em localhost ou HTTPS.

**`face_recognition` muito lento**
→ HOG (padrão) é adequado para uso local. Para GPU: substitua `model="hog"` por `model="cnn"` em `face_service.py`.

**`flask db upgrade` falha**
→ Verifique se `FLASK_APP=run.py` está no `.env` ou defina via `set FLASK_APP=run.py` (Windows).

## Requisitos Futuros (não implementados)

- Liveness detection (anti-spoofing)
- Múltiplos níveis de admin (RH, gerente)
- App mobile complementar
- Integração com folha de pagamento
- Banco de horas com saldo positivo (hora extra)
- Múltiplas escalas/turnos por funcionário
- Reconhecimento contínuo (sem clicar em capturar)
