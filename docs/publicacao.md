> A hospedagem escolhida para este projeto é Render + Supabase. Veja [o roteiro principal](render-supabase.md). Este documento é uma alternativa.

# Publicação gratuita no PythonAnywhere

Este roteiro mantém Flask, SQLite e fotos no disco da hospedagem. O plano Beginner oferece uma aplicação em `SEU_USUARIO.pythonanywhere.com` e espaço limitado; consulte https://www.pythonanywhere.com/pricing/ para os limites atuais. Não é necessário contratar domínio.

## 1. Enviar a preparação ao GitHub

No computador local, após conferir as mudanças:

```bash
git add .
git commit -m "Prepara publicação no PythonAnywhere"
git push origin main
```

Se sua branch tiver outro nome, use esse nome no lugar de `main` (consulte `git branch --show-current`). O arquivo `instance/production.json` é privado e ignorado pelo Git.

## 2. Criar a conta e copiar o projeto

Crie uma conta Beginner gratuita em https://www.pythonanywhere.com/ . Em **Consoles → Bash**, execute:

```bash
git clone https://github.com/ariana-ssilva/caopanheiro.git
cd ~/caopanheiro
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_production.py
flask --app wsgi:application create-admin
```

Escolha uma versão Python disponível no painel (3.10 ou superior). Se não houver 3.13, substitua o comando e use exatamente a mesma versão ao criar a aplicação Web. O comando de administrador pede e-mail e senha de forma interativa. Não compartilhe senhas nem a chave secreta na conversa.

Se o repositório for privado, utilize a autenticação do GitHub no console ou envie um ZIP pelo gerenciador **Files**, sem incluir `.git`, `.venv`, banco de dados ou configuração privada. Não coloque tokens em URLs de clone.

## 3. Configurar a aplicação Web

Em **Web → Add a new web app**:

1. Escolha o endereço gratuito.
2. Selecione **Manual configuration** e a mesma versão Python do ambiente virtual.
3. Em **Virtualenv**, informe `/home/SEU_USUARIO/caopanheiro/.venv`.
4. Em **Source code**, informe `/home/SEU_USUARIO/caopanheiro`.
5. Abra o arquivo de configuração **WSGI** indicado pelo painel e substitua o conteúdo por:

```python
import sys

project_path = '/home/SEU_USUARIO/caopanheiro'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from wsgi import application
```

Substitua `SEU_USUARIO` pelo nome da conta PythonAnywhere. Não adicione `app.run()`.

Em **Static files**, adicione:

| URL | Diretório |
| --- | --- |
| `/static/` | `/home/SEU_USUARIO/caopanheiro/app/static/` |

Ative **Force HTTPS**, se disponível, e clique **Reload**. Abra `https://SEU_USUARIO.pythonanywhere.com`, entre com o administrador e teste cadastro de animal, envio de foto e doação. Cookies de sessão de produção exigem HTTPS.

## Dados e fotos

A instalação começa com um banco novo: `instance/caopanheiro.sqlite3`. As contas e os dados do computador não são copiados pelo Git. As fotos novas ficam em `app/static/uploads/`. Para levar os registros locais existentes, pause as alterações durante a cópia e transfira uma cópia consistente do banco junto com as fotos correspondentes; não coloque o banco no GitHub.

Faça backups do banco e da pasta de fotos pelo gerenciador Files. A configuração privada `instance/production.json` deve ser preservada entre atualizações. Acompanhe o limite de disco e a data de renovação da aplicação gratuita mostrada no painel.

## Atualizar uma publicação existente

No console Bash:

```bash
cd ~/caopanheiro
source .venv/bin/activate
git pull --ff-only
pip install -r requirements.txt
flask --app wsgi:application init-db
```

Depois clique **Reload** na aba Web. `init-db` preserva os registros e aplica as migrações do projeto. Evite atualizar quando usuários estiverem fazendo alterações; faça um backup antes.

## Referências

- Configuração oficial de Flask: https://help.pythonanywhere.com/pages/Flask/
- Plano gratuito e limites: https://www.pythonanywhere.com/pricing/
