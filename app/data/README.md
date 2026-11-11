# Opções do cadastro

`animal_options.json` é um catálogo local editável, sem chamadas a serviços externos em tempo de execução. Contém espécies, portes e uma seleção de nomes de raças em português, não uma lista exaustiva nem uma classificação automática do animal.

Referências de nomenclatura (somente nomes, sem reprodução de descrições):
- Cães: American Kennel Club — https://www.akc.org/public-education/resources/general-tips-information/dog-breeds-sorted-groups/
- Gatos: Cat Fanciers' Association — https://cfa.org/breeds/

“Sem raça definida (SRD)” é uma opção adicional do projeto. Raça continua sendo um campo livre. Não se deduz raça, porte ou estado de saúde pela foto. Os portes permanecem compatíveis com os filtros existentes: Pequeno, Médio e Grande.

Descrição e cuidados continuam salvos como texto. O filtro Jinja `info_tags` separa apenas ponto e vírgula e quebras de linha ao apresentar as tags; frases e registros antigos são preservados.
