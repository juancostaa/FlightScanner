# ✈️ Flight Price Monitor

Ferramenta de linha de comando para monitorar preços de passagens aéreas, comparar com histórico e receber relatórios por email automaticamente.

---

## Funcionalidades

- Busca de passagens via **Google Flights** (SerpAPI) com resultados em tempo real
- Retorna data de ida/volta, companhia aérea, tipo de voo (direto ou com conexão), duração e preço
- **Comparação histórica** de preços armazenada localmente em SQLite
- Envio de **relatório por email** (HTML formatado) via SMTP
- **Agendamento automático** com intervalo em horas ou minutos (mínimo 1 minuto)
- **Modo alerta**: envia email completo apenas quando o preço cair abaixo de um valor definido; nos demais checks envia um resumo com o menor preço encontrado e a média
- Suporte a múltiplos passageiros e cálculo automático da data de volta por número de dias

---

## Estrutura do projeto

```
flight_monitor/
│
├── main.py                  # Ponto de entrada — executa o CLI
├── config.py                # Variáveis de ambiente e configurações
├── .env                     # Chaves de API e credenciais (não versionar)
├── requirements.txt
├── test_alert.py            # Script de teste do modo alerta (sem API)
│
├── src/
│   ├── cli.py               # Interface interativa no terminal
│   ├── searcher.py          # Integração com SerpAPI / Google Flights
│   ├── history.py           # Leitura e escrita do histórico de preços (SQLite)
│   ├── reporter.py          # Montagem dos relatórios em HTML e texto
│   ├── emailer.py           # Envio de email via SMTP
│   ├── scheduler.py         # Agendamento de jobs com APScheduler
│   └── utils.py             # Helpers de formatação, cores no terminal, etc.
│
├── data/
│   ├── flights.db           # Banco SQLite com histórico de preços
│   └── jobs.json            # Jobs de monitoramento ativos
│
├── templates/
│   ├── email_report.html    # Template do relatório completo
│   ├── email_alert.html     # Template do email de alerta (preço abaixo do limite)
│   └── email_summary.html   # Template do resumo diário (modo alerta sem disparo)
│
└── reports/                 # Relatórios gerados localmente (HTML)
```

---

## Tecnologias e dependências

| Pacote | Uso |
|---|---|
| `serpapi` | Busca no Google Flights |
| `APScheduler` | Agendamento de monitoramentos periódicos |
| `smtplib` (stdlib) | Envio de emails via SMTP |
| `sqlite3` (stdlib) | Histórico de preços local |
| `python-dotenv` | Leitura do `.env` |
| `rich` | Formatação bonita no terminal |
| `jinja2` | Template dos emails HTML |

---

## Configuração

Crie um arquivo `.env` na raiz com:

```env
# SerpAPI — gratuita até 100 buscas/mês
# Cadastro em: https://serpapi.com/
SERPAPI_KEY=sua_chave_aqui

# Email (exemplo com Gmail)
# Ative "Senhas de app" em: myaccount.google.com/security
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=seuemail@gmail.com
EMAIL_PASSWORD=sua_senha_de_app
```

---

## Como usar

```bash
pip install -r requirements.txt
python main.py
```

O CLI guia o usuário passo a passo:

```
✈️  Flight Price Monitor

  1 → Nova busca de passagens
  2 → Ver monitoramentos ativos
  3 → Executar checks pendentes agora
  4 → Histórico de preços
  0 → Sair
```

---

## Agendamento por horas ou minutos

Ao criar uma nova busca, o CLI pergunta a unidade do intervalo:

```
Unidade do intervalo de reenvio: [h] horas  [m] minutos  [0] não agendar
Unidade [h/m/0]: m
Intervalo em minutos (mínimo 1): 30
```

| Opção | Comportamento |
|-------|---------------|
| `h` | Intervalo em horas (ex: `6` → a cada 6h) |
| `m` | Intervalo em minutos (mínimo 1 min) |
| `0` | Sem agendamento — busca única |

O intervalo fica visível na coluna **Intervalo** da listagem de jobs (`2 → Ver monitoramentos ativos`), exibido como `30min` ou `6h` conforme o valor configurado.

---

