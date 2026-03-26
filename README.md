# ✈️ Flight Price Monitor

Ferramenta de linha de comando para monitorar preços de passagens aéreas, comparar com histórico e receber relatórios por email automaticamente.

---

## Funcionalidades

- Busca de passagens via **Google Flights** (SerpAPI) com resultados em tempo real
- Retorna data de ida/volta, companhia aérea, tipo de voo (direto ou com conexão), duração e preço
- **Comparação histórica** de preços armazenada localmente em SQLite
- Envio de **relatório por email** (HTML formatado) via SMTP
- **Agendamento automático**: o usuário escolhe de quanto em quanto tempo quer receber um novo report para o mesmo trecho
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
│
├── src/
│   ├── cli.py               # Interface interativa no terminal
│   ├── searcher.py          # Integração com SerpAPI / Google Flights
│   ├── history.py           # Leitura e escrita do histórico de preços (SQLite)
│   ├── reporter.py          # Montagem do relatório em HTML e texto
│   ├── emailer.py           # Envio de email via SMTP
│   ├── scheduler.py         # Agendamento de jobs com APScheduler
│   └── utils.py             # Helpers de formatação, cores no terminal, etc.
│
├── data/
│   ├── flights.db           # Banco SQLite com histórico de preços
│   └── jobs.json            # Jobs de monitoramento ativos
│
├── templates/
│   └── email_report.html    # Template HTML do email de relatório
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
| `jinja2` | Template do email HTML |

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
──────────────────────────────
  1 → Nova busca de passagens
  2 → Ver monitoramentos ativos
  3 → Executar checks pendentes agora
  4 → Histórico de preços
  0 → Sair

Cidade de origem: São Paulo (GRU)
Cidade de destino: Lisboa (LIS)
Data de ida (dd/mm/aaaa) ou deixe em branco para usar janela de dias:
Quantos dias a partir de hoje? 7
Duração da viagem (dias): 10
Número de passageiros: 2
Seu email para receber o relatório: voce@email.com
Reenviar report a cada quantas horas? (0 = não agendar): 24
```

---

## Exemplo de saída (terminal)

```
┌─────────────────────────────────────────────────────┐
│  GRU → LIS  |  10/05 → 20/05  |  2 passageiros      │
├─────────────────────────────────────────────────────┤
│  LATAM Airlines          Direto      14h20   R$ 4.820│
│  TAP Air Portugal        1 conexão   17h05   R$ 3.990│
│  Iberia via Madrid       1 conexão   19h30   R$ 3.540│
├─────────────────────────────────────────────────────┤
│  📉 Histórico: preço médio últimos 30d — R$ 4.320    │
│     Menor preço registrado —————————— R$ 3.210       │
└─────────────────────────────────────────────────────┘
Relatório enviado para voce@email.com ✓
Próximo report agendado em 24h ✓
```

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
    interval_hours: int
    next_run: datetime
```

---

## Limitações e observações

- A SerpAPI tem limite de **100 buscas gratuitas por mês** — para uso intenso, avalie o plano pago
- O agendamento é baseado em processo ativo (APScheduler em memória); para rodar em background de forma persistente, considere usar `cron` do sistema operacional apontando para `main.py --run-jobs`
- A comparação histórica só tem dados a partir da primeira busca feita pela ferramenta
- Passagens internacionais com moeda diferente de BRL são convertidas no momento da busca

---

## Possíveis evoluções

- Interface web com Flask/FastAPI
- Alertas de queda de preço por threshold configurável (ex.: avisar se cair mais de 10%)
- Suporte a múltiplos destinos em paralelo
- Exportação do histórico em CSV/Excel
- Integração com Telegram Bot como canal alternativo ao email
