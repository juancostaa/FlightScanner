import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from src.emailer import make_subject, send_report
from src.history import get_price_stats, save_results
from src.models import MonitorJob
from src.reporter import build_report, make_report_filename, save_local_report
from src.searcher import search_flights

# Formato usado para serializar/desserializar datas no JSON
_DT_FMT = "%Y-%m-%dT%H:%M:%S"
_DATE_FMT = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Persistência de jobs (jobs.json)
# ---------------------------------------------------------------------------

def save_job(job: MonitorJob) -> None:
    """Persiste um job de monitoramento em data/jobs.json (upsert por id)."""
    jobs = _load_raw()
    jobs[job.id] = _job_to_dict(job)
    _write_raw(jobs)


def load_jobs() -> List[MonitorJob]:
    """Carrega e desserializa todos os jobs de data/jobs.json."""
    return [_dict_to_job(d) for d in _load_raw().values()]


def delete_job(job_id: str) -> None:
    """Remove um job pelo id."""
    jobs = _load_raw()
    jobs.pop(job_id, None)
    _write_raw(jobs)


def create_job(
    origin: str,
    destination: str,
    departure_date,
    return_date,
    passengers: int,
    email: str,
    interval_hours: int,
) -> MonitorJob:
    """Cria e persiste um novo MonitorJob, retornando o objeto criado."""
    job = MonitorJob(
        id=str(uuid.uuid4()),
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        passengers=passengers,
        email=email,
        interval_hours=interval_hours,
        next_run=datetime.now() + timedelta(hours=interval_hours),
    )
    save_job(job)
    return job


# ---------------------------------------------------------------------------
# Execução de jobs
# ---------------------------------------------------------------------------

def run_pending_jobs() -> None:
    """Executa todos os jobs cujo next_run <= agora (modo cron / --run-jobs)."""
    now = datetime.now()
    jobs = load_jobs()
    pending = [j for j in jobs if j.next_run <= now]

    if not pending:
        print("Nenhum job pendente.")
        return

    for job in pending:
        print(f"Executando job {job.id}: {job.origin} → {job.destination}...")
        try:
            _execute_job(job)
            job.next_run = now + timedelta(hours=job.interval_hours)
            save_job(job)
        except Exception as e:
            print(f"  Erro no job {job.id}: {e}")


def schedule_with_apscheduler(job: MonitorJob) -> None:
    """Agenda job em memória com APScheduler e bloqueia até interrupção."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=_execute_job,
        args=[job],
        trigger="interval",
        hours=job.interval_hours,
        next_run_time=datetime.now(),  # executa imediatamente na primeira vez
        id=job.id,
        name=f"{job.origin}→{job.destination}",
    )
    print(f"Agendamento ativo: {job.origin} → {job.destination} a cada {job.interval_hours}h. Ctrl+C para parar.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Agendamento encerrado.")


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _execute_job(job: MonitorJob) -> None:
    """Busca passagens, salva histórico, gera relatório e envia email."""
    results = search_flights(
        job.origin,
        job.destination,
        job.departure_date,
        job.return_date,
        job.passengers,
    )
    save_results(results)

    stats = get_price_stats(job.origin, job.destination)
    report = build_report(results, stats)

    filename = make_report_filename(job.origin, job.destination)
    save_local_report(report["html"], filename)

    subject = make_subject(job.origin, job.destination, results[0].price_brl)
    send_report(job.email, subject, report["html"], report["text"])


def _load_raw() -> dict:
    if not os.path.exists(config.JOBS_PATH):
        return {}
    with open(config.JOBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_raw(jobs: dict) -> None:
    os.makedirs(os.path.dirname(config.JOBS_PATH), exist_ok=True)
    with open(config.JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def _job_to_dict(job: MonitorJob) -> dict:
    return {
        "id": job.id,
        "origin": job.origin,
        "destination": job.destination,
        "departure_date": job.departure_date.isoformat(),
        "return_date": job.return_date.isoformat(),
        "passengers": job.passengers,
        "email": job.email,
        "interval_hours": job.interval_hours,
        "next_run": job.next_run.strftime(_DT_FMT),
    }


def _dict_to_job(d: dict) -> MonitorJob:
    return MonitorJob(
        id=d["id"],
        origin=d["origin"],
        destination=d["destination"],
        departure_date=datetime.strptime(d["departure_date"], _DATE_FMT).date(),
        return_date=datetime.strptime(d["return_date"], _DATE_FMT).date(),
        passengers=d["passengers"],
        email=d["email"],
        interval_hours=d["interval_hours"],
        next_run=datetime.strptime(d["next_run"], _DT_FMT),
    )
