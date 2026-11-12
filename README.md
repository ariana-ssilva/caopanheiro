# Caopanheiro

Aplicação web para apoiar uma ONG municipal de Joaçaba/SC no cadastro, divulgação e gerenciamento da adoção de animais.

O projeto materializa a proposta validada de **Atividades Extensionistas III - Tecnologia Aplicada à Inclusão Digital**, do curso de Engenharia de Software.

## Escopo do MVP

- Cadastro e autenticação de adotantes e equipe da ONG;
- Cadastro, edição e remoção de animais;
- Atualização dos dados, status e foto dos animais pela equipe da ONG;
- Consulta pública de animais disponíveis;
- Manifestação de interesse em adoção;
- Análise e atualização do processo de adoção pela ONG;
- Registro de feedback após a adoção;
- Exploração com busca e filtros;
- Favoritos, perfil do adotante e registro de intenções de doação;
- Controle de permissões e armazenamento seguro de senhas.

Integração com redes sociais, aplicativo mobile, pagamentos, notificações push e inteligência artificial são evoluções futuras, não fazem parte do MVP.

## Tecnologias

- Python 3.10+;
- Flask;
- SQLite para desenvolvimento local;
- PostgreSQL e Supabase Storage para publicação no Render;
- MySQL 8+ para produção;
- HTML5, CSS3 e Jinja2;
- pytest.

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Abra `http://127.0.0.1:5000`.

Por padrão, os dados ficam em `instance/caopanheiro.sqlite3`. Para usar MySQL:

```bash
export DATABASE_URL="mysql://usuario:senha@localhost/caopanheiro"
export SECRET_KEY="substitua-esta-chave"
flask --app app run
```

O banco é inicializado automaticamente. Para criar um usuário administrador:

```bash
flask --app app create-admin
```

O comando solicita e-mail e senha de forma interativa.

## Usuários e permissões

- **Adotante:** consulta animais, solicita adoção e registra feedback;
- **ONG:** cadastra animais, analisa solicitações e acompanha adoções;
- **Administrador:** possui as permissões da ONG e pode cadastrar a equipe.

## Testes

```bash
pytest
```

## Documentação acadêmica

- [Requisitos e regras de negócio](docs/requisitos.md);
- [Arquitetura e decisões técnicas](docs/arquitetura.md);
- [Diagramas UML e modelo de dados](docs/modelagem.md);
- [Plano de testes e validação](docs/testes.md);
- [Cronograma e riscos](docs/planejamento.md).
- Identidade visual baseada no guia fornecido: creme aconchego, rosa carinho, amarelo alegria, verde menta, caramelo, marrom cacau e coral suave; títulos Fredoka e textos Nunito.

## Estrutura

```text
app/
  __init__.py       fábrica da aplicação e comandos CLI
  db.py             conexão, esquema e consultas
  security.py       hash de senha e decorators de autorização
  templates/        interfaces HTML
  static/           estilos
schema.sql          esquema compatível com MySQL
tests/              testes automatizados
docs/               documentação do projeto
```

## Ajustes a partir do guia de UI/UX

Referência: `docs/Caopanheiro_Identidade_Visual_Wireframes.pdf`.

- Paleta e tipografia do guia, foco por teclado, navegação responsiva e alvos de toque de pelo menos 44 px.
- Busca na Home, categorias com links e acesso a favoritos, doações e pedidos.
- Cadastro e filtros por sexo, idade informada, vacinação e castração; raça e cuidados no detalhe.
- Candidatura com dados pessoais, moradia, experiência e revisão; validação também no servidor e respostas disponíveis à equipe autorizada.
- Status em português: Enviado, Em análise, Contato/entrevista, Aprovado, Não aprovado e Finalizado.
- Acompanhamento pós-adoção disponível após a finalização; informações de saúde desconhecidas não são apresentadas como confirmadas.

As colunas novas são adicionadas automaticamente na inicialização, preservando os registros existentes. Candidaturas antigas aparecem com respostas não informadas.

O guia também propõe evoluções que ainda não estão implementadas: galeria com múltiplas fotos, histórico de cada mudança de status, mensagens internas, recuperação de senha, edição das necessidades da ONG, fotos no pós-adoção e relatórios. Doações continuam sendo intenções de contribuição, sem processamento de pagamentos. Os símbolos de animais usam ícones do Font Awesome Free, sem reproduzir a ilustração conceitual do PDF.

## Ícones

A interface utiliza Font Awesome Free 7.3.1, com estilos Solid e Regular hospedados em `app/static/vendor/fontawesome/`. A licença original está em `LICENSE.txt` nessa pasta. Não é necessário configurar conta ou Kit. Documentação: https://docs.fontawesome.com/web/setup/host-yourself/webfonts/

Exemplo de ícone decorativo junto de um rótulo:

```html
<i class="fa-solid fa-paw" aria-hidden="true"></i> Explorar pets
```

A pasta `app/static/icons/` permanece disponível para ícones personalizados.

## Foto de perfil e formulários

O cadastro público permite uma foto opcional; contas existentes de adotante, ONG e administrador podem adicionar, substituir ou remover a foto em Meu perfil. O cadastro público continua criando apenas adotantes. As imagens usam o armazenamento local `app/static/uploads/` e são exibidas no perfil e no menu lateral. A coluna `users.photo_filename` é adicionada automaticamente na inicialização, sem apagar contas existentes.

Formulários de conta, doação, adoção e cadastro de animal usam campos compactos, agrupamento em colunas no desktop e uma coluna no celular. As fotos têm prévia antes do envio. Formatos aceitos: JPG, PNG e WEBP; limite de upload da aplicação: 5 MB por requisição.

## Fluxo de doações

1. Em **Doações**, o usuário informa tipo, descrição, contato e, para contribuição financeira, o valor oferecido.
2. A contribuição começa em **Aguardando análise**. A equipe acessa **Gerenciar doações** pelo menu lateral ou painel, abre a oferta e registra o aceite ou a recusa com orientações.
3. Após o aceite, pode registrar **Entrega combinada** ou confirmar **Recebida**. Uma oferta ainda pendente não pode ser marcada diretamente como recebida.
4. O doador acompanha status e orientações no detalhe da contribuição e pode cancelar antes do recebimento. Cancelamentos, recusas e recebimentos encerram o fluxo.

Cada mudança registra um evento; somente o próprio doador e a equipe autorizada podem consultar os detalhes e contatos. Não há transferência de dinheiro ou notificação externa automática: valores financeiros são ofertas, e as orientações são consultadas dentro do sistema. A confirmação financeira é manual, feita pela equipe após verificar o recebimento.

A migração converte uma única vez as antigas intenções que tinham o rótulo técnico `received` para pendentes, pois a versão anterior não possuía confirmação de recebimento. Eventos anteriores não são inventados; o detalhe identifica registros legados sem histórico. Novas confirmações de recebimento são preservadas nas próximas inicializações.

## Publicação

A publicação escolhida usa **Render + Supabase**, com PostgreSQL e imagens externos. Siga [Publicação no Render com Supabase](docs/render-supabase.md). O roteiro alternativo do PythonAnywhere continua em [Publicação no PythonAnywhere](docs/publicacao.md).

## Instalação como aplicativo (PWA)

O projeto inclui manifesto, ícones e aviso offline. Veja como publicar e instalar no Android, iPhone e computador em [Instalação PWA](docs/pwa.md). Operações e consultas continuam exigindo internet.
