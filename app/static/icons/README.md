# Ícones da interface

Coloque os ícones do projeto nesta pasta. Prefira SVG; PNG e WebP com fundo transparente também funcionam.
Use nomes curtos, em minúsculas e sem espaços ou acentos: inicio.svg, pets.svg, favoritos.svg, doacoes.svg, perfil.svg.

Referência em templates Flask/Jinja:

```html
<img src="{{ url_for('static', filename='icons/pets.svg') }}" width="24" height="24" alt="">
```

Se houver texto ao lado, use alt vazio para evitar leitura duplicada. Quando o ícone transmitir informação sozinho, inclua uma descrição acessível no link ou botão.

As fotos enviadas nos cadastros ficam em `app/static/uploads/`.
