
import sys
sys.path.insert(0, r"D:\goldbot\backtrader-pullback-window-xauusd")

# Override CONFIG before importing
import xauusd_trading_bot
xauusd_trading_bot.CONFIG['data_file'] = 'XAU_1m_2020-2025.csv'
xauusd_trading_bot.CONFIG['from_date'] = '2020-01-01'
xauusd_trading_bot.CONFIG['to_date'] = '2025-12-31'
xauusd_trading_bot.CONFIG['timeframe'] = '1M'

# Run backtest
bot = xauusd_trading_bot.XAUUSDTradingBot()
bot.setup_cerebro()
bot.run()
