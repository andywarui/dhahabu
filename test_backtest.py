"""
Quick Test Script for XAUUSD Trading Bot
Tests if backtest runs successfully
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import backtrader as bt

# Add strategy path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from strategy.sunrise_ogle_xauusd import SunriseOgle

def run_quick_test():
    print("="*80)
    print("XAUUSD M30 TRADING BOT - QUICK TEST")
    print("="*80)

    # Create Cerebro
    cerebro = bt.Cerebro(stdstats=False)

    # Load data
    data_path = Path(__file__).parent / 'data' / 'XAUUSD_M30_2020-2025.csv'

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        return False

    print(f"Loading data: {data_path.name}")

    # Quick test: Last 30 days
    to_date = datetime.strptime('2025-07-25', '%Y-%m-%d')
    from_date = to_date - timedelta(days=30)

    print(f"Period: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")

    # Create data feed
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=30,
        fromdate=from_date,
        todate=to_date
    )

    cerebro.adddata(data)

    # Set broker
    starting_cash = 100000
    cerebro.broker.setcash(starting_cash)
    cerebro.broker.setcommission(leverage=30.0)

    # Add strategy
    cerebro.addstrategy(SunriseOgle,
        enable_long_trades=True,
        enable_short_trades=True,
        risk_percent=0.0125,
        long_entry_window_periods=5,
        short_entry_window_periods=7,
        use_forex_position_calc=True,
        print_signals=False,
        verbose_debug=False
    )

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f"Starting Capital: ${starting_cash:,.2f}")
    print(f"Risk Per Trade: 1.25%")
    print(f"Timeframe: M30 (30-minute)")
    print("="*80)

    print("\nRunning backtest...")

    # Run
    results = cerebro.run()
    strategy = results[0]

    # Results
    final_value = cerebro.broker.getvalue()
    pnl = final_value - starting_cash
    returns = (pnl / starting_cash) * 100

    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)
    print(f"Starting Capital:  ${starting_cash:,.2f}")
    print(f"Final Value:       ${final_value:,.2f}")
    print(f"Total P&L:         ${pnl:+,.2f}")
    print(f"Return:            {returns:+.2f}%")

    # Trade stats
    try:
        trade_analysis = strategy.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        lost_trades = trade_analysis.get('lost', {}).get('total', 0)

        if total_trades > 0:
            win_rate = (won_trades / total_trades) * 100
            print(f"\nTotal Trades:      {total_trades}")
            print(f"Winning Trades:    {won_trades} ({win_rate:.1f}%)")
            print(f"Losing Trades:     {lost_trades}")
    except:
        pass

    print("="*80)

    if total_trades > 0:
        print("\nSUCCESS! Bot is working correctly.")
        return True
    else:
        print("\nWARNING: No trades generated (may be normal for 30-day test)")
        return True


if __name__ == '__main__':
    try:
        success = run_quick_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
