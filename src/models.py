from dataclasses import dataclass
from datetime import date, datetime


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


@dataclass
class MonitorJob:
    id: str
    origin: str
    destination: str
    departure_date: date
    return_date: date
    passengers: int
    email: str
    interval_minutes: int
    next_run: datetime
    alert_mode: bool = False
    alert_threshold: float = 0.0