## Modo alerta

Após definir o intervalo, o CLI pergunta o modo de notificação:

```
  1 → Relatório completo a cada intervalo
  2 → Alerta: email somente quando o preço estiver abaixo de X

Modo de notificação [1/2]: 2
Valor limite em reais (ex: 2500): 2500
```

### Comportamento no modo alerta

| Situação | Email enviado |
|----------|--------------|
| Algum voo encontrado **abaixo do limite** | **Email de alerta** com todos os detalhes dos voos elegíveis (companhia, tipo, duração, preço) e link direto para compra |
| Nenhum voo abaixo do limite | **Resumo diário** com a média de preços da busca atual e os detalhes completos do voo mais barato encontrado |

Isso garante que você só receba notificações relevantes, mas nunca fique sem informação — o resumo diário mantém você atualizado mesmo quando o preço-alvo não foi atingido.

A coluna **Modo** na listagem de jobs exibe `Completo` ou `Alerta < R$ X` para cada monitoramento.

---

## Exemplo de saída (terminal)

```
┌─────────────────────────────────────────────────────┐
│  GRU → LIS  |  10/07 → 24/07  |  1 passageiro       │
├─────────────────────────────────────────────────────┤
│  LATAM Airlines          Direto      11h25   R$ 2.350│
│  TAP Air Portugal        1 conexão   13h00   R$ 2.890│
│  Air France              1 conexão   13h40   R$ 3.100│
├─────────────────────────────────────────────────────┤
│  📉 Histórico: preço médio últimos 30d — R$ 3.200    │
│     Menor preço registrado —————————— R$ 2.350       │
└─────────────────────────────────────────────────────┘
Relatório enviado para voce@email.com ✓
Modo alerta ativo: notificação quando < R$ 2.500, resumo caso contrário. Intervalo: 30min ✓
```

---

## Testando o modo alerta

O script `test_alert.py` permite testar os dois cenários do modo alerta sem consumir cota da SerpAPI nem do SMTP:

```bash
# Salva os HTMLs gerados em reports/ para inspeção visual
python test_alert.py

# Também envia os emails reais (requer .env configurado)
python test_alert.py --email
```

| Cenário | Descrição |
|---------|-----------|
| 1 — Alerta disparado | Threshold `R$ 2.500` → voo a `R$ 2.350` passa → gera email de alerta |
| 2 — Resumo diário | Threshold `R$ 1.000` → nenhum voo elegível → gera resumo com menor preço e média |
| 3 — Sem histórico | `stats=None` → nenhuma exceção, seção de histórico omitida corretamente |

---

## Modelo de dados

**`FlightResult`** — resultado de uma busca

```python
@dataclass
class FlightResult:
    origin: str
    destination: str
    departure_date: date
    return_date: date
    airline: str
    is_direct: bool
    stops: int
    duration_minutes: int
    price_brl: float
    passengers: int
    searched_at: datetime
    booking_url: str = ""
```

**`MonitorJob`** — job de monitoramento ativo

```python
@dataclass
class MonitorJob:
    id: str
    origin: str
    destination: str
    departure_date: date
    return_date: date
    passengers: int
    email: str
    interval_minutes: int   # intervalo em minutos (mínimo 1)
    next_run: datetime
    alert_mode: bool = False
    alert_threshold: float = 0.0
```

---

## Limitações e observações

- A SerpAPI tem limite de **250 buscas gratuitas por mês** — intervalos curtos (ex: 1 minuto) consomem cota rapidamente; use com moderação
- O agendamento é baseado em processo ativo (APScheduler em memória); para rodar em background de forma persistente, use `cron` do sistema operacional apontando para `main.py --run-jobs`
- A comparação histórica só tem dados a partir da primeira busca feita pela ferramenta
- Passagens internacionais com moeda diferente de BRL são convertidas no momento da busca
- Jobs salvos em versões anteriores (com `interval_hours`) são convertidos automaticamente para minutos ao carregar

---

## Possíveis evoluções

- Interface web com Flask/FastAPI
- Suporte a múltiplos destinos em paralelo
- Exportação do histórico em CSV/Excel
- Integração com Telegram Bot como canal alternativo ao email
