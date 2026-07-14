from typing import Optional

from modules.settings.services import SettingsService


class CurrencyFormatter:
    @classmethod
    async def get_currency(cls, db) -> str:
        """Get currency dari settings."""
        settings_service = SettingsService(db)
        pricing = await settings_service.get_pricing_settings()
        return pricing.currency if pricing else "IDR"

    @classmethod
    async def format_currency(
        cls,
        db,
        amount: float,
        currency: Optional[str] = None
    ) -> str:
        """Format currency dengan symbol dari settings."""
        if not currency:
            currency = await cls.get_currency(db)

        symbols = {
            "IDR": "Rp",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
        }
        symbol = symbols.get(currency, "Rp")

        # Format dengan locale
        if currency == "IDR":
            return f"{symbol} {amount:,.0f}".replace(",", ".")
        else:
            return f"{symbol}{amount:,.2f}"
