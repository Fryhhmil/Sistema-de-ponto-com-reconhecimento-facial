# Manual do Usuário — Sistema de Ponto

## O que é este sistema?

Sistema de controle de ponto que usa **reconhecimento facial** pela câmera do computador. O funcionário olha para a câmera e o sistema registra automaticamente a entrada ou saída. Não é necessário cartão, senha ou biometria de impressão digital.

---

## Para o Funcionário

### Registrar Ponto (Entrada ou Saída)

1. Abra o navegador e acesse o endereço do sistema (ex.: `http://servidor:5000`).
2. Clique em **"Registrar Ponto"**.
3. Permita o acesso à câmera quando o navegador solicitar.
4. Posicione o rosto centralizado na tela, com boa iluminação.
5. Aguarde — o sistema reconhece automaticamente e exibe uma confirmação com seu nome e o horário registrado.

> **Dica:** Se o sistema não reconhecer, ajuste a iluminação e tente novamente. Se o problema persistir, procure o RH para verificar seu cadastro.

---

### Consultar Meu Espelho de Ponto

1. Na página inicial, clique em **"Consultar Meu Ponto"**.
2. Posicione o rosto na câmera para se identificar.
3. Após o reconhecimento, escolha o mês e ano desejado.
4. O sistema exibe o espelho completo: entradas, saídas, horas trabalhadas, saldo e faltas.

---

## Para o Administrador

### Primeiro Acesso

Na primeira vez que acessar o sistema, vá para `/admin/auth/setup` e crie o usuário administrador com nome, login e senha (mínimo 8 caracteres).

### Entrar no Painel

Acesse `/admin` e faça login com seu usuário e senha.

---

### Dashboard

Ao entrar no painel você verá:

- **Total de funcionários ativos**
- **Presentes hoje** (já registraram entrada)
- **Ausentes hoje**
- **Últimas 10 batidas** registradas no sistema
- **Gráfico dos últimos 30 dias** com volume de batidas

---

### Funcionários

#### Cadastrar novo funcionário

1. Vá em **Funcionários → Novo Funcionário**.
2. Preencha: Nome, CPF, Matrícula, Cargo, Departamento e Data de Admissão.
3. Clique em **Salvar**.
4. O sistema abre automaticamente a tela de captura de fotos.

#### Capturar fotos para reconhecimento

Após cadastrar (ou acessando **Funcionários → Fotos**):

1. O sistema solicita 5 fotos do rosto.
2. Peça ao funcionário para olhar para a câmera.
3. Clique em **Capturar** para cada foto — varie levemente o ângulo entre elas.
4. Clique em **Salvar Fotos**.

> O funcionário só consegue registrar ponto após as fotos serem salvas.

#### Editar funcionário

Em **Funcionários**, clique no ícone de edição ao lado do nome. Você pode alterar nome, cargo, departamento, data de admissão e foto de perfil.

#### Desativar funcionário

Clique em **Desativar** na linha do funcionário. Funcionários inativos não conseguem registrar ponto e não aparecem nos relatórios ativos.

---

### Pontos (Registros de Batida)

#### Visualizar batidas

Vá em **Pontos**. Filtre por:
- Mês e ano
- Funcionário específico
- Departamento

#### Editar uma batida

1. Clique no ícone de edição ao lado da batida.
2. Informe a nova data/hora e uma justificativa obrigatória.
3. Clique em **Salvar**. A alteração é registrada no log de auditoria.

#### Adicionar batida manual

Use quando o funcionário esqueceu de registrar ou houve falha na câmera:

1. Clique em **Adicionar Batida Manual**.
2. Selecione o funcionário, o tipo (Entrada ou Saída), data/hora e justificativa.
3. Clique em **Adicionar**.

#### Excluir batida

Clique no ícone de lixeira. A exclusão é registrada no log de auditoria.

---

### Justificativas de Ausência

Usadas para registrar faltas justificadas, atestados médicos ou folgas combinadas.

1. Vá em **Justificativas → Nova Justificativa**.
2. Selecione o funcionário, a data, o tipo e informe o motivo.

**Tipos disponíveis:**
- Falta Justificada
- Atestado Médico
- Folga
- Outro

> Uma justificativa por dia/funcionário. Cadastrar nova sobrescreve a anterior do mesmo dia.

---

### Feriados

1. Vá em **Feriados → Novo Feriado**.
2. Informe a data e a descrição (ex.: "Carnaval").
3. Marque **Recorrente Anual** para feriados que se repetem todo ano (ex.: Natal, Ano Novo).

Dias marcados como feriado não contam como falta nos relatórios.

---

### Relatórios

#### Espelho de Ponto Individual (PDF)

1. Vá em **Relatórios**.
2. Selecione o funcionário, mês e ano.
3. Clique em **Baixar PDF**.

O arquivo contém: todos os dias do mês, horários de entrada/saída, horas trabalhadas, saldo diário e resumo mensal (total trabalhado, previsto, saldo, atrasos, faltas).

#### Consolidado Mensal (Excel)

1. Vá em **Relatórios**.
2. Selecione mês, ano e opcionalmente um departamento.
3. Clique em **Baixar Excel**.

O arquivo contém uma linha por funcionário com: dias trabalhados, total de horas, saldo, atrasos e faltas.

---

### Configurações

Vá em **Configurações** para ajustar:

| Configuração | O que faz |
|---|---|
| Horário de Entrada | Horário esperado de chegada (ex.: 07:00) |
| Horário de Saída | Horário esperado de saída (ex.: 17:00) |
| Tolerância de Atraso | Minutos de tolerância antes de marcar atraso (ex.: 10) |
| Limite de Recuperação | Máximo de horas extras reconhecidas por dia (ex.: 120 min) |
| Dias Úteis | Dias da semana que contam como dia de trabalho |
| Nome da Empresa | Aparece nos relatórios PDF/Excel |
| Logo da Empresa | Imagem exibida nos relatórios |
| Sensibilidade de Reconhecimento | Threshold (0.0 a 1.0). Menor = mais exigente. Padrão: 0.6 |
| Salvar Foto na Batida | Guarda a imagem capturada no momento de cada batida |
| Retenção de Fotos | Quantos dias manter as fotos salvas |

#### Trocar Senha de Administrador

Na mesma tela de Configurações, role até **Alterar Senha**, informe a senha atual e a nova senha (mínimo 8 caracteres).

---

### Backup do Banco de Dados

Em **Configurações**, clique em **Baixar Backup (ponto.db)**.

O arquivo `ponto.db` contém todos os dados do sistema. Guarde em local seguro periodicamente.

Para restaurar: substitua o arquivo `instance/ponto.db` pelo backup e reinicie o sistema.

---

## Perguntas Frequentes

**A câmera não abre no navegador.**
Use o endereço `http://localhost:5000`. A câmera só funciona em localhost ou em sites com HTTPS.

**O sistema não me reconhece.**
Verifique a iluminação do ambiente. Se persistir, peça ao administrador para recapturar suas fotos.

**Registrei ponto errado. O que faço?**
Informe o administrador. Ele pode editar, adicionar ou excluir batidas com justificativa.

**Esqueci de bater saída ontem.**
Informe o administrador, que pode adicionar a batida manualmente.

**Posso usar no celular?**
Sim, desde que o celular tenha câmera frontal e esteja na mesma rede que o servidor.
