export type CredentialFieldType = 'text' | 'password' | 'number' | 'select'

export type CredentialFieldOption = {
  label: string
  value: string
}

export type PlatformCredentialField = {
  key: string
  label: string
  placeholder: string
  help: string
  required?: boolean
  type?: CredentialFieldType
  options?: CredentialFieldOption[]
  fullWidth?: boolean
}

export type BrokerPlatform = {
  id: string
  label: string
  logoDomain: string
  logoUrl?: string
  credentials: PlatformCredentialField[]
  metrics: string[]
}

export type BrokerDirectoryEntry = {
  id: string
  name: string
  kind: 'broker' | 'prop'
  logoDomain: string
  logoUrl?: string
  platforms: BrokerPlatform[]
}

const credential = (
  key: string,
  label: string,
  placeholder: string,
  help: string,
  options: Partial<PlatformCredentialField> = {},
): PlatformCredentialField => ({
  key,
  label,
  placeholder,
  help,
  required: options.required ?? true,
  type: options.type ?? 'text',
  options: options.options,
  fullWidth: options.fullWidth ?? false,
})

export const PLATFORM_DIRECTORY: Record<string, BrokerPlatform> = {
  mt4: {
    id: 'mt4',
    label: 'MetaTrader 4',
    logoDomain: 'metatrader4.com',
    credentials: [
      credential('account_number', 'Account Number', 'MT4 login number', 'Account/login number shown by your broker.'),
      credential('account_password', 'Password', 'Trading or investor password', 'Use account password. For read-only setup you can use investor password.', { type: 'password' }),
      credential('server_name', 'Server Name', 'Broker-Server (e.g. ICMarketsSC-Demo)', 'Exact MT4 server name from your platform.'),
    ],
    metrics: ['Balance', 'Equity', 'Free Margin', 'Open Positions', 'Daily PnL'],
  },
  mt5: {
    id: 'mt5',
    label: 'MetaTrader 5',
    logoDomain: 'metatrader5.com',
    credentials: [
      credential('account_number', 'Account Number', 'MT5 login number', 'Account/login number shown by your broker.'),
      credential('account_password', 'Password', 'Trading or investor password', 'Use account password. For read-only setup you can use investor password.', { type: 'password' }),
      credential('server_name', 'Server Name', 'Broker-Server (e.g. ICMarketsSC-Demo)', 'Exact MT5 server name from your platform.'),
    ],
    metrics: ['Balance', 'Equity', 'Free Margin', 'Open Positions', 'Daily PnL'],
  },
  ctrader: {
    id: 'ctrader',
    label: 'cTrader',
    logoDomain: 'ctrader.com',
    credentials: [
      credential('account_id', 'cTrader Account ID', 'cTrader account id', 'cTrader account identifier provided by your broker.'),
      credential('account_password', 'Password', 'cTrader password', 'Password for this cTrader account.', { type: 'password' }),
      credential('server_name', 'Server / Environment', 'cTrader server or broker endpoint', 'Server/environment name required by your broker.'),
    ],
    metrics: ['Balance', 'Equity', 'Used Margin', 'Open Positions', 'Daily PnL'],
  },
  dxtrade: {
    id: 'dxtrade',
    label: 'DXtrade',
    logoDomain: 'dx.trade',
    credentials: [
      credential('account_id', 'Account ID', 'DXtrade account id', 'Account identifier shown inside DXtrade.'),
      credential('account_password', 'Password', 'DXtrade password', 'Password for this DXtrade account.', { type: 'password' }),
      credential('server_name', 'Server Name', 'Broker server / realm', 'Server or realm assigned by broker/prop.'),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Realized PnL', 'Unrealized PnL'],
  },
  matchtrader: {
    id: 'matchtrader',
    label: 'Match-Trader',
    logoDomain: 'match-trader.com',
    credentials: [
      credential('account_id', 'Account ID', 'Match-Trader account id', 'Account id for your Match-Trader workspace.'),
      credential('account_password', 'Password', 'Match-Trader password', 'Password for this Match-Trader account.', { type: 'password' }),
      credential('server_name', 'Server Name', 'Server / broker endpoint', 'Server or endpoint provided by broker.'),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Margin Used', 'Daily PnL'],
  },
  tradelocker: {
    id: 'tradelocker',
    label: 'TradeLocker',
    logoDomain: 'tradelocker.com',
    credentials: [
      credential('account_id', 'Account ID', 'TradeLocker account id', 'Account id for your TradeLocker workspace.'),
      credential('account_password', 'Password', 'TradeLocker password', 'Password for this TradeLocker account.', { type: 'password' }),
      credential('server_name', 'Server Name', 'Server / realm', 'Server or realm assigned by broker/prop.'),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Margin Used', 'Daily PnL'],
  },
  thinktrader: {
    id: 'thinktrader',
    label: 'ThinkTrader',
    logoDomain: 'thinktrader.com',
    credentials: [
      credential('account_id', 'Account ID', 'ThinkTrader account id', 'ThinkTrader account id assigned by broker.'),
      credential('account_password', 'Password', 'ThinkTrader password', 'Password for this account.', { type: 'password' }),
      credential('server_name', 'Server Name', 'ThinkTrader server', 'Server/cluster assigned by broker.'),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Margin', 'Daily PnL'],
  },
  tradingview: {
    id: 'tradingview',
    label: 'TradingView Bridge',
    logoDomain: 'tradingview.com',
    logoUrl: 'https://cdn.simpleicons.org/tradingview',
    credentials: [
      credential('workspace_id', 'Workspace/User', 'TradingView username', 'TradingView workspace/user identifier.'),
      credential('session_token', 'Session / Bridge Token', 'Connector token', 'Token issued by your connector/bridge provider.', { type: 'password' }),
      credential('server_name', 'Bridge Endpoint', 'Bridge endpoint URL', 'Bridge endpoint where orders/signals are routed.'),
    ],
    metrics: ['Signal Feed', 'Execution Status', 'Latency', 'Open Positions', 'PnL'],
  },
  oanda_api: {
    id: 'oanda_api',
    label: 'OANDA API',
    logoDomain: 'oanda.com',
    logoUrl: 'https://cdn.simpleicons.org/oanda',
    credentials: [
      credential('oanda_account_id', 'OANDA Account ID', '101-XXX-XXXXXXXX-XXX', 'Your OANDA account identifier.'),
      credential('oanda_api_key', 'OANDA API Key', 'Paste API key', 'Generate API key from OANDA dashboard.', { type: 'password' }),
      credential(
        'oanda_environment',
        'Environment',
        '',
        'Practice for demo, Live for real account.',
        {
          type: 'select',
          options: [
            { label: 'Practice', value: 'practice' },
            { label: 'Live', value: 'live' },
          ],
        },
      ),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Margin', 'Daily PnL'],
  },
  ig_api: {
    id: 'ig_api',
    label: 'IG API',
    logoDomain: 'ig.com',
    logoUrl: 'https://cdn.simpleicons.org/ig',
    credentials: [
      credential('ig_username', 'Username', 'IG username', 'Username for IG account.'),
      credential('ig_password', 'Password', 'IG password', 'Password for IG account.', { type: 'password' }),
      credential('ig_api_key', 'API Key', 'IG API key', 'API key from IG developer portal.', { type: 'password' }),
      credential('ig_account_id', 'Account ID', 'IG account id', 'IG account identifier.', { required: false }),
      credential(
        'ig_environment',
        'Environment',
        '',
        'Demo for testing, Live for production.',
        {
          type: 'select',
          options: [
            { label: 'Demo', value: 'demo' },
            { label: 'Live', value: 'live' },
          ],
          required: false,
        },
      ),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Margin', 'Daily PnL'],
  },
  alpaca_api: {
    id: 'alpaca_api',
    label: 'Alpaca API',
    logoDomain: 'alpaca.markets',
    logoUrl: 'https://cdn.simpleicons.org/alpinedata',
    credentials: [
      credential('alpaca_api_key', 'API Key', 'Alpaca API key', 'API key from Alpaca dashboard.', { type: 'password' }),
      credential('alpaca_secret_key', 'Secret Key', 'Alpaca secret key', 'Secret key from Alpaca dashboard.', { type: 'password' }),
      credential(
        'alpaca_paper',
        'Environment',
        '',
        'Paper for demo, Live for production.',
        {
          type: 'select',
          options: [
            { label: 'Paper', value: 'true' },
            { label: 'Live', value: 'false' },
          ],
        },
      ),
    ],
    metrics: ['Balance', 'Equity', 'Open Positions', 'Buying Power', 'Daily PnL'],
  },
  ib_api: {
    id: 'ib_api',
    label: 'Interactive Brokers API',
    logoDomain: 'interactivebrokers.com',
    logoUrl: 'https://cdn.simpleicons.org/interactivebrokers',
    credentials: [
      credential('ib_account_id', 'Account ID', 'IB account id', 'Interactive Brokers account id.'),
      credential('ib_host', 'Gateway Host', '127.0.0.1', 'Host where IB Gateway/TWS API is available.', { required: false }),
      credential('ib_port', 'Gateway Port', '7497', '7497 paper, 7496 live.', { type: 'number', required: false }),
      credential('ib_client_id', 'Client ID', '1', 'Client id used for TWS/Gateway API.', { type: 'number', required: false }),
    ],
    metrics: ['Net Liquidation', 'Equity', 'Open Positions', 'Margin', 'Daily PnL'],
  },
}

const platformsFor = (...platformIds: string[]) =>
  platformIds
    .map((id) => PLATFORM_DIRECTORY[id])
    .filter((platform): platform is BrokerPlatform => Boolean(platform))

export const BROKER_DIRECTORY: BrokerDirectoryEntry[] = [
  { id: 'ic_markets', name: 'IC Markets', kind: 'broker', logoDomain: 'icmarkets.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'pepperstone', name: 'Pepperstone', kind: 'broker', logoDomain: 'pepperstone.com', platforms: platformsFor('mt4', 'mt5', 'ctrader', 'tradingview') },
  { id: 'roboforex', name: 'RoboForex', kind: 'broker', logoDomain: 'roboforex.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'xm', name: 'XM', kind: 'broker', logoDomain: 'xm.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'exness', name: 'Exness', kind: 'broker', logoDomain: 'exness.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'vantage', name: 'Vantage', kind: 'broker', logoDomain: 'vantagemarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'tickmill', name: 'Tickmill', kind: 'broker', logoDomain: 'tickmill.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'fp_markets', name: 'FP Markets', kind: 'broker', logoDomain: 'fpmarkets.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'eightcap', name: 'Eightcap', kind: 'broker', logoDomain: 'eightcap.com', platforms: platformsFor('mt4', 'mt5', 'tradingview') },
  { id: 'blackbull', name: 'BlackBull Markets', kind: 'broker', logoDomain: 'blackbull.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'thinkmarkets', name: 'ThinkMarkets', kind: 'broker', logoDomain: 'thinkmarkets.com', platforms: platformsFor('mt4', 'mt5', 'thinktrader') },
  { id: 'admirals', name: 'Admirals', kind: 'broker', logoDomain: 'admiralmarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'oanda', name: 'OANDA', kind: 'broker', logoDomain: 'oanda.com', logoUrl: 'https://cdn.simpleicons.org/oanda', platforms: platformsFor('oanda_api', 'mt5') },
  { id: 'ig', name: 'IG', kind: 'broker', logoDomain: 'ig.com', logoUrl: 'https://cdn.simpleicons.org/ig', platforms: platformsFor('ig_api', 'mt4') },
  { id: 'interactive_brokers', name: 'Interactive Brokers', kind: 'broker', logoDomain: 'interactivebrokers.com', logoUrl: 'https://cdn.simpleicons.org/interactivebrokers', platforms: platformsFor('ib_api') },
  { id: 'alpaca', name: 'Alpaca', kind: 'broker', logoDomain: 'alpaca.markets', platforms: platformsFor('alpaca_api') },
  { id: 'xtb', name: 'XTB', kind: 'broker', logoDomain: 'xtb.com', platforms: platformsFor('mt5') },
  { id: 'forex_com', name: 'Forex.com', kind: 'broker', logoDomain: 'forex.com', platforms: platformsFor('mt5', 'tradingview') },
  { id: 'cmc_markets', name: 'CMC Markets', kind: 'broker', logoDomain: 'cmcmarkets.com', platforms: platformsFor('tradingview') },
  { id: 'swissquote', name: 'Swissquote', kind: 'broker', logoDomain: 'swissquote.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'trade_station', name: 'TradeStation', kind: 'broker', logoDomain: 'tradestation.com', platforms: platformsFor('tradingview') },
  { id: 'darwinex', name: 'Darwinex', kind: 'broker', logoDomain: 'darwinex.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'city_index', name: 'City Index', kind: 'broker', logoDomain: 'cityindex.com', platforms: platformsFor('mt4', 'tradingview') },
  { id: 'saxo', name: 'Saxo', kind: 'broker', logoDomain: 'home.saxo', platforms: platformsFor('tradingview') },
  { id: 'plus500', name: 'Plus500', kind: 'broker', logoDomain: 'plus500.com', platforms: platformsFor('tradingview') },
  { id: 'avatrade', name: 'AvaTrade', kind: 'broker', logoDomain: 'avatrade.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'fxtm', name: 'FXTM', kind: 'broker', logoDomain: 'fxtm.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'hf_markets', name: 'HF Markets', kind: 'broker', logoDomain: 'hfm.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'tradersway', name: 'TradersWay', kind: 'broker', logoDomain: 'tradersway.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'lmax', name: 'LMAX', kind: 'broker', logoDomain: 'lmax.com', platforms: platformsFor('mt4', 'tradingview') },
  { id: 'activtrades', name: 'ActivTrades', kind: 'broker', logoDomain: 'activtrades.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'forex4you', name: 'Forex4you', kind: 'broker', logoDomain: 'forex4you.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'topstepx', name: 'TopstepX', kind: 'broker', logoDomain: 'topstep.com', platforms: platformsFor('tradingview') },
  { id: 'tradeovate', name: 'Tradeovate', kind: 'broker', logoDomain: 'tradeovate.com', platforms: platformsFor('tradingview') },
  { id: 'ninjatrader', name: 'NinjaTrader Brokerage', kind: 'broker', logoDomain: 'ninjatrader.com', platforms: platformsFor('tradingview') },
  { id: 'tradier', name: 'Tradier', kind: 'broker', logoDomain: 'tradier.com', platforms: platformsFor('tradingview') },
  { id: 'capital_com', name: 'Capital.com', kind: 'broker', logoDomain: 'capital.com', platforms: platformsFor('tradingview') },
  { id: 'easymarkets', name: 'easyMarkets', kind: 'broker', logoDomain: 'easymarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'infinox', name: 'INFINOX', kind: 'broker', logoDomain: 'infinox.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'fusion_markets', name: 'Fusion Markets', kind: 'broker', logoDomain: 'fusionmarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'aetoscapital', name: 'AETOS', kind: 'broker', logoDomain: 'aetoscg.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'blueberry_markets', name: 'Blueberry Markets', kind: 'broker', logoDomain: 'blueberrymarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'orbex', name: 'ORBEX', kind: 'broker', logoDomain: 'orbex.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'hantec', name: 'Hantec Markets', kind: 'broker', logoDomain: 'hmarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'axi', name: 'Axi', kind: 'broker', logoDomain: 'axi.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'fxpro', name: 'FxPro', kind: 'broker', logoDomain: 'fxpro.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'acap', name: 'AUS Capital', kind: 'broker', logoDomain: 'ausglobal.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'gkfx', name: 'GKFX', kind: 'broker', logoDomain: 'gkfx.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'moneta_markets', name: 'Moneta Markets', kind: 'broker', logoDomain: 'monetamarkets.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'funderpro', name: 'FunderPro', kind: 'prop', logoDomain: 'funderpro.com', platforms: platformsFor('mt5', 'matchtrader', 'tradelocker') },
  { id: 'ftmo', name: 'FTMO', kind: 'prop', logoDomain: 'ftmo.com', platforms: platformsFor('mt4', 'mt5', 'dxtrade') },
  { id: 'fundednext', name: 'FundedNext', kind: 'prop', logoDomain: 'fundednext.com', platforms: platformsFor('mt4', 'mt5', 'ctrader') },
  { id: 'the5ers', name: 'The5ers', kind: 'prop', logoDomain: 'the5ers.com', platforms: platformsFor('mt5') },
  { id: 'my_funded_fx', name: 'MyFundedFX', kind: 'prop', logoDomain: 'myfundedfx.com', platforms: platformsFor('mt5', 'matchtrader') },
  { id: 'funded_trading_plus', name: 'Funded Trading Plus', kind: 'prop', logoDomain: 'fundedtradingplus.com', platforms: platformsFor('mt4', 'mt5', 'tradelocker') },
  { id: 'e8_markets', name: 'E8 Markets', kind: 'prop', logoDomain: 'e8markets.com', platforms: platformsFor('mt5', 'matchtrader') },
  { id: 'alpha_capital_group', name: 'Alpha Capital Group', kind: 'prop', logoDomain: 'alphacapitalgroup.uk', platforms: platformsFor('mt5') },
  { id: 'true_forex_funds', name: 'True Forex Funds', kind: 'prop', logoDomain: 'trueforexfunds.com', platforms: platformsFor('mt4', 'mt5') },
  { id: 'funded_peaks', name: 'Funded Peaks', kind: 'prop', logoDomain: 'fundedpeaks.com', platforms: platformsFor('mt5') },
  { id: 'instant_funding', name: 'Instant Funding', kind: 'prop', logoDomain: 'instantfunding.io', platforms: platformsFor('mt5', 'tradelocker') },
  { id: 'apex_trader_funding', name: 'Apex Trader Funding', kind: 'prop', logoDomain: 'apextraderfunding.com', platforms: platformsFor('tradingview') },
  { id: 'topone_trader', name: 'Top One Trader', kind: 'prop', logoDomain: 'toponetrader.com', platforms: platformsFor('mt5', 'tradelocker') },
  { id: 'funded_engineer', name: 'Funded Engineer', kind: 'prop', logoDomain: 'fundedengineer.com', platforms: platformsFor('mt5') },
  { id: 'brightfunded', name: 'BrightFunded', kind: 'prop', logoDomain: 'brightfunded.com', platforms: platformsFor('mt5', 'dxtrade') },
  { id: 'blue_guardian', name: 'Blue Guardian', kind: 'prop', logoDomain: 'blueguardian.com', platforms: platformsFor('mt5', 'tradelocker') },
  { id: 'funding_pips', name: 'Funding Pips', kind: 'prop', logoDomain: 'fundingpips.com', platforms: platformsFor('mt5', 'matchtrader') },
  { id: 'lux_trading_firm', name: 'Lux Trading Firm', kind: 'prop', logoDomain: 'luxtradingfirm.com', platforms: platformsFor('mt5') },
  { id: 'the_trading_pit', name: 'The Trading Pit', kind: 'prop', logoDomain: 'thetradingpit.com', platforms: platformsFor('ctrader', 'tradingview') },
  { id: 'surge_trader', name: 'SurgeTrader', kind: 'prop', logoDomain: 'surgetrader.com', platforms: platformsFor('mt4', 'mt5') },
]

export const getClearbitLogoUrl = (domain: string) => `https://logo.clearbit.com/${domain}`

export const getBrokerTypeByPlatform = (platformId: string): string => {
  if (platformId === 'oanda_api') return 'oanda'
  if (platformId === 'ig_api') return 'ig'
  if (platformId === 'alpaca_api') return 'alpaca'
  if (platformId === 'ib_api') return 'interactive_brokers'
  return 'metaapi'
}

export const inferBrokerFromAccountName = (name: string): BrokerDirectoryEntry | null => {
  const value = name.toLowerCase()
  for (const broker of BROKER_DIRECTORY) {
    if (value.includes(broker.name.toLowerCase()) || value.includes(broker.id.replace(/_/g, ' '))) {
      return broker
    }
  }
  return null
}

export const inferPlatformFromAccountName = (
  name: string,
  broker: BrokerDirectoryEntry | null,
): string | null => {
  if (!broker) return null
  const value = name.toLowerCase()
  for (const platform of broker.platforms) {
    if (value.includes(platform.label.toLowerCase()) || value.includes(platform.id.toLowerCase())) {
      return platform.id
    }
  }
  return null
}
