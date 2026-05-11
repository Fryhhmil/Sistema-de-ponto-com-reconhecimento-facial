# Plano de Testes — Sistema de Ponto com Reconhecimento Facial

**Projeto:** Sistema de Ponto com Reconhecimento Facial — Granja Barradas  
**Data:** 10/05/2026  
**Versão:** 1.0  
**Responsáveis:** Equipe de Desenvolvimento

---

## 1. Objetivo

Validar que as funcionalidades implementadas no MVP funcionam corretamente, são estáveis e atendem aos requisitos definidos no backlog do projeto.

---

## 2. Escopo dos Testes

### 2.1 O que será testado

| Módulo | Tipo de Teste |
|---|---|
| Cálculo de jornada (`time_service`) | Unitário |
| Serialização facial (`face_service`) | Unitário |
| Identificação facial (`face_service`) | Unitário com mock |
| Rotas públicas e administrativas | Integração (Flask test client) |
| Registro de ponto via API | Integração |

### 2.2 O que NÃO será testado

- Qualidade do reconhecimento facial em ambiente real (depende de hardware)
- Performance com centenas de usuários simultâneos
- Compatibilidade com todos os navegadores

---

## 3. Ambiente de Testes

- **SO:** Windows 11 Pro
- **Python:** 3.10.11
- **Framework de testes:** pytest 8.3.4 + pytest-flask 1.3.0
- **Banco:** SQLite em memória (`:memory:`) para testes de integração
- **Biblioteca facial:** `face_recognition` mockada nos testes unitários
- **Comando:** `pytest tests/ -v`

---

## 4. Casos de Teste

### 4.1 Módulo: Cálculo de Jornada (`time_service`)

**Configuração base:** Entrada 07:00 · Saída 17:00 · Tolerância 10 min · Recuperação máx. 120 min · Dias úteis Seg–Sex

---

#### CT-01 — Dia completo no horário

| Campo | Valor |
|---|---|
| **ID** | CT-01 |
| **Pré-condição** | Configuração padrão ativa |
| **Entrada** | Entrada: 07:00 / Saída: 17:00 |
| **Ação** | Chamar `calcular_dia()` |
| **Resultado Esperado** | Status = COMPLETO · Horas = 600 min · Saldo = 0 · Atraso = 0 |
| **Tipo** | Unitário |

---

#### CT-02 — Entrada antecipada não gera crédito

| Campo | Valor |
|---|---|
| **ID** | CT-02 |
| **Entrada** | Entrada: 06:00 / Saída: 17:00 |
| **Resultado Esperado** | Horas = 600 min · Saldo = 0 (entrada antes do horário não conta) |
| **Tipo** | Unitário |

---

#### CT-03 — Atraso dentro da tolerância

| Campo | Valor |
|---|---|
| **ID** | CT-03 |
| **Entrada** | Entrada: 07:10 / Saída: 17:00 |
| **Resultado Esperado** | Atraso = 10 min · Saldo = −10 min |
| **Tipo** | Unitário |

---

#### CT-04 — Atraso recuperado com horas extras

| Campo | Valor |
|---|---|
| **ID** | CT-04 |
| **Entrada** | Entrada: 07:30 / Saída: 17:30 |
| **Resultado Esperado** | Status = COMPLETO · Horas = 600 · Saldo = 0 |
| **Tipo** | Unitário |

---

#### CT-05 — Hora extra não conta além do previsto

| Campo | Valor |
|---|---|
| **ID** | CT-05 |
| **Entrada** | Entrada: 07:00 / Saída: 19:00 |
| **Resultado Esperado** | Horas = 600 · Saldo = 0 (sem crédito de extra não autorizado) |
| **Tipo** | Unitário |

---

#### CT-06 — Atraso acima da tolerância

| Campo | Valor |
|---|---|
| **ID** | CT-06 |
| **Entrada** | Entrada: 07:30 / Saída: 17:00 |
| **Resultado Esperado** | Status = ATRASADO · Atraso = 30 · Saldo = −30 |
| **Tipo** | Unitário |

---

#### CT-07 — Saída antecipada

| Campo | Valor |
|---|---|
| **ID** | CT-07 |
| **Entrada** | Entrada: 07:00 / Saída: 16:00 |
| **Resultado Esperado** | Status = SAIDA_ANTECIPADA · Saldo = −60 |
| **Tipo** | Unitário |

---

#### CT-08 — Falta (sem batidas)

| Campo | Valor |
|---|---|
| **ID** | CT-08 |
| **Entrada** | Entrada: None / Saída: None / Justificativa: None |
| **Resultado Esperado** | Status = FALTA · Saldo = −600 · Horas = 0 |
| **Tipo** | Unitário |

---

#### CT-09 — Falta justificada (atestado)

| Campo | Valor |
|---|---|
| **ID** | CT-09 |
| **Entrada** | Entrada: None / Saída: None / Justificativa: "atestado" |
| **Resultado Esperado** | Status = FALTA_JUSTIFICADA · Saldo = 0 |
| **Tipo** | Unitário |

---

#### CT-10 — Feriado

| Campo | Valor |
|---|---|
| **ID** | CT-10 |
| **Entrada** | Feriado: True / Entrada: None / Saída: None |
| **Resultado Esperado** | Status = FERIADO · Horas = 0 · Saldo = 0 |
| **Tipo** | Unitário |

---

#### CT-11 — Recuperação limitada ao máximo configurado

