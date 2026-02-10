#!/usr/bin/env python3
"""
Diagnostic script to check available MetaTrader symbols via MetaApi.
Run this to see what symbols your MetaTrader broker supports and identify
the correct symbol names for indices.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Expected symbols from the app
APP_INDICES = ['US30', 'US500', 'NAS100', 'US2000', 'DE40', 'UK100', 'FR40', 'EU50', 'ES35', 'IT40', 'JP225', 'HK50', 'AU200', 'CN50', 'VIX']

# Common variations for each index
INDEX_PATTERNS = {
    'US30': ['US30', 'DJ30', 'DJI30', 'DOW30', 'DJIA', 'WS30'],
    'US500': ['US500', 'SPX500', 'SP500', 'SPX', 'SPA35'],
    'NAS100': ['NAS100', 'USTEC', 'NDX100', 'NASDAQ', 'NDX', 'USTECH'],
    'US2000': ['US2000', 'RUSSELL', 'RUT', 'RTY', 'RUSS2000'],
    'DE40': ['DE40', 'GER40', 'GER30', 'DAX40', 'DAX', 'DE30'],
    'UK100': ['UK100', 'FTSE100', 'FTSE', 'UK100'],
    'FR40': ['FR40', 'FRA40', 'CAC40', 'CAC', 'F40'],
    'EU50': ['EU50', 'EUSTX50', 'STOXX50', 'SX5E', 'EURO50'],
    'ES35': ['ES35', 'ESP35', 'IBEX35', 'IBEX', 'SPA35'],
    'IT40': ['IT40', 'ITA40', 'FTMIB', 'MIB'],
    'JP225': ['JP225', 'JPN225', 'NIKKEI', 'NI225', 'JAP225'],
    'HK50': ['HK50', 'HSI', 'HANGSENG', 'HK33', 'HKIND'],
    'AU200': ['AU200', 'AUS200', 'ASX200', 'ASX', 'AUIND'],
    'CN50': ['CN50', 'CHINA50', 'CHINAA50', 'A50', 'CHN50'],
    'VIX': ['VIX', 'VOLATILITY', 'UVXY', 'VIXM'],
}


async def check_symbols():
    from src.engines.trading.metatrader_broker import MetaTraderBroker

    access_token = os.environ.get("METAAPI_ACCESS_TOKEN")
    account_id = os.environ.get("METAAPI_ACCOUNT_ID")

    if not access_token or not account_id:
        print("ERROR: METAAPI_ACCESS_TOKEN and METAAPI_ACCOUNT_ID must be set")
        print("\nCurrent environment variables:")
        print(f"  METAAPI_ACCESS_TOKEN: {'SET' if access_token else 'NOT SET'}")
        print(f"  METAAPI_ACCOUNT_ID: {'SET' if account_id else 'NOT SET'}")
        return

    print(f"Connecting to MetaTrader via MetaApi...")
    print(f"Account ID: {account_id[:8]}...")

    broker = MetaTraderBroker(
        access_token=access_token,
        account_id=account_id,
    )

    try:
        await broker.connect()
        print("Connected!\n")
    except Exception as e:
        print(f"ERROR connecting: {e}")
        return

    # Get all symbols
    symbols_data = await broker.get_symbols()

    # Extract symbol names
    all_symbols = []
    for sym in symbols_data:
        if isinstance(sym, dict):
            all_symbols.append(sym.get('symbol', ''))
        else:
            all_symbols.append(str(sym))

    all_symbols_upper = {s.upper(): s for s in all_symbols}

    print("=" * 70)
    print("AVAILABLE SYMBOLS ON YOUR METATRADER BROKER")
    print("=" * 70)
    print(f"\nTotal symbols available: {len(all_symbols)}")

    # Categorize symbols
    indices_found = []
    forex_found = []
    metals_found = []
    commodities_found = []
    crypto_found = []
    other_found = []

    for sym in sorted(all_symbols):
        sym_upper = sym.upper()
        # Check if it's an index
        is_index = any(
            pattern in sym_upper
            for patterns in INDEX_PATTERNS.values()
            for pattern in patterns
        ) or any(x in sym_upper for x in ['30', '40', '50', '100', '200', '225', '500', 'DAX', 'FTSE', 'CAC', 'IBEX', 'NIKKEI', 'STOXX'])

        if is_index:
            indices_found.append(sym)
        elif any(x in sym_upper for x in ['XAU', 'XAG', 'GOLD', 'SILVER', 'XPT', 'XPD', 'PLAT', 'PALL']):
            metals_found.append(sym)
        elif any(x in sym_upper for x in ['OIL', 'WTI', 'BRENT', 'GAS', 'NATGAS', 'UKO', 'USO', 'XTI', 'XBR']):
            commodities_found.append(sym)
        elif any(x in sym_upper for x in ['BTC', 'ETH', 'LTC', 'XRP', 'CRYPTO']):
            crypto_found.append(sym)
        elif len(sym) <= 8 and not any(c.isdigit() for c in sym[:3]):
            forex_found.append(sym)
        else:
            other_found.append(sym)

    # Print indices (most important for this diagnostic)
    print(f"\n{'='*70}")
    print("INDICES FOUND ON YOUR BROKER (this is what we need!)")
    print("=" * 70)

    if indices_found:
        for sym in sorted(indices_found):
            print(f"  - {sym}")
    else:
        print("  NO INDICES FOUND! Your broker may not offer index CFDs.")

    # Print other categories
    print(f"\n{'='*70}")
    print(f"FOREX ({len(forex_found)} symbols)")
    print("=" * 70)
    for sym in sorted(forex_found)[:15]:
        print(f"  - {sym}")
    if len(forex_found) > 15:
        print(f"  ... and {len(forex_found) - 15} more")

    print(f"\n{'='*70}")
    print(f"METALS ({len(metals_found)} symbols)")
    print("=" * 70)
    for sym in sorted(metals_found):
        print(f"  - {sym}")

    print(f"\n{'='*70}")
    print(f"COMMODITIES/ENERGY ({len(commodities_found)} symbols)")
    print("=" * 70)
    for sym in sorted(commodities_found):
        print(f"  - {sym}")

    if crypto_found:
        print(f"\n{'='*70}")
        print(f"CRYPTO ({len(crypto_found)} symbols)")
        print("=" * 70)
        for sym in sorted(crypto_found)[:10]:
            print(f"  - {sym}")
        if len(crypto_found) > 10:
            print(f"  ... and {len(crypto_found) - 10} more")

    # Now check which app symbols can be matched
    print(f"\n{'='*70}")
    print("SYMBOL MAPPING ANALYSIS")
    print("=" * 70)
    print("\nChecking if app symbols can be found on your broker:\n")

    matched = {}
    not_matched = []

    for app_symbol in APP_INDICES:
        patterns = INDEX_PATTERNS.get(app_symbol, [app_symbol])
        found = None

        for pattern in patterns:
            # Check exact match (case insensitive)
            if pattern.upper() in all_symbols_upper:
                found = all_symbols_upper[pattern.upper()]
                break

            # Check if any broker symbol starts with pattern
            for broker_sym in all_symbols:
                if broker_sym.upper().startswith(pattern.upper()):
                    found = broker_sym
                    break
            if found:
                break

        if found:
            matched[app_symbol] = found
            print(f"  {app_symbol:10} -> {found:15} FOUND")
        else:
            not_matched.append(app_symbol)
            print(f"  {app_symbol:10} -> {'???':15} NOT FOUND")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  Matched indices: {len(matched)}/{len(APP_INDICES)}")
    print(f"  Missing indices: {len(not_matched)}")

    if not_matched:
        print(f"\n  Missing: {', '.join(not_matched)}")
        print("\n  These indices may not be available on your broker, or they use")
        print("  different symbol names. Check the 'INDICES FOUND' section above")
        print("  to see what your broker actually offers.")

    # If there are broker indices not matched to app symbols, show them
    matched_broker_symbols = set(matched.values())
    unmatched_broker_indices = [s for s in indices_found if s not in matched_broker_symbols]

    if unmatched_broker_indices:
        print(f"\n{'='*70}")
        print("BROKER INDICES NOT AUTOMATICALLY MAPPED")
        print("=" * 70)
        print("  These broker symbols weren't mapped to app symbols.")
        print("  You may need to add them to SYMBOL_ALIASES in metatrader_broker.py:\n")
        for sym in sorted(unmatched_broker_indices):
            print(f"  - {sym}")

    # Generate code suggestion if needed
    if not_matched or unmatched_broker_indices:
        print(f"\n{'='*70}")
        print("SUGGESTED SYMBOL_ALIASES UPDATE")
        print("=" * 70)
        print("\n  If your broker uses different symbol names, update the")
        print("  SYMBOL_ALIASES dict in metatrader_broker.py. For example:\n")
        print("  SYMBOL_ALIASES = {")
        for app_sym, broker_sym in matched.items():
            if app_sym != broker_sym:
                print(f"      '{app_sym}': ['{broker_sym}', ...],")
        print("      # Add your broker's index symbols here")
        for sym in sorted(unmatched_broker_indices)[:5]:
            possible_app = None
            sym_upper = sym.upper()
            for app_sym, patterns in INDEX_PATTERNS.items():
                if any(p.upper() in sym_upper for p in patterns):
                    possible_app = app_sym
                    break
            if possible_app:
                print(f"      '{possible_app}': ['{sym}', ...],  # Found on your broker")
        print("  }")

    await broker.disconnect()
    print("\nDiagnostic complete!")


if __name__ == "__main__":
    asyncio.run(check_symbols())
