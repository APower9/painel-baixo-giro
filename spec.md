# Spec — Painel Baixo Giro & Performance LEGO Obsoleto

Documento de especificação do dashboard HTML atual, para uso como referência ao continuar o desenvolvimento no Claude Code. O painel é um único arquivo `.html` autocontido (sem build step, sem dependências locais além de uma CDN).

## 1. Visão geral

- **Arquivo:** histórico de HTMLs (`Painel_Baixo_Giro_e_LEGO_Obsoleto_4.html`, `_6.html`, `_7.html`...) — HTML+CSS+JS em um único arquivo, dados embutidos como JSON inline (`const DATA = {...}`). **Decisão (24/08/2026): a partir de agora o nome de cada snapshot usa o número da semana de dados** (ex.: `Painel_..._Semana7.html`, arquivado em `archive/Semana7/`), não um contador solto — os dois já haviam divergido (existiam `_4`, `_6`, `_7`, sem `_5`, enquanto os dados foram Semana 1–5 e depois Semana 7, pulando a 6). Ver seção 9 para a nova arquitetura (`index.html` + `data.json` desacoplado).
- **Duas abas** (tab switching via JS, sem router):
  1. **Performance — LEGO obsoleto** (`id="panel-lego"`) — aba padrão/ativa ao carregar.
  2. **Baixo giro — Robótica** (`id="panel-giro"`).
- **Sem backend.** Todos os dados são estáticos, injetados no momento da geração do arquivo. Atualizar dados = regenerar o arquivo inteiro com um novo objeto `DATA`.
- **Dependência externa única:** Chart.js 4.4.1 via CDN (`cdnjs.cloudflare.com`) + fonte Google Fonts (Space Grotesk, Inter, IBM Plex Mono).

## 2. Stack e convenções técnicas

- HTML puro + CSS (custom properties) + JavaScript vanilla (sem framework).
- Gráficos: **Chart.js** (bar, line, e combinações bar+line com eixo duplo).
- Sem localStorage/sessionStorage (não usado, não necessário — dados são estáticos por geração).
- Todo o JS está em uma única tag `<script>` ao final do `<body>`, depois da tag do Chart.js.

## 3. Design system (tema escuro, estilo "LEGO Retail")

### Paleta (CSS custom properties em `:root`)
```css
--bg: #12131a;        /* fundo da página */
--surface: #1b1d29;    /* cards, painéis */
--surface-2: #232538;  /* hover, inputs */
--border: #2c2f45;
--text: #eef0f6;
--muted: #8d90a8;
--gold: #e8a33d;
--coral: #e0604f;
--teal: #4fc9a8;
--blue: #6c8cd5;
--purple: #a37de8;
--lightblue: #5ac8fa;
--yellow: #f2c14e;
--pink: #e07bb0;
```

### Tipografia
- **Títulos/headers:** Space Grotesk (600–700)
- **Corpo/labels:** Inter (400–600)
- **Números/valores/código:** IBM Plex Mono (400–600) — usado em KPIs, células numéricas de tabela, badges

### Componentes reutilizáveis (classes CSS)
| Classe | Uso |
|---|---|
| `.kpi-grid` / `.kpi` | Grid de 4 cartões de KPI no topo de cada seção. Variantes de cor: `.kpi.revenue` (gold), `.kpi.cost` (coral), `.kpi.margin` (teal), `.kpi.pct` (blue), `.kpi.purple` |
| `.studs` / `.stud` | Par de bolinhas coloridas decorativas no topo de cada KPI (referência estética a peças LEGO) |
| `.panel` | Card genérico para gráficos, com `<h2>` + `.desc` + `.chart-box` |
| `.chart-box` / `.chart-box.tall` | Container do `<canvas>`, altura fixa (260px / 320px) |
| `.table-panel` | Card contendo uma tabela, com `.toolbar` (busca) e `.table-scroll` (scroll interno) |
| `.callouts` / `.callout` | Grid de insights textuais. Variantes: `.callout.risk` (borda coral), `.callout.ok` (borda teal), `.callout.info` (borda blue) |
| `.mini-badge` | Badge pequeno no cabeçalho (contadores dinâmicos) |
| `.tab-btn` / `.tab-panel` | Sistema de abas |
| `.row.two` / `.row.two.even` | Grid de 2 colunas para pares de painéis lado a lado |

