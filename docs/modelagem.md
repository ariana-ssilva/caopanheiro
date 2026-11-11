# Modelagem

## Diagrama de casos de uso

```mermaid
flowchart LR
  V[Visitante] --> C[Consultar animais]
  A[Adotante] --> U[Criar conta e entrar]
  A --> S[Solicitar adoção]
  A --> F[Enviar feedback]
  O[Equipe da ONG] --> M[Gerenciar animais]
  O --> G[Analisar adoções]
  C --> D[(Banco de dados)]
  S --> D
  M --> D
  G --> D
```

## Diagrama de classes

```mermaid
classDiagram
  User "1" --> "*" Adoption : realiza
  Animal "1" --> "*" Adoption : recebe
  Adoption "1" --> "0..1" Feedback : possui
  class User { +id +name +email +role }
  class Animal { +id +name +species +status }
  class Adoption { +id +message +status +created_at }
  class Feedback { +id +rating +comment }
```

## Modelo relacional

`users (id, name, email, password_hash, role)`  
`animals (id, name, species, age, size, description, health, status)`  
`adoptions (id, animal_id FK, adopter_id FK, message, status)`  
`feedback (id, adoption_id FK, rating, comment)`
