import os
from datetime import datetime
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

import config
from src.models import FlightResult
from src.utils import format_duration, format_price

_jinja_env = Environment(loader=FileSystemLoader(config.TEMPLATES_DIR))
_jinja_env.filters["duration"] = format_duration
_jinja_env.filters["price"] = format_price


def build_report(
    results: List[FlightResult],
    price_stats: Optional[dict],
) -> dict:
    """Monta o relatório com resultados e comparação histórica.

    Retorna um dict com as chaves 'html' e 'text'.
    """
    if not results:
        raise ValueError("Nenhum resultado para gerar relatório.")

    first = results[0]
    context = {
        "origin": first.origin,
        "destination": first.destination,
        "departure_date": first.departure_date.strftime("%d/%m/%Y"),
        "return_date": first.return_date.strftime("%d/%m/%Y"),
        "passengers": first.passengers,
        "flights": results,
        "stats": price_stats,
    }

    html = _jinja_env.get_template("email_report.html").render(**context)
    text = _build_text(context, results, price_stats)

    return {"html": html, "text": text}


def build_alert_report(
    flights_below: List[FlightResult],
    threshold: float,
    price_stats: Optional[dict],
) -> dict:
    """Relatório de alerta: voos abaixo do threshold com todos os detalhes."""
    first = flights_below[0]
    context = {
        "origin": first.origin,
        "destination": first.destination,
        "departure_date": first.departure_date.strftime("%d/%m/%Y"),
        "return_date": first.return_date.strftime("%d/%m/%Y"),
        "passengers": first.passengers,
        "flights": flights_below,
        "threshold": threshold,
        "stats": price_stats,
    }
    html = _jinja_env.get_template("email_alert.html").render(**context)
    text = _build_alert_text(context, flights_below, threshold, price_stats)
    return {"html": html, "text": text}


def build_summary_report(
    cheapest: FlightResult,
    daily_avg: float,
    price_stats: Optional[dict],
) -> dict:
    """Relatório resumido diário: menor preço encontrado + média da busca."""
    context = {
        "origin": cheapest.origin,
        "destination": cheapest.destination,
        "departure_date": cheapest.departure_date.strftime("%d/%m/%Y"),
        "return_date": cheapest.return_date.strftime("%d/%m/%Y"),
        "passengers": cheapest.passengers,
        "cheapest": cheapest,
        "daily_avg": daily_avg,
        "stats": price_stats,
    }
    html = _jinja_env.get_template("email_summary.html").render(**context)
    text = _build_summary_text(context, cheapest, daily_avg, price_stats)
    return {"html": html, "text": text}


def save_local_report(html: str, filename: str) -> str:
    """Salva o relatório HTML em reports/ e retorna o caminho absoluto."""
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def make_report_filename(origin: str, destination: str) -> str:
    """Gera um nome de arquivo único baseado na rota e timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{origin.upper()}_{destination.upper()}_{ts}.html"


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _build_text(context: dict, results: List[FlightResult], stats: Optional[dict]) -> str:
    sep = "─" * 55
    lines = [
        sep,
        f"  {context['origin']} → {context['destination']}  |  "
        f"{context['departure_date']} → {context['return_date']}  |  "
        f"{context['passengers']} passageiro(s)",
        sep,
    ]

    for r in results:
        tipo = "Direto" if r.is_direct else f"{r.stops} conexão(ões)"
        lines.append(
            f"  {r.airline:<28} {tipo:<14} "
            f"{format_duration(r.duration_minutes):<8} {format_price(r.price_brl)}"
        )
        if r.booking_url:
            lines.append(f"  → Comprar: {r.booking_url}")

    lines.append(sep)

    if stats:
        lines.append(f"  Histórico 30d: média {format_price(stats['avg'])}  |  menor {format_price(stats['min'])}")
        lines.append(sep)

    return "\n".join(lines)


def _build_alert_text(context: dict, flights: List[FlightResult], threshold: float, stats: Optional[dict]) -> str:
    sep = "─" * 55
    lines = [
        sep,
        f"  🚨 ALERTA DE PREÇO — abaixo de {format_price(threshold)}",
        f"  {context['origin']} → {context['destination']}  |  "
        f"{context['departure_date']} → {context['return_date']}  |  "
        f"{context['passengers']} passageiro(s)",
        sep,
    ]
    for r in flights:
        tipo = "Direto" if r.is_direct else f"{r.stops} conexão(ões)"
        lines.append(
            f"  {r.airline:<28} {tipo:<14} "
            f"{format_duration(r.duration_minutes):<8} {format_price(r.price_brl)}"
        )
        if r.booking_url:
            lines.append(f"  → Comprar: {r.booking_url}")
    lines.append(sep)
    if stats:
        lines.append(f"  Histórico 30d: média {format_price(stats['avg'])}  |  menor {format_price(stats['min'])}")
        lines.append(sep)
    return "\n".join(lines)


def _build_summary_text(context: dict, cheapest: FlightResult, daily_avg: float, stats: Optional[dict]) -> str:
    sep = "─" * 55
    tipo = "Direto" if cheapest.is_direct else f"{cheapest.stops} conexão(ões)"
    lines = [
        sep,
        f"  📋 RESUMO DIÁRIO — nenhum voo abaixo do limite hoje",
        f"  {context['origin']} → {context['destination']}  |  "
        f"{context['departure_date']} → {context['return_date']}  |  "
        f"{context['passengers']} passageiro(s)",
        sep,
        f"  Média da busca atual:  {format_price(daily_avg)}",
        f"  Menor encontrado hoje:",
        f"  {cheapest.airline:<28} {tipo:<14} "
        f"{format_duration(cheapest.duration_minutes):<8} {format_price(cheapest.price_brl)}",
    ]
    if cheapest.booking_url:
        lines.append(f"  → Comprar: {cheapest.booking_url}")
    lines.append(sep)
    if stats:
        lines.append(f"  Histórico 30d: média {format_price(stats['avg'])}  |  menor {format_price(stats['min'])}")
        lines.append(sep)
    return "\n".join(lines)
