from datetime import date, datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src.emailer import make_subject, send_report
from src.history import get_history, get_price_stats, save_results
from src.models import MonitorJob
from src.reporter import build_report, make_report_filename, save_local_report
from src.scheduler import create_job, delete_job, load_jobs, schedule_with_apscheduler
from src.searcher import search_flights
from src.utils import format_duration, format_price

console = Console()


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def run_cli() -> None:
    console.print(Panel("✈️  Flight Price Monitor", style="bold cyan", expand=False))

    while True:
        _print_menu()
        choice = console.input("[bold]> [/bold]").strip()

        if choice == "1":
            _flow_new_search()
        elif choice == "2":
            _flow_list_jobs()
        elif choice == "3":
            _flow_run_now()
        elif choice == "4":
            _flow_history()
        elif choice == "0":
            console.print("Até logo! ✈️", style="cyan")
            break
        else:
            console.print("Opção inválida.", style="yellow")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def _print_menu() -> None:
    console.print()
    console.print("  [bold cyan]1[/bold cyan] → Nova busca de passagens")
    console.print("  [bold cyan]2[/bold cyan] → Ver monitoramentos ativos")
    console.print("  [bold cyan]3[/bold cyan] → Executar checks pendentes agora")
    console.print("  [bold cyan]4[/bold cyan] → Histórico de preços")
    console.print("  [bold cyan]0[/bold cyan] → Sair")
    console.print()


# ---------------------------------------------------------------------------
# Fluxo 1 — Nova busca
# ---------------------------------------------------------------------------

def _flow_new_search() -> None:
    console.print("\n[bold]Nova busca de passagens[/bold]")

    origin = _ask("Código IATA de origem (ex: GRU)").upper()
    destination = _ask("Código IATA de destino (ex: LIS)").upper()
    departure_date, return_date = _ask_dates()
    passengers = _ask_int("Número de passageiros", min_val=1)
    email = _ask("Seu email para receber o relatório")

    interval_hours = _ask_int(
        "Reenviar report a cada quantas horas? (0 = não agendar)", min_val=0
    )

    with console.status("Buscando passagens...", spinner="dots"):
        try:
            results = search_flights(origin, destination, departure_date, return_date, passengers)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return

    save_results(results)
    stats = get_price_stats(origin, destination)
    report = build_report(results, stats)

    _print_results_table(results, stats)

    filename = make_report_filename(origin, destination)
    path = save_local_report(report["html"], filename)
    console.print(f"Relatório salvo em: [dim]{path}[/dim]")

    with console.status("Enviando email..."):
        try:
            subject = make_subject(origin, destination, results[0].price_brl)
            send_report(email, subject, report["html"], report["text"])
            console.print(f"Relatório enviado para [green]{email}[/green] ✓")
        except Exception as e:
            console.print(f"[red]Falha ao enviar email: {e}[/red]")

    if interval_hours > 0:
        job = create_job(origin, destination, departure_date, return_date, passengers, email, interval_hours)
        console.print(f"Próximo report agendado em [cyan]{interval_hours}h[/cyan] ✓")
        _ask_apscheduler(job)


def _ask_apscheduler(job: MonitorJob) -> None:
    resp = console.input("Manter processo ativo com APScheduler? [s/N] ").strip().lower()
    if resp == "s":
        schedule_with_apscheduler(job)


# ---------------------------------------------------------------------------
# Fluxo 2 — Listar jobs
# ---------------------------------------------------------------------------

def _flow_list_jobs() -> None:
    jobs = load_jobs()
    if not jobs:
        console.print("\nNenhum monitoramento ativo.", style="yellow")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Rota")
    table.add_column("Ida / Volta")
    table.add_column("Passageiros", justify="center")
    table.add_column("Intervalo", justify="center")
    table.add_column("Próximo run")
    table.add_column("Email")

    for i, job in enumerate(jobs, 1):
        table.add_row(
            str(i),
            f"{job.origin} → {job.destination}",
            f"{job.departure_date.strftime('%d/%m/%Y')} / {job.return_date.strftime('%d/%m/%Y')}",
            str(job.passengers),
            f"{job.interval_hours}h",
            job.next_run.strftime("%d/%m %H:%M"),
            job.email,
        )

    console.print()
    console.print(table)

    resp = console.input("Cancelar algum monitoramento? Digite o número ou Enter para voltar: ").strip()
    if resp.isdigit():
        idx = int(resp) - 1
        if 0 <= idx < len(jobs):
            delete_job(jobs[idx].id)
            console.print(f"Monitoramento [red]cancelado[/red].")
        else:
            console.print("Número inválido.", style="yellow")