### Responsividade
Media query única em `840px`: KPI grid vira 2 colunas, `.row.two` vira 1 coluna, `.callouts` vira 1 coluna.

## 4. Estrutura de dados (`const DATA`)

Todo o objeto `DATA` é serializado como JSON e injetado diretamente no `<script>`. Chaves:

### `DATA.BAIXO_GIRO` — array de itens de estoque parado (Robótica)
```ts
{ grupo: string, material: number, descricao: string, estoque: number }[]
```
Fonte: aba única de `Analise_Baixo_Giro_04_05.xlsx`. **Não muda com as atualizações semanais do LEGO Obsoleto** — é um snapshot fixo do fechamento de 04/05.

### `DATA.LEGO_ITEMS` — agregado total por item (todo o período)
```ts
{ "Nome do item": string, sessions: number, cart: number, purchased: number, revenue: number }[]
```
Ordenado por `sessions` desc.

### `DATA.LEGO_TREND` — série diária total (soma de todos os itens)
```ts
{ DataStr: string /* "dd/mm" */, sessions: number }[]
```

### `DATA.LEGO_PIVOT` — série diária por item (para o gráfico multi-linha)
```ts
{
  dates: string[],              // "dd/mm", eixo X compartilhado
  series: { item: string, data: number[] }[]  // data.length === dates.length, alinhado por índice
}
```
No render, o gráfico usa apenas os **top 8 itens por volume total de sessões** (`topPivotSeries` calculado em runtime), mesmo que `LEGO_PIVOT.series` tenha mais itens.

### `DATA.LEGO_RAW` — registros brutos (nível item × dia)
```ts
{ "Nome do item": string, Data: string /* "dd/mm/aaaa" */, sessions: number, cart: number, purchased: number, revenue: number }[]
```
Ordenado por data crescente, depois por nome do item. Alimenta a tabela "Dados das sessões — detalhamento por item e dia".

### `DATA.LEGO_WEEK_CURRENT` — últimos 7 dias disponíveis
```ts
{ label: string /* "dd/mm – dd/mm/aaaa" */, items: { "Nome do item": string, sessions, cart, purchased, revenue }[] }
```
`items` vem pré-ordenado por `sessions` desc (e o JS reordena de novo por garantia).

### `DATA.LEGO_WEEKLY_EVOLUTION` — panorama semana a semana (desde o início do período)
```ts
{ label: string /* "S1", "S2", ... */, range: string /* "dd/mm–dd/mm" */, sessions: number, cart: number, purchased: number, revenue: number }[]
```
Alimenta o gráfico combinado (barras de sessões + linhas de carrinho/compras).

## 5. Seções e componentes visuais

### Aba "Performance — LEGO obsoleto" (`#panel-lego`)
1. **KPI grid (4 cards):** Sessões no período · Adições ao carrinho (+ taxa sobre sessões) · Compras concluídas · Taxa de conversão
2. **Panorama de evolução semanal** (`#weeklyEvoChart`) — gráfico combo:
   - Barras = sessões por semana (cor verde `--teal` se `purchased > 0` na semana, senão âmbar `--gold`)
   - Linha sólida azul (`--blue`) = carrinho, eixo secundário `y1`
   - Linha tracejada verde (`--teal`) com marcador ★ = compras, mesmo eixo `y1`
   - Tooltip customizado: mostra "★ N compra(s) · R$ X" quando a semana teve venda
3. **Sessões diárias — total** (`#trendChart`) — linha simples, área preenchida
4. **Sessões diárias — por item** (`#perItemChart`) — multi-linha, limitado a top 8 itens por sessões, paleta fixa de 8 cores (`itemColors`)
5. **Tabela "Semana atual"** (`#lego-week-panel`) — últimos 7 dias, ordenado por sessões, sem sort interativo (estático)
6. **Tabela "Performance consolidada por item"** (`#lego-summary-panel`) — sortável por qualquer coluna (click no `<th>`), com mini barra de conversão inline e rodapé de totais
7. **Tabela "Dados das sessões"** (`#lego-raw-panel`) — todos os registros brutos, com busca (`#r-search`) e sort por coluna
8. **Callouts** (3 cards) — texto editado manualmente a cada atualização, resumindo os principais insights da leva de dados mais recente

