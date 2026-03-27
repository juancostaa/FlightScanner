"""
Testa o modo alerta sem consumir a SerpAPI nem o SMTP.

Cenários cobertos:
  1. Alerta disparado  — há voos abaixo do threshold
  2. Resumo diário     — nenhum voo abaixo do threshold

Execução:
  python test_alert.py          # só salva HTMLs em reports/
  python test_alert.py --email  # também envia os emails (requer .env)
"""

import sys
from datetime import date, datetime

from src.emailer import make_alert_subject, make_summary_subject, send_report
from src.models import FlightResult
from src.reporter import (
    build_alert_report,
    build_summary_report,
    make_report_filename,
    save_local_report,
)

# ---------------------------------------------------------------------------
# Dados falsos
# ---------------------------------------------------------------------------

ORIGIN = "GRU"
DESTINATION = "LIS"
DEPARTURE = date(2026, 7, 10)
RETURN = date(2026, 7, 24)
PASSENGERS = 1

_fake_results = [
    FlightResult(
        origin=ORIGIN, destination=DESTINATION,
        departure_date=DEPARTURE, return_date=RETURN,
        airline="LATAM Airlines", is_direct=True, stops=0,
        duration_minutes=685, price_brl=2_350.0, passengers=PASSENGERS,
        searched_at=datetime.now(),
        booking_url="https://www.skyscanner.com.br/transporte/passagens-aereas/gru/lis/20260710/20260724/?adults=1",
    ),
    FlightResult(
        origin=ORIGIN, destination=DESTINATION,
        departure_date=DEPARTURE, return_date=RETURN,
        airline="TAP Air Portugal", is_direct=False, stops=1,
        duration_minutes=780, price_brl=2_890.0, passengers=PASSENGERS,
        searched_at=datetime.now(),
        booking_url="https://www.skyscanner.com.br/transporte/passagens-aereas/gru/lis/20260710/20260724/?adults=1",
    ),
    FlightResult(
        origin=ORIGIN, destination=DESTINATION,
        departure_date=DEPARTURE, return_date=RETURN,
        airline="Air France", is_direct=False, stops=1,
        duration_minutes=820, price_brl=3_100.0, passengers=PASSENGERS,
        searched_at=datetime.now(),
        booking_url="https://www.skyscanner.com.br/transporte/passagens-aereas/gru/lis/20260710/20260724/?adults=1",
    ),
]

# Histórico simulado (substitui get_price_stats)
_fake_stats = {"avg": 3_200.0, "min": 2_350.0, "max": 4_100.0, "total": 45}

SEND_EMAIL = "--email" in sys.argv
TEST_EMAIL = None  # preenchido abaixo se --email for passado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _daily_avg(results):
    return sum(r.price_brl for r in results) / len(results)


def _save_and_maybe_send(report, subject, label):
    filename = make_report_filename(ORIGIN, DESTINATION).replace(".html", f"_{label}.html")
    path = save_local_report(report["html"], filename)
    print(f"  HTML salvo: {path}")

    if SEND_EMAIL:
        try:
            send_report(TEST_EMAIL, subject, report["html"], report["text"])
            print(f"  Email enviado para {TEST_EMAIL} ✓")
        except Exception as e:
            print(f"  ERRO ao enviar email: {e}")


# ---------------------------------------------------------------------------
# Cenário 1 — Alerta: threshold ACIMA do menor preço → deve disparar
# ---------------------------------------------------------------------------

def test_alert_triggered():
    threshold = 2_500.0  # LATAM (R$ 2.350) fica abaixo
    below = [r for r in _fake_results if r.price_brl <= threshold]

    assert below, "Esperava encontrar voos abaixo do threshold"

    report = build_alert_report(below, threshold, _fake_stats)
    subject = make_alert_subject(ORIGIN, DESTINATION, below[0].price_brl, threshold)

    print(f"\n[Cenário 1] Alerta disparado")
    print(f"  Threshold: R$ {threshold:,.0f}  |  voos abaixo: {len(below)}")
    print(f"  Assunto  : {subject}")
    _save_and_maybe_send(report, subject, "alerta")

    assert "ALERTA" in subject
    assert "2.350" in report["text"]
    assert "Comprar agora" in report["html"]
    print("  Asserts OK")


# ---------------------------------------------------------------------------
# Cenário 2 — Resumo: threshold ABAIXO do menor preço → nenhum voo elegível
# ---------------------------------------------------------------------------

def test_summary_sent():
    threshold = 1_000.0  # nenhum voo chega perto disso
    below = [r for r in _fake_results if r.price_brl <= threshold]

    assert not below, "Esperava lista vazia de voos abaixo do threshold"

    cheapest = _fake_results[0]
    daily_avg = _daily_avg(_fake_results)
    report = build_summary_report(cheapest, daily_avg, _fake_stats)
    subject = make_summary_subject(ORIGIN, DESTINATION, cheapest.price_brl, daily_avg)

    print(f"\n[Cenário 2] Resumo diário (sem alerta)")
    print(f"  Threshold: R$ {threshold:,.0f}  |  voos abaixo: {len(below)}")
    print(f"  Menor preço: R$ {cheapest.price_brl:,.0f}  |  Média: R$ {daily_avg:,.0f}")
    print(f"  Assunto   : {subject}")
    _save_and_maybe_send(report, subject, "resumo")

    assert "Resumo" in subject
    assert "LATAM" in report["text"]
    assert "nenhum" in report["html"].lower()
    print("  Asserts OK")


# ---------------------------------------------------------------------------
# Cenário 3 — Sem histórico (stats=None): os dois modos não devem quebrar
# ---------------------------------------------------------------------------

def test_no_stats():
    threshold = 2_500.0
    below = [r for r in _fake_results if r.price_brl <= threshold]

    report_alert = build_alert_report(below, threshold, price_stats=None)
    report_summary = build_summary_report(_fake_results[0], _daily_avg(_fake_results), price_stats=None)

    print(f"\n[Cenário 3] Sem histórico (stats=None)")
    assert "Histórico" not in report_alert["text"]
    assert "Histórico" not in report_summary["text"]
    print("  Asserts OK — nenhuma exceção e histórico omitido corretamente")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if SEND_EMAIL:
        import config
        missing = [k for k, v in {
            "EMAIL_HOST": config.EMAIL_HOST,
            "EMAIL_USER": config.EMAIL_USER,
            "EMAIL_PASSWORD": config.EMAIL_PASSWORD,
        }.items() if not v]
        if missing:
            print(f"ERRO: variáveis não configuradas no .env: {', '.join(missing)}")
            sys.exit(1)
        TEST_EMAIL = config.EMAIL_USER
        print(f"Modo email ativo")
        print(f"  Host    : {config.EMAIL_HOST}:{config.EMAIL_PORT}")
        print(f"  Usuário : {config.EMAIL_USER}")
        print(f"  Destino : {TEST_EMAIL}")

    print("=" * 55)
    print("  Teste do modo alerta — Flight Price Monitor")
    print("=" * 55)

    test_alert_triggered()
    test_summary_sent()
    test_no_stats()

    print("\n" + "=" * 55)
    print("  Todos os cenários passaram.")
    print("=" * 55)
