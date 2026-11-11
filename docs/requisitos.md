# Requisitos do Caopanheiro

## Problema e objetivo

ONGs podem ter dificuldade para organizar animais, divulgar informações e acompanhar interessados. O Caopanheiro centraliza o processo de adoção e aproxima a ONG de adotantes responsáveis.

## Atores

- **Visitante:** consulta animais disponíveis.
- **Adotante:** cria conta, envia interesse e informa o bem-estar do animal.
- **Equipe da ONG:** cadastra animais e analisa solicitações.
- **Administrador:** gerencia a equipe e possui as permissões da ONG.

## Requisitos funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF01 | Cadastrar e autenticar usuários | Alta |
| RF02 | Manter cadastro de animais | Alta |
| RF03 | Exibir animais disponíveis | Alta |
| RF04 | Enviar solicitação de adoção | Alta |
| RF05 | Atualizar status da adoção | Alta |
| RF06 | Registrar feedback pós-adoção | Média |
| RF07 | Compartilhar/divulgar animais em redes sociais | Futura |
| RF08 | Receber doações financeiras e materiais | Futura |
| RF09 | Enviar notificações | Futura |

## Requisitos não funcionais

- RNF01: senhas devem ser armazenadas com PBKDF2, nunca em texto puro;
- RNF02: usuários devem acessar apenas operações autorizadas ao seu perfil;
- RNF03: a interface deve ser responsiva e acessível por navegador móvel;
- RNF04: consultas de animais devem retornar em até 2 segundos em ambiente de produção;
- RNF05: o sistema deve usar backup periódico do banco em produção;
- RNF06: dados pessoais devem ser tratados conforme a LGPD e minimizados.

## Regras de negócio

- Apenas animais com status `available` aparecem na vitrine;
- Um adotante não pode manter duas solicitações ativas para o mesmo animal;
- Apenas a ONG pode aprovar ou recusar uma solicitação;
- Ao aprovar ou concluir a adoção, o animal deixa de estar disponível;
- Feedback só pode ser enviado pelo adotante de uma adoção aprovada.