### Aba "Baixo giro — Robótica" (`#panel-giro`)
1. **KPI grid (4 cards):** Itens de baixo giro · Estoque total parado · Maior estoque individual · Top 3 concentram (%)
2. **Gráfico "10 maiores estoques"** (`#giroChart`) — barra horizontal
3. **Gráfico "Distribuição por faixa de estoque"** (`#faixaChart`) — barra vertical, faixas fixas: 1–10, 11–30, 31–100, 101–300, 300+
4. **Tabela completa** (`#giro-table-panel`) — sortável, com busca, rodapé de total
5. **Callouts** (2 cards)

## 6. Padrões de interatividade (JS)

- **Sort de tabela:** cada `<th data-k="...">` tem um listener de click que alterna `sortDir` (1/-1) e re-renderiza via função dedicada (`renderGiro`, `renderLego`, `renderRaw`). O indicador visual é um `▲`/`▼` injetado em `.sort-arrow`.
- **Busca:** input de texto filtra em `.toLowerCase().includes()` sobre nome/código/data, sem debounce (datasets pequenos, não é necessário).
- **Tabs:** troca de `display: none` / `block` em `.tab-panel`, sem reload de gráficos (os canvases da aba oculta continuam renderizados em memória).
- **Formatação:** `fmt()` usa `toLocaleString('pt-BR')` para milhares; `fmtR()` formata moeda BRL.

## 7. Processo de atualização semanal (como isso tem sido feito)

A cada nova semana de dados (`LEGO_Obsoleto_Semana_N.xlsx`, aba `Base`), o pipeline manual é:

1. **Ler a aba `Base`** com colunas: `Nome do item`, `Data.` (formato `YYYYMMDD`), `SessÃµes`, `Itens adicionados ao carrinho`, `Itens comprados`, `Receita do item`.
2. **Corrigir mojibake nos nomes.** Os nomes de item frequentemente vêm com encoding corrompido (UTF-8 lido como Latin-1/CP1252). Fix robusto:
   ```python
   def fix(n):
       try:
           return n.encode('cp1252').decode('utf-8')
       except Exception:
           return n
   ```
   Isso corrige `Â®`→`®`, `Ã§Ã£o`→`ção`, `â€“`→`–`, etc. em uma única operação — mais robusto que replaces manuais.
3. **Checar duplicatas/variações de nome** após a correção (mesma SKU, nomes ligeiramente diferentes por erro de digitação ou mudança de nome no catálogo). Merge manual via dict de `{nome_errado: nome_canonico}` quando necessário.
4. **Recalcular todas as 6 chaves de `DATA.LEGO_*`** a partir do dataset completo acumulado (não incremental — cada arquivo novo já vem com o histórico completo desde 25/05, então basta reprocessar tudo).
5. **Atualizar textos fixos manualmente:** período no subtítulo da seção, KPI de "foot" com o range de datas, descrição da tabela de dados brutos (contagem de registros), rodapé (`<footer>`), e os 2–3 `.callout` com uma leitura editorial dos dados novos (picos, quedas, primeiras conversões, etc.) — **isso não é gerado automaticamente, é escrito à mão a cada rodada**.
6. **`DATA.BAIXO_GIRO` não muda** entre atualizações — só seria reprocessado se um novo arquivo de estoque físico fosse enviado.
7. Validar antes de entregar: balanceamento de `<div>`, `node --check` no JS extraído, confirmar somas (`sessions`/`cart`/`purchased`/`revenue`) batem com os totais da planilha original.

## 8. Problemas de qualidade de dados já enfrentados (ficar atento)

