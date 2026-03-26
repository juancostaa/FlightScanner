def format_duration(minutes: int) -> str:
    """Converte minutos em string legível, ex: '14h20'."""
    hours, mins = divmod(minutes, 60)
    return f"{hours}h{mins:02d}"


def format_price(price_brl: float) -> str:
    """Formata valor em BRL, ex: 'R$ 4.820'."""
    return f"R$ {price_brl:,.0f}".replace(",", ".")
