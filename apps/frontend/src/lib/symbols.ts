/**
 * TradingView CFD Symbols
 * Organized by category: Forex, Commodities, Metals, Indices, Futures
 * NO stocks included
 */

export interface TradingSymbol {
  value: string        // Internal value (e.g., "EUR_USD")
  label: string        // Display label (e.g., "EUR/USD")
  tvSymbol: string     // TradingView symbol format (e.g., "FX:EURUSD")
  category: 'forex' | 'commodities' | 'metals' | 'indices' | 'futures'
  displayName: string  // Short name for cards
}

// ============ FOREX PAIRS ============
export const FOREX_SYMBOLS: TradingSymbol[] = [
  // Major Pairs
  { value: 'EUR_USD', label: 'EUR/USD', tvSymbol: 'FX:EURUSD', category: 'forex', displayName: 'EUR/USD' },
  { value: 'GBP_USD', label: 'GBP/USD', tvSymbol: 'FX:GBPUSD', category: 'forex', displayName: 'GBP/USD' },
  { value: 'USD_JPY', label: 'USD/JPY', tvSymbol: 'FX:USDJPY', category: 'forex', displayName: 'USD/JPY' },
  { value: 'USD_CHF', label: 'USD/CHF', tvSymbol: 'FX:USDCHF', category: 'forex', displayName: 'USD/CHF' },
  { value: 'AUD_USD', label: 'AUD/USD', tvSymbol: 'FX:AUDUSD', category: 'forex', displayName: 'AUD/USD' },
  { value: 'USD_CAD', label: 'USD/CAD', tvSymbol: 'FX:USDCAD', category: 'forex', displayName: 'USD/CAD' },
  { value: 'NZD_USD', label: 'NZD/USD', tvSymbol: 'FX:NZDUSD', category: 'forex', displayName: 'NZD/USD' },

  // Cross Pairs
  { value: 'EUR_GBP', label: 'EUR/GBP', tvSymbol: 'FX:EURGBP', category: 'forex', displayName: 'EUR/GBP' },
  { value: 'EUR_JPY', label: 'EUR/JPY', tvSymbol: 'FX:EURJPY', category: 'forex', displayName: 'EUR/JPY' },
  { value: 'GBP_JPY', label: 'GBP/JPY', tvSymbol: 'FX:GBPJPY', category: 'forex', displayName: 'GBP/JPY' },
  { value: 'EUR_CHF', label: 'EUR/CHF', tvSymbol: 'FX:EURCHF', category: 'forex', displayName: 'EUR/CHF' },
  { value: 'EUR_AUD', label: 'EUR/AUD', tvSymbol: 'FX:EURAUD', category: 'forex', displayName: 'EUR/AUD' },
  { value: 'EUR_CAD', label: 'EUR/CAD', tvSymbol: 'FX:EURCAD', category: 'forex', displayName: 'EUR/CAD' },
  { value: 'GBP_CHF', label: 'GBP/CHF', tvSymbol: 'FX:GBPCHF', category: 'forex', displayName: 'GBP/CHF' },
  { value: 'GBP_AUD', label: 'GBP/AUD', tvSymbol: 'FX:GBPAUD', category: 'forex', displayName: 'GBP/AUD' },
  { value: 'AUD_JPY', label: 'AUD/JPY', tvSymbol: 'FX:AUDJPY', category: 'forex', displayName: 'AUD/JPY' },
  { value: 'AUD_CAD', label: 'AUD/CAD', tvSymbol: 'FX:AUDCAD', category: 'forex', displayName: 'AUD/CAD' },
  { value: 'AUD_NZD', label: 'AUD/NZD', tvSymbol: 'FX:AUDNZD', category: 'forex', displayName: 'AUD/NZD' },
  { value: 'CAD_JPY', label: 'CAD/JPY', tvSymbol: 'FX:CADJPY', category: 'forex', displayName: 'CAD/JPY' },
  { value: 'NZD_JPY', label: 'NZD/JPY', tvSymbol: 'FX:NZDJPY', category: 'forex', displayName: 'NZD/JPY' },
  { value: 'CHF_JPY', label: 'CHF/JPY', tvSymbol: 'FX:CHFJPY', category: 'forex', displayName: 'CHF/JPY' },

  // Exotic Pairs
  { value: 'EUR_TRY', label: 'EUR/TRY', tvSymbol: 'FX:EURTRY', category: 'forex', displayName: 'EUR/TRY' },
  { value: 'USD_TRY', label: 'USD/TRY', tvSymbol: 'FX:USDTRY', category: 'forex', displayName: 'USD/TRY' },
  { value: 'USD_MXN', label: 'USD/MXN', tvSymbol: 'FX:USDMXN', category: 'forex', displayName: 'USD/MXN' },
  { value: 'USD_ZAR', label: 'USD/ZAR', tvSymbol: 'FX:USDZAR', category: 'forex', displayName: 'USD/ZAR' },
  { value: 'USD_SGD', label: 'USD/SGD', tvSymbol: 'FX:USDSGD', category: 'forex', displayName: 'USD/SGD' },
  { value: 'USD_HKD', label: 'USD/HKD', tvSymbol: 'FX:USDHKD', category: 'forex', displayName: 'USD/HKD' },
  { value: 'USD_NOK', label: 'USD/NOK', tvSymbol: 'FX:USDNOK', category: 'forex', displayName: 'USD/NOK' },
  { value: 'USD_SEK', label: 'USD/SEK', tvSymbol: 'FX:USDSEK', category: 'forex', displayName: 'USD/SEK' },
  { value: 'USD_DKK', label: 'USD/DKK', tvSymbol: 'FX:USDDKK', category: 'forex', displayName: 'USD/DKK' },
  { value: 'USD_PLN', label: 'USD/PLN', tvSymbol: 'FX:USDPLN', category: 'forex', displayName: 'USD/PLN' },
]

