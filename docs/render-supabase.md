# Publicar no Render com Supabase

O Flask roda como Web Service gratuito no Render. O PostgreSQL e as fotos ficam no Supabase; assim, reiniciar ou republicar o Render não apaga os dados. A execução local continua usando SQLite e arquivos locais quando as variáveis externas não estiverem configuradas.

## 1. Criar o Supabase

Crie um projeto em https://supabase.com/dashboard e guarde a senha do banco.

### Banco de dados

No botão **Connect**, escolha a conexão **Session pooler** e copie a URL PostgreSQL (porta 5432). Substitua o marcador de senha pela senha do banco, codificando caracteres especiais para URL. Use `?sslmode=require` ao final (ou `&sslmode=require` caso já haja parâmetros).

Exemplo sem credenciais reais:

```text
postgresql://postgres.PROJECT_REF:SENHA_CODIFICADA@HOST_SESSION_POOLER:5432/postgres?sslmode=require
```

Use o hostname exibido pelo seu projeto, sem copiar um hostname de outro exemplo. O session pooler é compatível com IPv4; o endereço direto do projeto pode depender de IPv6. Não use a chave da API no lugar da senha do banco.

A aplicação cria as tabelas automaticamente no schema **caopanheiro**, separado do schema público exposto pela Data API. No Table Editor, selecione esse schema para consultar as tabelas; não adicione `caopanheiro` à lista de schemas expostos da API. A autenticação segue sendo feita pelo Flask, sem depender do Supabase Auth.

### Fotos

Em **Storage**, crie um bucket chamado `caopanheiro-fotos` com:

- **Public bucket** ativado: as imagens de animais e avatares são públicas, como os arquivos estáticos da aplicação original.
- Limite de arquivo de 5 MB.
- Tipos MIME permitidos: `image/jpeg`, `image/png`, `image/webp`.

Não crie políticas de upload anônimo. Somente o servidor faz upload/remoção, com sua chave privada. Documentos pessoais ou comprovantes não devem ser colocados nesse bucket público.

Em **Project settings → API Keys**, copie a chave legada **service_role** (JWT). O código usa essa chave no servidor para acessar Storage. Não use a chave `anon`/publishable e não use a chave `sb_secret_...` neste campo: o cliente HTTP desta integração espera o JWT `service_role`. Copie também a **Project URL**, no formato `https://PROJECT_REF.supabase.co`.

## 2. Enviar os arquivos ao GitHub

No terminal local, depois de revisar as mudanças:

```bash
git add .
git commit -m "Configura Render com PostgreSQL e Storage do Supabase"
git push origin main
```

Não versione `.env`, `instance/production.json`, senhas ou banco de dados. `.env.example` contém somente exemplos. Não envie credenciais na conversa.

## 3. Criar o serviço no Render

### Pela Blueprint

Em https://dashboard.render.com, escolha **New → Blueprint**, conecte `ariana-ssilva/caopanheiro` na branch `main` e use o `render.yaml` do projeto. Ele configura Python, Gunicorn, plano Free, health check e uma chave secreta gerada automaticamente.

Preencha os valores solicitados:

| Variável | Valor |
| --- | --- |
| `DATABASE_URL` | URL do session pooler com senha e `sslmode=require` |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | JWT da chave `service_role`, somente no servidor |
| `ADMIN_EMAIL` | E-mail para o administrador inicial |
| `ADMIN_PASSWORD` | Senha do administrador com pelo menos 12 caracteres |

O arquivo já configura `STORAGE_BACKEND=supabase` e `SUPABASE_STORAGE_BUCKET=caopanheiro-fotos`.

### Como Web Service manual

Se preferir **New → Web Service**, selecione o mesmo repositório e informe:

- Runtime: Python 3.
- Plan: Free.
- Build Command: `pip install -r requirements.txt`.
- Start Command: `gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`.
- Health Check Path: `/health`.

Em **Environment**, configure todas as variáveis listadas acima, mais `STORAGE_BACKEND=supabase`, `SUPABASE_STORAGE_BUCKET=caopanheiro-fotos`, `PYTHON_VERSION=3.13.9` e `SECRET_KEY` (use Generate para criar um valor aleatório longo, com pelo menos 32 caracteres).

## 4. Conferir a publicação

Após o deploy, abra a URL HTTPS `.onrender.com` retornada pelo Render:

1. Entre com o administrador inicial.
2. Cadastre um animal com foto e confirme que a imagem abre no detalhe.
3. Envie uma contribuição e consulte em Gerenciar doações.
4. Reinicie/republique o serviço e confira que os registros e as fotos continuam disponíveis.
5. Remova `ADMIN_EMAIL` e `ADMIN_PASSWORD` do Environment após o primeiro deploy bem-sucedido. A conta já está salva no PostgreSQL; não apague `SECRET_KEY`.

A criação inicial é idempotente: não altera a senha de uma conta administrativa já existente nem promove uma conta de adotante com o mesmo e-mail. Não utiliza senha padrão. O endpoint `/health` testa a conexão do banco; o upload de fotos precisa ser conferido pelo formulário.

## Dados existentes e manutenção

O PostgreSQL novo começa vazio. Os usuários, animais e contribuições do SQLite local não são migrados automaticamente. Mantenha o arquivo `instance/caopanheiro.sqlite3` e as fotos locais até planejar a cópia dos dados. Não substitua o banco local pela URL externa sem querer operar diretamente no banco de produção.

Uploads novos usam o Supabase. Arquivos antigos já versionados seguem acessíveis pelo caminho local; arquivos antigos não versionados devem ser transferidos junto com os dados correspondentes.

O plano gratuito do Render continua sujeito a suspensão por inatividade e limites de uso. Os dados externos ficam sujeitos às cotas e políticas do plano Supabase escolhido; acompanhe o painel e faça backups. Esta preparação não cria contas ou recursos automaticamente e não publica sem as configurações da hospedagem.

## Testes de PostgreSQL

A suíte padrão roda em SQLite:

```bash
pytest -q
```

Para testar o mesmo fluxo em um PostgreSQL **local descartável**, configure `TEST_DATABASE_URL` com endereço `localhost` ou `127.0.0.1` e execute `pytest tests/test_app.py -q`. A fixture limpa os dados e reinicia as sequências desse banco entre os testes. Nunca use credenciais de produção nessa variável.

## Referências

- https://render.com/docs/deploy-flask
- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/storage/serving/downloads