- **Encoding duplo-corrompido** nos nomes de item (mojibake) — inconsistente entre arquivos e até entre linhas do mesmo arquivo. Sempre validar com a técnica do item 7.2.
- **Nomes de item mudam de uma semana para outra** para o mesmo SKU (ex.: adição de sufixo "– Kit Educativo DUPLO®"). É preciso checar manualmente se um "item novo" é genuinamente novo ou uma variação de nome de um item já existente.
- **Linhas com nome concatenado/duplicado por erro de digitação na fonte** (ex.: `"X – Kit Y X"` onde o nome se repete). Tratar como o item correto, não como SKU novo.
- **Catálogo de itens rastreados cresce ao longo do tempo** (começou com 8 SKUs, hoje tem 18). O código já foi ajustado para não hardcodear a contagem (`LEGO_ITEMS.length` no rodapé da tabela), mas textos descritivos (`.sub`, `.desc`) ainda são manuais.
- **Datas nem sempre contínuas** — há gaps de dias sem nenhum evento registrado (não confundir "sem dado" com "zero sessões"; o pivot/trend só inclui datas que aparecem em pelo menos um registro).
- **Uma semana de dados já foi pulada** (Semana 6 nunca foi enviada) — o painel seguiu direto da Semana 5 para a Semana 7 sem interpolar.

## 9. Arquitetura decidida (24/08/2026 — sessão de grilling sobre este spec)

As seções 9–11 abaixo eram "sugestões não implementadas". Foram fechadas como decisões em uma sessão de grilling e já parcialmente implementadas neste repositório:

- **`DATA` desacoplado do HTML.** `index.html` agora carrega `fetch('data.json')` em vez de embutir `const DATA = {...}` inline. Isso implica que o painel **não funciona mais abrindo o arquivo direto (`file://`)** — precisa sempre ser servido via HTTP (local: `python -m http.server`; produção: GitHub Pages, seção 10).
- **Snapshots históricos ficam congelados.** Cada semana publicada é arquivada como um par autocontido `archive/SemanaN/index.html` + `archive/SemanaN/data.json` (cópia exata do que foi publicado, não referencia o `data.json` "atual" da raiz — senão o histórico mudaria de conteúdo quando os dados da semana seguinte forem publicados).
- **`merge_map.json`** (raiz do repo) substitui o mapa de nomes que antes só existia na cabeça/conversa: `{nome_errado: nome_canonico}`, versionado e revisado manualmente a cada semana.
- **`build.py`** (raiz do repo) implementa o pipeline completo: ler `.xlsx` → fix de encoding → aplicar `merge_map.json` → recalcular as 6 chaves `DATA.LEGO_*` → validar somas → gravar `data.json`, preservando `DATA.BAIXO_GIRO`. Uso: `python build.py "Semana N.xlsx"` (`--check` só valida; `--allow-new` libera o gate de SKU novo). Os textos editoriais do `index.html` e o arquivamento em `archive/SemanaN/` continuam manuais.
- **Item em aberto, não decidido:** a pasta de origem tem dois arquivos de "baixo giro" não documentados neste spec (`Analise Baixo Giro 04.05 (1).xlsx`, 8,2 MB, 21/05; `Ficha Tecnica - Itens baixo giro revendas.xlsx`, 11 MB, 06/08). Antes de tocar em `DATA.BAIXO_GIRO` de novo, investigar o que são — pode ser que o snapshot fixo de 04/05 usado hoje já esteja desatualizado.

## 10. Hospedagem, acesso e publicação — decisões

### 10.1 Hospedagem
**Decisão: GitHub Pages**, repositório público, na conta pessoal GitHub já autenticada neste ambiente (`APower9`, plano gratuito — Pages privado exigiria upgrade pago ou uma org corporativa, nenhuma disponível hoje). Repositório local (`painel_baixo_giro`) ainda precisa de `git init` + criação do repo remoto (não existia até esta sessão, apesar de o contexto do Claude Code sugerir o contrário).

Opção de embutir a página num web part "Incorporar" do SharePoint (ideia original da seção 10.1 antiga) continua válida como passo posterior, depois que a URL do GitHub Pages existir.

