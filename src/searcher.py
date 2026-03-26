from datetime import date, datetime
from typing import List

import serpapi
from serpapi.exceptions import HTTPError

import config
from src.models import FlightResult

_client = None


def _get_client() -> serpapi.Client:
    global _client
    if _client is None:
        _client = serpapi.Client(api_key=config.SERPAPI_KEY)
    return _client


def search_flights(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date,
    passengers: int,
) -> List[FlightResult]:
    """Busca passagens no Google Flights via SerpAPI.

    Args:
        origin: Código IATA do aeroporto de origem (ex: "GRU").
        destination: Código IATA do aeroporto de destino (ex: "LIS").
        departure_date: Data de ida.
        return_date: Data de volta.
        passengers: Número de adultos.

    Returns:
        Lista de FlightResult ordenada por preço (menor primeiro).

    Raises:
        ValueError: Se a API retornar erro ou não houver resultados.
    """
    params = {
        "engine": "google_flights",
        "departure_id": origin.upper(),
        "arrival_id": destination.upper(),
        "outbound_date": departure_date.isoformat(),
        "return_date": return_date.isoformat(),
        "type": "1",  # round trip
        "adults": passengers,
        "travel_class": "1",  # economy
        "currency": "BRL",
        "hl": "pt",
    }

    try:
        response = _get_client().search(params)
    except HTTPError as e:
        status = getattr(e, "status_code", None) or str(e)
        if "401" in str(e):
            raise ValueError("Chave da SerpAPI inválida ou expirada. Verifique SERPAPI_KEY no .env.")
        raise ValueError(f"Erro ao chamar a SerpAPI (HTTP {status}): {e}")

    error = response.get("error")
    if error:
        raise ValueError(f"Erro na API do SerpAPI: {error}")

    raw_flights = response.get("best_flights", []) + response.get("other_flights", [])

    if not raw_flights:
        raise ValueError(
            f"Nenhuma passagem encontrada para {origin} → {destination} "
            f"em {departure_date.isoformat()}."
        )

    results = [_parse_flight(f, origin, destination, departure_date, return_date, passengers) for f in raw_flights]
    results.sort(key=lambda r: r.price_brl)
    return results


def _parse_flight(
    raw: dict,
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date,
    passengers: int,
) -> FlightResult:
    """Converte um item da resposta SerpAPI em FlightResult."""
    legs: list = raw.get("flights", [])

    airline = legs[0].get("airline", "Desconhecida") if legs else "Desconhecida"
    stops = max(len(legs) - 1, 0)
    is_direct = stops == 0
    duration_minutes = raw.get("total_duration", 0)
    price_brl = float(raw.get("price", 0))

    return FlightResult(
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        return_date=return_date,
        airline=airline,
        is_direct=is_direct,
        stops=stops,
        duration_minutes=duration_minutes,
        price_brl=price_brl,
        passengers=passengers,
        searched_at=datetime.now(),
    )