# ---------------------------------------------------------------------------
# Fluxo 3 — Executar checks pendentes agora
# ---------------------------------------------------------------------------

def _flow_run_now() -> None:
    from src.scheduler import run_pending_jobs
    console.print()
    with console.status("Executando jobs pendentes..."):
        run_pending_jobs()
    console.print("Concluído.", style="green")


# ---------------------------------------------------------------------------
# Fluxo 4 — Histórico de preços
# ---------------------------------------------------------------------------

def _flow_history() -> None:
    console.print("\n[bold]Histórico de preços[/bold]")
    origin = _ask("Código IATA de origem").upper()
    destination = _ask("Código IATA de destino").upper()

    records = get_history(origin, destination, days=30)
    stats = get_price_stats(origin, destination, days=30)

    if not records:
        console.print(f"Nenhum histórico para {origin} → {destination}.", style="yellow")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("Companhia")
    table.add_column("Tipo", justify="center")
    table.add_column("Duração", justify="right")
    table.add_column("Preço", justify="right")
    table.add_column("Buscado em")

    for r in records:
        tipo = "Direto" if r.is_direct else f"{r.stops} con."
        table.add_row(
            r.airline,
            tipo,
            format_duration(r.duration_minutes),
            format_price(r.price_brl),
            r.searched_at.strftime("%d/%m %H:%M"),
        )

    console.print()
    console.print(table)

    if stats:
        console.print(
            f"  Média 30d: [bold]{format_price(stats['avg'])}[/bold]  |  "
            f"Menor: [green]{format_price(stats['min'])}[/green]  |  "
            f"Maior: [red]{format_price(stats['max'])}[/red]"
        )


# ---------------------------------------------------------------------------
# Helpers de input
# ---------------------------------------------------------------------------

def _ask(prompt: str) -> str:
    while True:
        val = console.input(f"[cyan]{prompt}:[/cyan] ").strip()
        if val:
            return val
        console.print("Campo obrigatório.", style="yellow")


def _ask_int(prompt: str, min_val: int = 0) -> int:
    while True:
        raw = console.input(f"[cyan]{prompt}:[/cyan] ").strip()
        if raw.isdigit() and int(raw) >= min_val:
            return int(raw)
        console.print(f"Digite um número inteiro >= {min_val}.", style="yellow")


def _ask_dates() -> tuple[date, date]:
    """Solicita datas de ida e volta, com suporte a 'daqui N dias'."""
    console.print("[dim]Deixe em branco para usar janela de dias a partir de hoje.[/dim]")

    raw_departure = console.input("[cyan]Data de ida (dd/mm/aaaa)[/cyan] ou Enter: ").strip()

    if raw_departure:
        departure_date = _parse_date(raw_departure)
    else:
        days_from_now = _ask_int("Daqui quantos dias?", min_val=1)
        departure_date = date.today() + timedelta(days=days_from_now)

    duration_days = _ask_int("Duração da viagem (dias)", min_val=1)
    return_date = departure_date + timedelta(days=duration_days)

    console.print(
        f"  Ida: [bold]{departure_date.strftime('%d/%m/%Y')}[/bold]  "
        f"Volta: [bold]{return_date.strftime('%d/%m/%Y')}[/bold]"
    )
    return departure_date, return_date


def _parse_date(raw: str) -> date:
    while True:
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            raw = console.input("[yellow]Formato inválido. Use dd/mm/aaaa:[/yellow] ").strip()


# ---------------------------------------------------------------------------
# Exibição de resultados
# ---------------------------------------------------------------------------

def _print_results_table(results, stats: Optional[dict]) -> None:
    first = results[0]
    title = (
        f"✈️  {first.origin} → {first.destination}  |  "
        f"{first.departure_date.strftime('%d/%m')} → {first.return_date.strftime('%d/%m')}  |  "
        f"{first.passengers} passageiro(s)"
    )

    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Companhia")
    table.add_column("Tipo", justify="center")
    table.add_column("Duração", justify="right")
    table.add_column("Preço", justify="right", style="bold green")

    for r in results:
        tipo = "Direto" if r.is_direct else f"{r.stops} conexão(ões)"
        table.add_row(r.airline, tipo, format_duration(r.duration_minutes), format_price(r.price_brl))

    console.print()
    console.print(table)

    if stats:
        console.print(
            f"  📉 Histórico 30d: média [bold]{format_price(stats['avg'])}[/bold]  |  "
            f"menor [green]{format_price(stats['min'])}[/green]"
        )
    console.print()