| Campo | Valor |
|---|---|
| **ID** | CT-11 |
| **Entrada** | Entrada: 10:00 / Saída: 19:00 (atraso 3h, limite 2h) |
| **Resultado Esperado** | Horas = 540 · Saldo = −60 |
| **Tipo** | Unitário |

---

### 4.2 Módulo: Serviço Facial (`face_service`)

---

#### CT-12 — Serialização e desserialização de encoding

| Campo | Valor |
|---|---|
| **ID** | CT-12 |
| **Entrada** | Vetor numpy 128-dim |
| **Resultado Esperado** | Roundtrip JSON preserva valores (tolerância float64) |
| **Tipo** | Unitário |

---

#### CT-13 — Serialização de 5 encodings

| Campo | Valor |
|---|---|
| **ID** | CT-13 |
| **Entrada** | Lista com 5 vetores numpy distintos |
| **Resultado Esperado** | Desserialização retorna 5 vetores idênticos aos originais |
| **Tipo** | Unitário |

---

#### CT-14 — Desserialização de string vazia

| Campo | Valor |
|---|---|
| **ID** | CT-14 |
| **Entrada** | String vazia `""` |
| **Resultado Esperado** | Retorna lista vazia `[]` sem exceção |
| **Tipo** | Unitário |

---

#### CT-15 — Identificação correta de funcionário

| Campo | Valor |
|---|---|
| **ID** | CT-15 |
| **Entrada** | Cache com func_id=1 (dist=0.3) e func_id=2 (dist=0.8) · threshold=0.6 |
| **Resultado Esperado** | Retorna `1` (menor distância, abaixo do threshold) |
| **Tipo** | Unitário (mock face_recognition) |

---

#### CT-16 — Distância acima do threshold retorna None

| Campo | Valor |
|---|---|
| **ID** | CT-16 |
| **Entrada** | Cache com 1 funcionário · distância 0.8 · threshold 0.6 |
| **Resultado Esperado** | Retorna `None` (não reconhecido) |
| **Tipo** | Unitário (mock) |

---

#### CT-17 — Cache vazio retorna None

| Campo | Valor |
|---|---|
| **ID** | CT-17 |
| **Entrada** | Cache vazio `{}` |
| **Resultado Esperado** | Retorna `None` sem erro |
| **Tipo** | Unitário |

---

### 4.3 Testes Manuais — Interface Web

---

#### CT-18 — Tela de batida de ponto abre câmera

| Campo | Valor |
|---|---|
| **ID** | CT-18 |
| **Pré-condição** | Navegador com câmera · acesso via localhost |
| **Ação** | Acessar `/ponto` e permitir câmera |
| **Resultado Esperado** | Vídeo da câmera exibido, botão "Registrar Ponto" visível |
| **Tipo** | Manual |

---

#### CT-19 — Reconhecimento e registro de ponto

| Campo | Valor |
|---|---|
| **ID** | CT-19 |
| **Pré-condição** | Funcionário cadastrado com fotos |
| **Ação** | Clicar "Registrar Ponto" em `/ponto` |
| **Resultado Esperado** | Nome do funcionário exibido + tipo (entrada/saída) + horário |
| **Tipo** | Manual |

---

#### CT-20 — Login do administrador

| Campo | Valor |
|---|---|
| **ID** | CT-20 |
| **Entrada** | Usuário e senha válidos |
| **Resultado Esperado** | Redirecionado para `/admin/` com dashboard |
| **Tipo** | Manual |

---

#### CT-21 — Cadastro de funcionário

| Campo | Valor |
|---|---|
| **ID** | CT-21 |
| **Ação** | Preencher formulário em `/admin/funcionarios/novo` |
| **Resultado Esperado** | Funcionário salvo · redirecionado para captura de fotos |
| **Tipo** | Manual |

---

#### CT-22 — Download de relatório PDF

| Campo | Valor |
|---|---|
| **ID** | CT-22 |
| **Ação** | Selecionar funcionário + mês + clicar "Baixar PDF" |
| **Resultado Esperado** | Arquivo `.pdf` baixado com espelho do mês |
| **Tipo** | Manual |

---

#### CT-23 — Download de relatório Excel

| Campo | Valor |
|---|---|
| **ID** | CT-23 |
| **Ação** | Selecionar mês + clicar "Baixar Excel" |
| **Resultado Esperado** | Arquivo `.xlsx` baixado com consolidado de todos os funcionários |
| **Tipo** | Manual |

---

#### CT-24 — Backup do banco de dados

| Campo | Valor |
|---|---|
| **ID** | CT-24 |
| **Ação** | Acessar Configurações → Baixar Backup |
| **Resultado Esperado** | Arquivo `ponto_backup_<data>.db` baixado |
| **Tipo** | Manual |

---

## 5. Critérios de Aprovação

| Critério | Meta |
|---|---|
| Testes automatizados passando | 100% (0 falhas) |
| Cobertura das funcionalidades críticas | Todas as 24 CTs executadas |
| Funcionalidades bloqueantes com falha | 0 |

---

## 6. Ferramentas

| Ferramenta | Uso |
|---|---|
| pytest | Execução dos testes automatizados |
| pytest-flask | Fixture do app Flask em modo teste |
| unittest.mock | Mock da biblioteca `face_recognition` |
| numpy | Geração de encodings sintéticos |
| Navegador (Chrome/Edge) | Testes manuais da interface |
