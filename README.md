# SmartRobots — BB IA com IBM watsonx.ai

Esta versão adapta a interface e o backend existentes. O arquivo ZIP original permanece intacto.
A aplicação continua sendo um protótipo acadêmico, sem operações bancárias reais.

## 1. Preparar o backend (Windows / PowerShell)

Use Python 3.11 ou 3.12 e abra um terminal na pasta `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Abra `.env` em um editor e preencha:

- `WATSONX_API_KEY`: chave IBM com acesso ao serviço, somente no backend.
- `WATSONX_URL`: URL de serviço da região do seu projeto IBM.
- `WATSONX_PROJECT_ID`: ID do projeto watsonx.ai.
- `WATSONX_MODEL_ID`: identificador exato do modelo habilitado no seu projeto. Copie do código de integração disponibilizado pelo watsonx.ai; não use apenas o nome exibido na tela.
- `DJANGO_SECRET_KEY`: valor aleatório privado.

Não compartilhe a chave pelo chat, não coloque no JavaScript e não envie o `.env` ao repositório.
O modelo não foi fixado para evitar presumir disponibilidade regional ou acesso ao Granite escolhido.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## 2. Abrir a interface

Em outro terminal, na pasta `SmartRobots`:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Acesse http://localhost:5500, entre em **Entrar**, cadastre uma conta de teste e faça login.
O frontend usa http://localhost:8000 para acessar o backend.
As origens localhost e 127.0.0.1 na porta 5500 já estão permitidas para desenvolvimento.
Sem configuração IBM, o chat informa que o backend precisa ser configurado; não gera resposta fictícia.

## 3. Autorizar um gerente

Cadastre primeiro a conta que será usada pelo gerente. Em outro terminal, na pasta `backend`:

```powershell
.\.venv\Scripts\python.exe manage.py set_manager gerente@exemplo.com
```

Substitua pelo e-mail real da conta de teste cadastrada. A autorização fica no banco e só pode ser concedida por esse comando no servidor.
Para revogar, acrescente `--revoke`. Cadastro e login pelo navegador não concedem essa permissão.
Clientes veem apenas seus próprios atendimentos. Gerentes autorizados veem e atualizam a fila.

## 4. Fluxo implementado

1. Texto livre e botões de assunto passam pelo mesmo endpoint `/api/chat/`.
2. O backend inclui as instruções do BB IA como mensagem `system` e chama o SDK IBM.
3. O histórico é vinculado ao usuário e à sessão no SQLite; até 20 mensagens anteriores são usadas como contexto.
4. O modelo pode propor um resumo estruturado. O backend valida tipos, limites e prioridade.
5. O usuário vê o resumo e escolhe **Confirmar atendimento** ou **Cancelar encaminhamento**.
6. Após confirmação, o Django salva o atendimento de simulação e gera um protocolo `AT-` com identificador aleatório.
7. Repetir a confirmação na mesma sessão retorna o mesmo protocolo, sem criar outro atendimento.
8. O painel consulta o banco; não mistura casos fictícios ou protocolos locais.

Uma nova solicitação cria uma nova sessão no navegador. Recarregar a página também inicia uma conversa nova; a interface ainda não oferece reabertura de históricos antigos.
As páginas de conta e perfil permanecem. Valores de perfil e investimentos são dados do protótipo.
O antigo simulador de empréstimo com taxas fixas no navegador foi retirado do chat: pedidos de simulação passam ao BB IA, que deve pedir dados e taxa informada pelo usuário. Não há calculadora financeira determinística integrada nesta versão.

## 5. Instruções do BB IA e Prompt Lab

As instruções usadas pela aplicação estão em `backend/agent/system_prompt.txt`.
Foram reconstruídas com base no contexto disponível, incluindo português, escopo bancário, limites de simulação e proibição de dados sensíveis/procedimentos inventados.
O texto completo salvo por você no Prompt Lab não estava disponível; compare e ajuste esse arquivo para manter a versão desejada.
Salvar ou editar o Prompt Lab não atualiza automaticamente esta aplicação. Não é necessário criar notebook ou outro frontend.

Pontos de código:

- `agent/watsonx_service.py`: SDK IBM, credenciais e leitura da resposta.
- `agent/views.py`: histórico, validação, confirmação e permissões.
- `agent/models.py`: histórico persistido e papel de gerente.
- `SmartRobots/main.js`: chat unificado e protocolo retornado pelo servidor.
- `SmartRobots/gerente.js`: leitura e gravação dos atendimentos pela API.

## 6. Banco existente

O pacote não inclui a cópia do banco original nem a antiga `.venv`.
Para continuar com os usuários e atendimentos anteriores, copie **seu** `backend/db.sqlite3` original para o novo `backend` antes de executar `migrate`, mantendo um backup.
As migrações adicionam sessões e permissão de gerente sem apagar os modelos anteriores.
Senhas antigas em SHA-256 são atualizadas para o hash do Django no primeiro login correto.
Atendimentos antigos sem usuário vinculado ficam visíveis apenas a gerentes; não são atribuídos automaticamente a um cliente.

## 7. Verificação

Na pasta `backend`, após instalar dependências:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test agent
```

Resultado da verificação nesta entrega:

- 11 testes automatizados do backend passaram com respostas IBM simuladas.
- Verificados proposta sem gravação, confirmação, cancelamento, repetição de confirmação, histórico, erro da IBM, falta de configuração, isolamento de clientes, permissão do gerente e atualização de senhas.
- Adaptador SDK verificado com substitutos de teste; não equivale a executar o SDK real.
- Verificação de sintaxe JavaScript e teste de fluxo do frontend com DOM simulado passaram.
- As migrações foram aplicadas com sucesso a uma cópia de trabalho do banco original.

A instalação pela internet não foi possível no ambiente de desenvolvimento (falha de resolução de nomes). Os testes locais usaram Django 5.0.6 disponível no ZIP original, sem executar seus binários. O ambiente recomendado no requirements usa Django 5.2 e deve repetir os comandos acima após a instalação. Não houve teste visual em navegador nem chamada real à IBM. Credenciais, compatibilidade exata do SDK instalado, disponibilidade/custo do modelo e comportamento real do Granite precisam ser validados no seu ambiente.

## 8. Teste de aceite com a IBM

- Envie uma dúvida bancária e confira português e continuidade do contexto.
- Peça atendimento de gerente: verifique que nenhum caso é criado antes da confirmação.
- Confirme e veja o mesmo protocolo no chat e no painel.
- Use duas contas de cliente e confirme que cada uma vê apenas seus próprios casos.
- Entre com a conta autorizada como gerente e atualize status e notas.
- Peça bloqueio de cartão: a resposta deve informar os limites do protótipo e orientar pelos canais oficiais, sem alegar bloqueio real.

Use dados fictícios de teste. O prompt reduz respostas inadequadas, mas não garante o comportamento do modelo; essas verificações são necessárias antes de disponibilizar o protótipo a outras pessoas.

Referência da integração: https://ibm.github.io/watsonx-ai-python-sdk/fm_model_inference.html
