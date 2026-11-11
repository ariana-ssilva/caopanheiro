# Plano de testes e validação

## Estratégia

1. Testes unitários para hash de senha e validações;
2. Testes de integração das rotas com banco temporário;
3. Testes de autorização para impedir acesso de adotante ao painel;
4. Testes de aceitação com os fluxos de cadastro, solicitação e aprovação;
5. Teste de usabilidade com representantes da ONG e pelo menos três adotantes.

## Critérios de aceite

- Um visitante encontra um animal disponível em até três interações;
- Um adotante consegue criar conta e solicitar adoção;
- A equipe consegue atualizar a solicitação;
- Um adotante não acessa operações administrativas;
- O sistema não armazena a senha original;
- A interface funciona em tela de 360px de largura.

Execute os testes automatizados com `pytest`.