// ============ METALS ============
export const METALS_SYMBOLS: TradingSymbol[] = [
  { value: 'XAU_USD', label: 'XAU/USD (Gold)', tvSymbol: 'OANDA:XAUUSD', category: 'metals', displayName: 'Gold' },
  { value: 'XAG_USD', label: 'XAG/USD (Silver)', tvSymbol: 'OANDA:XAGUSD', category: 'metals', displayName: 'Silver' },
  { value: 'XPT_USD', label: 'XPT/USD (Platinum)', tvSymbol: 'OANDA:XPTUSD', category: 'metals', displayName: 'Platinum' },
  { value: 'XPD_USD', label: 'XPD/USD (Palladium)', tvSymbol: 'OANDA:XPDUSD', category: 'metals', displayName: 'Palladium' },
  { value: 'XCU_USD', label: 'Copper', tvSymbol: 'COMEX:HG1!', category: 'metals', displayName: 'Copper' },
]

// ============ COMMODITIES ============
export const COMMODITIES_SYMBOLS: TradingSymbol[] = [
  // Energy
  { value: 'WTI_USD', label: 'WTI Crude Oil', tvSymbol: 'TVC:USOIL', category: 'commodities', displayName: 'WTI Oil' },
  { value: 'BRENT_USD', label: 'Brent Crude Oil', tvSymbol: 'TVC:UKOIL', category: 'commodities', displayName: 'Brent Oil' },
  { value: 'NATGAS_USD', label: 'Natural Gas', tvSymbol: 'NYMEX:NG1!', category: 'commodities', displayName: 'Nat Gas' },

  // Agricultural
  { value: 'WHEAT_USD', label: 'Wheat', tvSymbol: 'CBOT:ZW1!', category: 'commodities', displayName: 'Wheat' },
  { value: 'CORN_USD', label: 'Corn', tvSymbol: 'CBOT:ZC1!', category: 'commodities', displayName: 'Corn' },
  { value: 'SOYBEAN_USD', label: 'Soybeans', tvSymbol: 'CBOT:ZS1!', category: 'commodities', displayName: 'Soybeans' },
  { value: 'COFFEE_USD', label: 'Coffee', tvSymbol: 'ICEUS:KC1!', category: 'commodities', displayName: 'Coffee' },
  { value: 'SUGAR_USD', label: 'Sugar', tvSymbol: 'ICEUS:SB1!', category: 'commodities', displayName: 'Sugar' },
  { value: 'COCOA_USD', label: 'Cocoa', tvSymbol: 'ICEUS:CC1!', category: 'commodities', displayName: 'Cocoa' },
  { value: 'COTTON_USD', label: 'Cotton', tvSymbol: 'ICEUS:CT1!', category: 'commodities', displayName: 'Cotton' },
]

