def format_currency(value: float) -> str:
    """Formata um valor float para moeda brasileira: R$ 1.234,56"""
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"
