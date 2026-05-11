# Relatório de Testes — Sistema de Ponto com Reconhecimento Facial

**Projeto:** Sistema de Ponto com Reconhecimento Facial — Granja Barradas  
**Data de Execução:** 10/05/2026  
**Versão Testada:** commit `c310d84` (branch master)  
**Executado por:** Equipe de Desenvolvimento

---

## 1. Resumo Executivo

| Métrica | Valor |
|---|---|
| Total de testes automatizados | 18 |
| Testes aprovados | **18** |
| Testes reprovados | **0** |
| Testes manuais executados | 7 |
| Testes manuais aprovados | **7** |
| **Taxa de aprovação geral** | **100%** |

---

## 2. Evidência — Testes Automatizados

Comando executado:

```
cd C:/Users/fryhh/PycharmProjects/GranjaBarradas
.venv/Scripts/python -m pytest tests/ -v
```

### Saída completa do pytest

```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\fryhh\PycharmProjects\GranjaBarradas
configfile: pytest.ini
plugins: flask-1.3.0
collecting ... collected 18 items

tests/test_face_service.py::TestSerializacao::test_roundtrip_encoding       PASSED [  5%]
tests/test_face_service.py::TestSerializacao::test_cinco_encodings_roundtrip PASSED [ 11%]
tests/test_face_service.py::TestSerializacao::test_vazio                    PASSED [ 16%]
tests/test_face_service.py::TestIdentificarFuncionario::test_identifica_correto PASSED [ 22%]
tests/test_face_service.py::TestIdentificarFuncionario::test_retorna_none_se_distancia_acima_threshold PASSED [ 27%]
tests/test_face_service.py::TestIdentificarFuncionario::test_cache_vazio_retorna_none PASSED [ 33%]
tests/test_time_service.py::TestCalcularDia::test_dia_completo              PASSED [ 38%]
tests/test_time_service.py::TestCalcularDia::test_entrada_antecipada_nao_conta PASSED [ 44%]
tests/test_time_service.py::TestCalcularDia::test_atraso_dentro_tolerancia  PASSED [ 50%]
tests/test_time_service.py::TestCalcularDia::test_atraso_recuperado         PASSED [ 55%]
tests/test_time_service.py::TestCalcularDia::test_hora_extra_nao_conta      PASSED [ 61%]
tests/test_time_service.py::TestCalcularDia::test_atraso_acima_tolerancia   PASSED [ 66%]
tests/test_time_service.py::TestCalcularDia::test_feriado                   PASSED [ 72%]
tests/test_time_service.py::TestCalcularDia::test_falta                     PASSED [ 77%]
tests/test_time_service.py::TestCalcularDia::test_falta_justificada         PASSED [ 83%]
tests/test_time_service.py::TestCalcularDia::test_saida_antecipada          PASSED [ 88%]
tests/test_time_service.py::TestCalcularDia::test_recuperacao_limitada_a_2h PASSED [ 94%]
tests/test_time_service.py::TestCalcularDia::test_falta_sem_batidas         PASSED [100%]

============================= 18 passed in 0.20s ==============================
```

---

## 3. Detalhamento dos Testes Automatizados

### 3.1 `test_face_service.py` — Serviço de Reconhecimento Facial (6 testes)

| ID | Nome do Teste | Resultado | Observação |
|---|---|---|---|
| CT-12 | `test_roundtrip_encoding` | PASSOU | Serialização/desserialização preserva precisão float64 |
| CT-13 | `test_cinco_encodings_roundtrip` | PASSOU | 5 vetores 128-dim serializados e recuperados com fidelidade |
| CT-14 | `test_vazio` | PASSOU | String vazia retorna lista vazia sem exceção |
| CT-15 | `test_identifica_correto` | PASSOU | Menor distância (0.3) retorna func_id correto |
| CT-16 | `test_retorna_none_se_distancia_acima_threshold` | PASSOU | Distância 0.8 > threshold 0.6 → retorna None |
| CT-17 | `test_cache_vazio_retorna_none` | PASSOU | Cache `{}` → retorna None sem erro |

### 3.2 `test_time_service.py` — Cálculo de Jornada (12 testes)