// ============ INDICES ============
export const INDICES_SYMBOLS: TradingSymbol[] = [
  // US Indices
  { value: 'US30', label: 'US30 (Dow Jones)', tvSymbol: 'FOREXCOM:DJI', category: 'indices', displayName: 'US30' },
  { value: 'US500', label: 'S&P 500', tvSymbol: 'FOREXCOM:SPX500', category: 'indices', displayName: 'S&P 500' },
  { value: 'NAS100', label: 'NASDAQ 100', tvSymbol: 'FOREXCOM:NSXUSD', category: 'indices', displayName: 'NAS100' },
  { value: 'US2000', label: 'Russell 2000', tvSymbol: 'FOREXCOM:RUSS2000', category: 'indices', displayName: 'Russell' },

  // European Indices
  { value: 'DE40', label: 'DAX 40 (Germany)', tvSymbol: 'PEPPERSTONE:GER40', category: 'indices', displayName: 'DAX40' },
  { value: 'UK100', label: 'FTSE 100 (UK)', tvSymbol: 'PEPPERSTONE:UK100', category: 'indices', displayName: 'FTSE100' },
  { value: 'FR40', label: 'CAC 40 (France)', tvSymbol: 'PEPPERSTONE:FRA40', category: 'indices', displayName: 'CAC40' },
  { value: 'EU50', label: 'Euro Stoxx 50', tvSymbol: 'PEPPERSTONE:EUSTX50', category: 'indices', displayName: 'EU50' },
  { value: 'ES35', label: 'IBEX 35 (Spain)', tvSymbol: 'PEPPERSTONE:ESP35', category: 'indices', displayName: 'IBEX35' },
  { value: 'IT40', label: 'FTSE MIB (Italy)', tvSymbol: 'PEPPERSTONE:ITA40', category: 'indices', displayName: 'FTMIB' },

  // Asian Indices
  { value: 'JP225', label: 'Nikkei 225 (Japan)', tvSymbol: 'PEPPERSTONE:JPN225', category: 'indices', displayName: 'Nikkei' },
  { value: 'HK50', label: 'Hang Seng (HK)', tvSymbol: 'PEPPERSTONE:HK50', category: 'indices', displayName: 'HSI' },
  { value: 'AU200', label: 'ASX 200 (Australia)', tvSymbol: 'PEPPERSTONE:AUS200', category: 'indices', displayName: 'ASX200' },
  { value: 'CN50', label: 'China A50', tvSymbol: 'PEPPERSTONE:CHINA50', category: 'indices', displayName: 'CN50' },

  // Other
  { value: 'VIX', label: 'VIX (Volatility)', tvSymbol: 'TVC:VIX', category: 'indices', displayName: 'VIX' },
]

// ============ FUTURES ============
export const FUTURES_SYMBOLS: TradingSymbol[] = [
  // Index Futures
  { value: 'ES1', label: 'E-mini S&P 500', tvSymbol: 'CME:ES1!', category: 'futures', displayName: 'ES' },
  { value: 'NQ1', label: 'E-mini NASDAQ', tvSymbol: 'CME:NQ1!', category: 'futures', displayName: 'NQ' },
  { value: 'YM1', label: 'E-mini Dow', tvSymbol: 'CBOT:YM1!', category: 'futures', displayName: 'YM' },
  { value: 'RTY1', label: 'E-mini Russell', tvSymbol: 'CME:RTY1!', category: 'futures', displayName: 'RTY' },

  // Metal Futures
  { value: 'GC1', label: 'Gold Futures', tvSymbol: 'COMEX:GC1!', category: 'futures', displayName: 'GC' },
  { value: 'SI1', label: 'Silver Futures', tvSymbol: 'COMEX:SI1!', category: 'futures', displayName: 'SI' },

  // Energy Futures
  { value: 'CL1', label: 'Crude Oil Futures', tvSymbol: 'NYMEX:CL1!', category: 'futures', displayName: 'CL' },
  { value: 'NG1', label: 'Natural Gas Futures', tvSymbol: 'NYMEX:NG1!', category: 'futures', displayName: 'NG' },

  // Currency Futures
  { value: '6E1', label: 'Euro FX Futures', tvSymbol: 'CME:6E1!', category: 'futures', displayName: '6E' },
  { value: '6B1', label: 'British Pound Futures', tvSymbol: 'CME:6B1!', category: 'futures', displayName: '6B' },
  { value: '6J1', label: 'Japanese Yen Futures', tvSymbol: 'CME:6J1!', category: 'futures', displayName: '6J' },

  // Bond Futures
  { value: 'ZB1', label: '30-Year T-Bond', tvSymbol: 'CBOT:ZB1!', category: 'futures', displayName: 'ZB' },
  { value: 'ZN1', label: '10-Year T-Note', tvSymbol: 'CBOT:ZN1!', category: 'futures', displayName: 'ZN' },
]

// ============ ALL SYMBOLS COMBINED ============
export const ALL_SYMBOLS: TradingSymbol[] = [
  ...FOREX_SYMBOLS,
  ...METALS_SYMBOLS,
  ...COMMODITIES_SYMBOLS,
  ...INDICES_SYMBOLS,
  ...FUTURES_SYMBOLS,
]

// ============ CATEGORY LABELS ============
export const CATEGORY_LABELS: Record<TradingSymbol['category'], string> = {
  forex: 'Forex',
  commodities: 'Commodities',
  metals: 'Metals',
  indices: 'Indices',
  futures: 'Futures',
}

// ============ GET SYMBOLS BY CATEGORY ============
export function getSymbolsByCategory(category: TradingSymbol['category']): TradingSymbol[] {
  return ALL_SYMBOLS.filter(s => s.category === category)
}

// ============ CONVERT TO TRADINGVIEW FORMAT ============
export function toTradingViewSymbol(value: string): string {
  const symbol = ALL_SYMBOLS.find(s => s.value === value)
  return symbol?.tvSymbol || value.replace('_', '')
}

// ============ CONVERT TO OANDA FORMAT ============
export function toOandaSymbol(value: string): string {
  // OANDA uses underscore format
  return value
}

// ============ FIND SYMBOL ============
export function findSymbol(value: string): TradingSymbol | undefined {
  return ALL_SYMBOLS.find(s => s.value === value)
}
