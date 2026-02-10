#!/usr/bin/env python3
"""
Diagnostic script to check available OANDA instruments.
Run this to see what instruments your OANDA account supports.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_instruments():
    from src.engines.trading.oanda_broker import OANDABroker

    api_key = os.environ.get("OANDA_API_KEY")
    account_id = os.environ.get("OANDA_ACCOUNT_ID")
    environment = os.environ.get("OANDA_ENVIRONMENT", "practice")

    if not api_key or not account_id:
        print("ERROR: OANDA_API_KEY and OANDA_ACCOUNT_ID must be set")
        return

    print(f"Connecting to OANDA ({environment})...")
    print(f"Account ID: {account_id[:8]}...")

    broker = OANDABroker(
        api_key=api_key,
        account_id=account_id,
        environment=environment
    )

    await broker.connect()
    print("Connected!\n")

    # Get all instruments
    instruments = await broker.get_instruments()

    # Categorize instruments
    forex = []
    indices = []
    commodities = []
    metals = []
    bonds = []
    other = []

    for inst in instruments:
        name = inst.symbol
        if any(x in name for x in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]) and "_" in name and len(name) == 7:
            forex.append(name)
        elif any(x in name for x in ["US30", "SPX", "NAS", "UK100", "DE30", "DE40", "FR40", "JP225", "AU200", "HK", "CN50", "EU50"]):
            indices.append(name)
        elif any(x in name for x in ["XAU", "XAG", "XPT", "XPD", "XCU"]):
            metals.append(name)
        elif any(x in name for x in ["BCO", "WTICO", "NATGAS", "CORN", "WHEAT", "SOYBN", "SUGAR"]):
            commodities.append(name)
        elif any(x in name for x in ["USB", "UK10", "DE10", "BUND"]):
            bonds.append(name)
        else:
            other.append(name)

    print("=" * 60)
    print("AVAILABLE INSTRUMENTS ON YOUR OANDA ACCOUNT")
    print("=" * 60)

    print(f"\n📈 INDICES ({len(indices)}):")
    for inst in sorted(indices):
        print(f"  - {inst}")

    print(f"\n💱 FOREX ({len(forex)}):")
    for inst in sorted(forex)[:20]:
        print(f"  - {inst}")
    if len(forex) > 20:
        print(f"  ... and {len(forex) - 20} more")

    print(f"\n🥇 METALS ({len(metals)}):")
    for inst in sorted(metals):
        print(f"  - {inst}")

    print(f"\n🛢️ COMMODITIES ({len(commodities)}):")
    for inst in sorted(commodities):
        print(f"  - {inst}")

    print(f"\n📊 BONDS ({len(bonds)}):")
    for inst in sorted(bonds):
        print(f"  - {inst}")

    if other:
        print(f"\n📋 OTHER ({len(other)}):")
        for inst in sorted(other)[:10]:
            print(f"  - {inst}")
        if len(other) > 10:
            print(f"  ... and {len(other) - 10} more")

    print("\n" + "=" * 60)
    print(f"TOTAL: {len(instruments)} instruments available")
    print("=" * 60)

    # Check specific indices we want
    print("\n🔍 CHECKING SPECIFIC INDICES WE NEED:")
    wanted = {
        "US30_USD": "Dow Jones",
        "SPX500_USD": "S&P 500",
        "NAS100_USD": "NASDAQ 100",
        "UK100_GBP": "FTSE 100",
        "DE30_EUR": "DAX",
        "FR40_EUR": "CAC 40",
        "EU50_EUR": "Euro Stoxx 50",
        "JP225_USD": "Nikkei 225",
        "AU200_AUD": "ASX 200",
        "HK33_HKD": "Hang Seng",
        "CN50_USD": "China A50",
    }

    available_names = {inst.symbol for inst in instruments}

    for symbol, name in wanted.items():
        status = "✅ AVAILABLE" if symbol in available_names else "❌ NOT AVAILABLE"
        print(f"  {symbol} ({name}): {status}")

    await broker.disconnect()

if __name__ == "__main__":
    asyncio.run(check_instruments())