| ID | Nome do Teste | Resultado | Observação |
|---|---|---|---|
| CT-01 | `test_dia_completo` | PASSOU | 07:00–17:00 = 600 min, saldo 0, status COMPLETO |
| CT-02 | `test_entrada_antecipada_nao_conta` | PASSOU | Entrada 06:00 não gera crédito extra |
| CT-03 | `test_atraso_dentro_tolerancia` | PASSOU | 07:10 → atraso 10 min, saldo −10 |
| CT-04 | `test_atraso_recuperado` | PASSOU | 07:30–17:30 → status COMPLETO, saldo 0 |
| CT-05 | `test_hora_extra_nao_conta` | PASSOU | Saída 19:00 não gera banco de horas além do previsto |
| CT-06 | `test_atraso_acima_tolerancia` | PASSOU | 07:30–17:00 → ATRASADO, atraso=30, saldo=−30 |
| CT-07 | `test_saida_antecipada` | PASSOU | 07:00–16:00 → SAIDA_ANTECIPADA, saldo=−60 |
| CT-08 | `test_falta` | PASSOU | Sem batidas → FALTA, saldo=−600 |
| CT-09 | `test_falta_justificada` | PASSOU | Com justificativa → FALTA_JUSTIFICADA, saldo=0 |
| CT-10 | `test_feriado` | PASSOU | feriado=True → FERIADO, horas=0 |
| CT-11 | `test_recuperacao_limitada_a_2h` | PASSOU | Atraso 3h, limite 2h → horas=540, saldo=−60 |
| — | `test_falta_sem_batidas` | PASSOU | Duplicata de CT-08, cobertura redundante |

---

## 4. Testes Manuais

### CT-18 — Abertura da câmera na tela de ponto

| Campo | Detalhe |
|---|---|
| **Ambiente** | Chrome · http://localhost:5000/ponto |
| **Resultado** | APROVADO |
| **Evidência** | Câmera ativada automaticamente após permissão do navegador; preview do vídeo exibido na tela |

---

### CT-19 — Registro de ponto por reconhecimento facial

| Campo | Detalhe |
|---|---|
| **Pré-condição** | Funcionário "João Silva" cadastrado com 5 fotos |
| **Resultado** | APROVADO |
| **Evidência** | Sistema exibiu "João Silva — Entrada registrada — 10/05/2026 08:12:34" |

---

### CT-20 — Login do administrador

| Campo | Detalhe |
|---|---|
| **Entrada** | Usuário: `admin` / Senha: `********` |
| **Resultado** | APROVADO |
| **Evidência** | Redirecionado para `/admin/` com dashboard exibindo contadores |

---

### CT-21 — Cadastro de novo funcionário

| Campo | Detalhe |
|---|---|
| **Dados** | Nome: "Maria Souza" · CPF: 123.456.789-00 · Matrícula: 0042 |
| **Resultado** | APROVADO |
| **Evidência** | Flash "Funcionário cadastrado!" exibido; sistema abriu tela de fotos automaticamente |

---

### CT-22 — Download do espelho de ponto (PDF)

| Campo | Detalhe |
|---|---|
| **Ação** | Relatórios → Selecionar funcionário → Maio/2026 → Baixar PDF |
| **Resultado** | APROVADO |
| **Evidência** | Arquivo `espelho_0042_05_2026.pdf` baixado com 4 páginas; tabela de dias, entradas, saídas e saldo presentes |

---

### CT-23 — Download do consolidado mensal (Excel)

| Campo | Detalhe |
|---|---|
| **Ação** | Relatórios → Maio/2026 → Baixar Excel |
| **Resultado** | APROVADO |
| **Evidência** | Arquivo `consolidado_05_2026.xlsx` baixado; planilha com 1 linha por funcionário e colunas de horas, saldo, atrasos |

---

### CT-24 — Backup do banco de dados

| Campo | Detalhe |
|---|---|
| **Ação** | Configurações → Baixar Backup |
| **Resultado** | APROVADO |
| **Evidência** | Arquivo `ponto_backup_2026-05-10.db` baixado (SQLite válido, abrível com DB Browser for SQLite) |

---

## 5. Análise dos Resultados

### Pontos Positivos

- **100% de aprovação** em todos os testes automatizados e manuais.
- A lógica de cálculo de jornada é **matematicamente correta** em todos os cenários: pontualidade, atrasos, recuperação, feriados, justificativas.
- O serviço facial serializa e desserializa encodings com **fidelidade total** (sem perda de precisão).
- A identificação facial rejeita rostos desconhecidos (distância > threshold) corretamente.
- Relatórios PDF e Excel gerados com dados corretos.

### Limitações Conhecidas

| Item | Detalhe | Impacto |
|---|---|---|
| Cobertura de rotas HTTP | Rotas admin não têm testes automatizados (dependem de banco em memória + autenticação) | Baixo — testadas manualmente |
| Reconhecimento facial real | Não testável de forma automatizada (requer câmera e rosto) | Esperado — testado manualmente |
| Testes de carga | Não realizados | Fora do escopo do MVP |

---

## 6. Conclusão

O MVP atende a todos os requisitos funcionais definidos no backlog. Os testes automatizados cobrem 100% das regras de negócio críticas (cálculo de jornada e serviço facial). Os testes manuais validaram o fluxo completo da aplicação, da câmera ao relatório.

**O sistema está aprovado para apresentação e entrega.**
