# Instalar o Cãopanheiro como PWA

## Publicar as alterações

No computador local:

```bash
git add .
git commit -m "Adiciona instalação PWA e aviso offline"
git push origin main
```

Aguarde o deploy no Render e abra o endereço HTTPS público do serviço. Não é necessário criar outro serviço ou configurar novas variáveis no Supabase/Render.

## Android

Abra o endereço no Chrome. Se o navegador oferecer instalação, o menu lateral do site mostra **Instalar aplicativo**. Também é possível abrir o menu do Chrome e procurar **Instalar aplicativo** ou **Adicionar à tela inicial**. A nomenclatura e a disponibilidade variam conforme o navegador.

## iPhone/iPad

Abra o endereço no Safari, toque em **Compartilhar → Adicionar à Tela de Início** e confirme. Se aparecer **Abrir como App da Web**, mantenha ativado. A instalação é feita pelo menu do navegador; o botão do site depende de suporte ao evento `beforeinstallprompt`.

## Computador

Abra no Chrome ou Edge e procure o ícone de instalação na barra de endereços ou a opção de instalar no menu do navegador. Se o navegador habilitar a instalação, também aparece o botão no menu lateral do site.

## Funcionamento e privacidade

- O aplicativo usa o mesmo endereço e os mesmos dados do site. Não é um APK nem uma publicação nas lojas.
- Há manifesto com escopo `/`, ícones PNG 192/512, ícone maskable e apple-touch-icon.
- O service worker é servido em `/service-worker.js`, com escopo raiz e revalidação.
- Apenas uma lista explícita de arquivos públicos de interface e o aviso offline entram no Cache Storage.
- Páginas HTML, formulários, pedidos, doações, perfis e imagens enviadas não são gravados nesse cache. Requisições POST e serviços externos não são interceptados.
- Sem conexão, a navegação mostra um aviso genérico; nenhuma solicitação é enfileirada para envio posterior. Se a rede cair durante o envio de um formulário, confira o resultado antes de reenviar.
- A aplicação precisa de internet para acessar contas, listar animais e gravar dados. A sessão da versão instalada pode ser diferente da sessão do navegador.
- HTTPS é necessário na hospedagem; localhost serve para desenvolvimento. O endereço de rede HTTP de outro computador não equivale a localhost.

## Validação

```bash
pytest -q
node tests/test_service_worker.cjs
```

No Chrome/Edge, use as ferramentas do desenvolvedor em **Application → Manifest / Service Workers** para conferir o manifesto e o worker. Depois de uma visita online com o worker ativo, use o modo Offline e navegue: o aviso deve aparecer. Verifique em **Cache Storage** que não há páginas de perfil, painel, pedidos ou doações. A instalação e o modo offline reais também devem ser conferidos no dispositivo escolhido.

Arquivos de interface são buscados primeiro na rede e usam o cache apenas se a rede falhar. Ao mudar a estratégia ou remover arquivos do cache, aumente a versão `CACHE_NAME` no worker; a ativação remove apenas caches antigos com o prefixo do Cãopanheiro. O worker não força recarregamentos de páginas abertas.

Referência: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable
