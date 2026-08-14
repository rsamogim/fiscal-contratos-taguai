# Fiscal de Contratos — Prefeitura de Taguaí/SP

Monitora os contratos publicados pela Prefeitura Municipal de Taguaí/SP e envia um alerta
no Telegram sempre que houver um contrato novo ou uma atualização (aditivo/retificação)
em um contrato já conhecido.

## Por que não usa a API do PNCP

O projeto originalmente seria baseado na API pública de consulta do PNCP
(`https://pncp.gov.br/api/consulta/v1/contratos`). Na validação inicial essa API estava
fora do ar (504/502/503 de forma consistente, inclusive na página estática do swagger-ui).
Em vez disso, o projeto usa o **Portal da Transparência da própria Prefeitura de Taguaí**
(sistema Fiorilli SCPI 9.0), que expõe um endpoint de "Dados Abertos" com os mesmos dados,
validado com chamadas reais:

```
GET http://portal.taguai.sp.gov.br:5656/transparencia/VersaoJson/LicitacoesEContratos/
    ?ConectarExercicio={ano}&Listagem=Contratos&Ano={ano}&Empresa=1
    &MostraDadosConsolidado=False&ContratosApenasPublicados=False
```

Esse endpoint não pagina — retorna todos os contratos do ano informado em uma única
chamada, ordenados do mais recente para o mais antigo. Não há filtro por data de
publicação, então o projeto busca o ano corrente e os `ANOS_RETROATIVOS` anos anteriores
(padrão: 2) a cada execução, para não perder aditivos em contratos plurianuais.

Se a API do PNCP voltar a funcionar de forma estável, `src/taguai_client.py` pode ser
substituído por um cliente PNCP sem afetar `database.py`, `telegram_notifier.py` ou a
orquestração em `main.py` — só a normalização de campos mudaria.

## Como funciona a detecção de novidade

Cada contrato é identificado pelo campo `CODTCE` (identificador único usado no TCE-SP).
Um alerta "🆕 Novo Contrato" dispara quando um `CODTCE` nunca visto aparece. Um alerta
"📝 Contrato Atualizado" dispara quando um `CODTCE` já conhecido tem mudança em algum dos
campos:

- `VALCON` (valor do contrato)
- `VIGENF` (vigência final)
- `VENCIMENTO_ATUAL`
- `ADITADO` (valor aditivado)

Os campos `EMPENHADO` e `LIQUIDADO` **não** são monitorados: eles mudam a cada pagamento
normal (execução orçamentária) e não representam alteração contratual — monitorá-los
geraria alerta falso a cada nota de empenho ou liquidação.

Não há link público estável por contrato individual nesse portal (é uma aplicação
ASP.NET com postback). Os alertas linkam para a página geral de Contratos do portal e
incluem o código do contrato (ex: `0096/26`) para busca manual.

## Estrutura

```
src/
├── taguai_client.py   # chamadas ao portal, um ano por vez
├── database.py        # SQLite: contratos_notificados
├── telegram_notifier.py
└── main.py             # orquestração
data/
└── contratos.db        # versionado no repo (ver "Persistência" abaixo)
```

## Persistência no GitHub Actions

Runners do GitHub Actions são efêmeros. O workflow (`.github/workflows/monitor.yml`)
commita `data/contratos.db` de volta no repositório ao final de cada execução, usando
`stefanzweifel/git-auto-commit-action`, com `[skip ci]` na mensagem para não disparar o
workflow recursivamente.

## Rodando localmente

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env
# edite .env com TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
python src/main.py
```

Na primeira execução (banco vazio) o script carrega a baseline sem enviar nenhum alerta.

## Configurando o bot do Telegram

1. Crie um bot com o [@BotFather](https://t.me/BotFather) e gere um token novo.
2. Descubra o `chat_id` (do seu usuário ou de um grupo) — por exemplo enviando uma
   mensagem ao bot e consultando `https://api.telegram.org/bot{TOKEN}/getUpdates`.
3. No GitHub: Settings → Secrets and variables → Actions → adicione
   `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.

**Nunca** coloque o token diretamente no código ou no YAML do workflow.

## Testes manuais recomendados antes de considerar pronto

1. Banco vazio → rodar `python src/main.py` → confirma baseline sem alertas e
   `data/contratos.db` populado.
2. Apagar manualmente uma linha do banco (`DELETE FROM contratos_notificados WHERE codtce = '...'`)
   → rodar de novo → confirma alerta "🆕 Novo Contrato" no Telegram.
3. Rodar de novo sem mudanças → confirma que nada é enviado (idempotência).
4. Alterar manualmente `vigenf` de uma linha do banco → rodar de novo → confirma alerta
   "📝 Contrato Atualizado" mostrando o campo alterado (antigo → novo).
5. Testar o workflow via `workflow_dispatch` manual no GitHub antes de confiar no
   agendamento automático.

## Observações

- O portal roda em HTTP simples (não HTTPS) na porta 5656 — é assim que a Prefeitura
  disponibiliza os dados publicamente, não há credenciais envolvidas.
- `11:00 UTC` no cron do workflow corresponde a `08:00` em Brasília (Brasil não observa
  horário de verão desde 2019).
