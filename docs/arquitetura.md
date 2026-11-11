# Arquitetura e decisões técnicas

O sistema usa uma arquitetura web em camadas:

```text
Navegador (HTML/CSS/Jinja2)
          |
Rotas Flask e autorização
          |
Camada de acesso a dados (SQLite/MySQL)
          |
Banco relacional
```

O padrão de fábrica `create_app` permite testes isolados. A configuração `DATABASE_URL` seleciona MySQL; na ausência dela, SQLite reduz o custo de instalação para desenvolvimento e demonstração. O esquema lógico é o mesmo nos dois modos.

## Segurança

- Hash PBKDF2-HMAC-SHA256 com salt aleatório;
- Sessão assinada pelo Flask;
- Queries parametrizadas;
- Decorators separados para autenticação e autorização;
- Validação de status permitidos no servidor;
- Dados sensíveis fora do código por variáveis de ambiente.

Para produção, ainda devem ser configurados HTTPS, proteção CSRF, gerenciamento de segredos, logs, backups e política de retenção de dados.