### 10.2 Controle de acesso
**Decisão: sem restrição de acesso e sem anonimização.** Foi avaliado anonimizar receita/estoque/nomes de item para compensar o repositório ser público, mas a decisão final foi que esses dados não são tratados como confidenciais o suficiente para justificar esse trabalho (nem o custo de um plano pago com Pages privado). Painel fica acessível a qualquer pessoa com o link.

### 10.3 Textos editoriais (callouts, período, contagem de SKUs)
**Decisão: sempre geram rascunho, nunca publicam direto.** O pipeline (seção 11) roda sozinho até produzir `data.json` + sugestão de callouts, mas a publicação real (`git commit`/`push`) só acontece depois de revisão humana numa conversa com o Claude Code — sem PR automático, sem merge automatizado.

## 11. Automação por gatilho de pasta (OneDrive/SharePoint) — decidido

**Objetivo:** ao adicionar um novo arquivo `LEGO Obsoleto Semana N.xlsx` na pasta abaixo, um rascunho da atualização deve ser gerado sozinho, sem intervenção manual no chat — a publicação continua manual (seção 10.3).

**Pasta monitorada:**
```
C:\Users\T8675\OneDrive - Positivo\Alex\Diretoria Produtos\LEGO Retail\Itens Education Baixo Giro
```
(Caminho local sincronizado do OneDrive; a automação em nuvem usa a biblioteca do SharePoint/OneDrive for Business por trás desse caminho via Microsoft Graph API, não o caminho de disco local.)

### Arquitetura decidida
```
[Novo .xlsx na pasta]
        │
        ▼
[Gatilho: n8n — nó OneDrive/SharePoint, via conector MCP já disponível no Claude Code]
        │
        ▼
[Processamento — nó de código Python no n8n:]
  1. Ler aba "Base" do novo arquivo
  2. Corrigir encoding: name.encode('cp1252').decode('utf-8')
  3. Aplicar merge_map.json (raiz do repo) de nomes duplicados/variantes
  4. Recalcular as 7 chaves de DATA.* a partir do histórico acumulado
  5. Validar somas (sessions/cart/purchased/revenue) contra o arquivo de origem
     → divergência NÃO bloqueia; vira aviso na notificação
  6. Se houver item não reconhecido pelo merge_map → BLOQUEIA a publicação
     (mesmo gate do item 7 abaixo), sinaliza destaque na notificação
  7. Gravar rascunho (data.json + sugestão de callouts) em
     drafts/ dentro da própria pasta monitorada
        │
        ▼
[Notificar Alex via Teams — link do rascunho + resumo + alertas]
        │
        ▼
[Alex revisa/edita o rascunho numa conversa com o Claude Code]
        │
        ▼
[Claude Code publica: copia data.json para a raiz do repo, arquiva
 snapshot em archive/SemanaN/, git commit + push → GitHub Pages atualiza]
```

### Por que n8n
A Positivo já tem uma instância n8n interna (`https://n8n.positivo.corp`), e este ambiente Claude Code já tem um **conector MCP do n8n** disponível — o workflow pode ser criado/ajustado diretamente daqui, sem sair do Claude Code. Alternativa nativa Microsoft (Power Automate + Azure Function) foi descartada por não ter esse atalho de integração direta.

### Decisões já fechadas (a lista de "o que precisa ser decidido" da versão anterior deste spec)
1. Onde publicar (10.1): **GitHub Pages**, repo público, conta pessoal `APower9`.
2. Callouts exigem revisão humana (10.3): **sim, sempre** — pipeline gera rascunho, nunca publica sozinho.
3. Item novo não reconhecido pelo `merge_map`: **bloqueia a publicação** até confirmação manual (não "publica mesmo assim" como a versão anterior deste spec sugeria) — consistente com o gate de aprovação dos callouts.

### Ainda não implementado
- O workflow n8n em si (trigger + nó de código Python + gravação em `drafts/` + notificação Teams).
- ~~O script Python de processamento reutilizável~~ — **feito (22/09/2026): `build.py` na raiz do repo** (ver seção 9). O nó de código do n8n pode chamá-lo em vez de reimplementar a lógica.

