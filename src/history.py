import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional

import config
from src.models import FlightResult


@contextmanager
def _get_conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flight_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            origin          TEXT NOT NULL,
            destination     TEXT NOT NULL,
            departure_date  TEXT NOT NULL,
            return_date     TEXT NOT NULL,
            airline         TEXT NOT NULL,
            is_direct       INTEGER NOT NULL,
            stops           INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            price_brl       REAL NOT NULL,
            passengers      INTEGER NOT NULL,
            searched_at     TEXT NOT NULL
        )
    """)


def save_results(results: List[FlightResult]) -> None:
    """Persiste resultados de busca no banco SQLite."""
    with _get_conn() as conn:
        _init_db(conn)
        conn.executemany(
            """
            INSERT INTO flight_results (
                origin, destination, departure_date, return_date,
                airline, is_direct, stops, duration_minutes,
                price_brl, passengers, searched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.origin,
                    r.destination,
                    r.departure_date.isoformat(),
                    r.return_date.isoformat(),
                    r.airline,
                    int(r.is_direct),
                    r.stops,
                    r.duration_minutes,
                    r.price_brl,
                    r.passengers,
                    r.searched_at.isoformat(),
                )
                for r in results
            ],
        )


def get_price_stats(
    origin: str, destination: str, days: int = 30
) -> Optional[dict]:
    """Retorna estatísticas de preço (média, mínimo) dos últimos N dias.

    Retorna None se não houver histórico para a rota.
    """
    since = (datetime.now() - timedelta(days=days)).isoformat()

    with _get_conn() as conn:
        _init_db(conn)
        row = conn.execute(
            """
            SELECT
                AVG(price_brl) AS avg,
                MIN(price_brl) AS min,
                MAX(price_brl) AS max,
                COUNT(*)       AS total
            FROM flight_results
            WHERE origin = ?
              AND destination = ?
              AND searched_at >= ?
            """,
            (origin, destination, since),
        ).fetchone()

    if row is None or row["total"] == 0:
        return None

    return {
        "avg": round(row["avg"], 2),
        "min": round(row["min"], 2),
        "max": round(row["max"], 2),
        "total": row["total"],
    }


def get_history(origin: str, destination: str, days: int = 30) -> List[FlightResult]:
    """Retorna os registros brutos dos últimos N dias para uma rota."""
    since = (datetime.now() - timedelta(days=days)).isoformat()

    with _get_conn() as conn:
        _init_db(conn)
        rows = conn.execute(
            """
            SELECT * FROM flight_results
            WHERE origin = ?
              AND destination = ?
              AND searched_at >= ?
            ORDER BY searched_at DESC
            """,
            (origin, destination, since),
        ).fetchall()

    return [
        FlightResult(
            origin=row["origin"],
            destination=row["destination"],
            departure_date=datetime.fromisoformat(row["departure_date"]).date(),
            return_date=datetime.fromisoformat(row["return_date"]).date(),
            airline=row["airline"],
            is_direct=bool(row["is_direct"]),
            stops=row["stops"],
            duration_minutes=row["duration_minutes"],
            price_brl=row["price_brl"],
            passengers=row["passengers"],
            searched_at=datetime.fromisoformat(row["searched_at"]),
        )
        for row in rows
    ]
