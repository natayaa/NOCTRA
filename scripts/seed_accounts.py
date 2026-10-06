"""
Seed the default chart of accounts.

Idempotent — matches on code.

Run: python -m scripts.seed_accounts
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.finance.constants import AccountType
from app.modules.finance.models import Account

import app.core.models_registry  # noqa: F401


ACCOUNTS: list[dict] = [
    # Assets
    {"code": "1000", "name": "Cash on hand", "account_type": AccountType.ASSET.value},
    {"code": "1010", "name": "Bank account — BCA", "account_type": AccountType.ASSET.value},
    {"code": "1020", "name": "Bank account — Mandiri", "account_type": AccountType.ASSET.value},
    {"code": "1100", "name": "Accounts receivable", "account_type": AccountType.ASSET.value},
    {"code": "1200", "name": "Inventory — materials", "account_type": AccountType.ASSET.value},
    {"code": "1500", "name": "Equipment", "account_type": AccountType.ASSET.value},

    # Liabilities
    {"code": "2000", "name": "Accounts payable", "account_type": AccountType.LIABILITY.value},
    {"code": "2100", "name": "Tax payable (PPN)", "account_type": AccountType.LIABILITY.value},
    {"code": "2500", "name": "Long-term loans", "account_type": AccountType.LIABILITY.value},

    # Equity
    {"code": "3000", "name": "Owner's equity", "account_type": AccountType.EQUITY.value},
    {"code": "3100", "name": "Retained earnings", "account_type": AccountType.EQUITY.value},

    # Revenue
    {"code": "4000", "name": "Revenue — repaint", "account_type": AccountType.REVENUE.value},
    {"code": "4100", "name": "Revenue — restoration", "account_type": AccountType.REVENUE.value},
    {"code": "4200", "name": "Revenue — custom paint", "account_type": AccountType.REVENUE.value},
    {"code": "4300", "name": "Revenue — detailing", "account_type": AccountType.REVENUE.value},
    {"code": "4900", "name": "Revenue — other", "account_type": AccountType.REVENUE.value},

    # Expenses (COGS)
    {"code": "5000", "name": "Cost of materials", "account_type": AccountType.EXPENSE.value},
    {"code": "5100", "name": "Cost of labor", "account_type": AccountType.EXPENSE.value},
    {"code": "5200", "name": "Cost of outsourcing", "account_type": AccountType.EXPENSE.value},

    # Operating expenses
    {"code": "6000", "name": "Rent", "account_type": AccountType.EXPENSE.value},
    {"code": "6100", "name": "Utilities", "account_type": AccountType.EXPENSE.value},
    {"code": "6200", "name": "Salaries (admin)", "account_type": AccountType.EXPENSE.value},
    {"code": "6300", "name": "Marketing", "account_type": AccountType.EXPENSE.value},
    {"code": "6400", "name": "Transport", "account_type": AccountType.EXPENSE.value},
    {"code": "6500", "name": "Maintenance", "account_type": AccountType.EXPENSE.value},
    {"code": "6600", "name": "Professional services", "account_type": AccountType.EXPENSE.value},
    {"code": "6700", "name": "Office supplies", "account_type": AccountType.EXPENSE.value},
    {"code": "6900", "name": "Other operating expenses", "account_type": AccountType.EXPENSE.value},
]


async def main() -> int:
    print("Seeding chart of accounts...")
    created = 0
    skipped = 0

    async with SessionLocal() as db:
        try:
            for item in ACCOUNTS:
                existing = (
                    await db.execute(
                        select(Account).where(Account.code == item["code"])
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    skipped += 1
                    continue
                db.add(Account(**item))
                created += 1
                print(f"  + {item['code']} {item['name']}")

            await db.commit()
        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    print(f"\n✅ Chart of accounts seed complete. Created: {created}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))