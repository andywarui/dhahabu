@echo off
REM ════════════════════════════════════════════════════════════════════════════
REM   XAUUSD Trading Bot - Quick Start Menu
REM ════════════════════════════════════════════════════════════════════════════

echo.
echo ╔═══════════════════════════════════════════════════════════════════════════╗
echo ║              XAUUSD M1 TRADING BOT - MetaTrader 5                         ║
echo ║              Gold Trading System                                          ║
echo ╚═══════════════════════════════════════════════════════════════════════════╝
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

:MENU
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo                            MAIN MENU
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo   [1] Test MT5 Connection
echo   [2] Run Backtest (Full)
echo   [3] Run Quick Test (30 days)
echo   [4] Start MT5 Live Trading (⚠️  REAL TRADES)
echo   [5] Long-Only Backtest
echo   [6] Short-Only Backtest
echo   [7] Exit
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto TEST_MT5
if "%choice%"=="2" goto BACKTEST
if "%choice%"=="3" goto QUICK_TEST
if "%choice%"=="4" goto MT5_LIVE
if "%choice%"=="5" goto LONG_ONLY
if "%choice%"=="6" goto SHORT_ONLY
if "%choice%"=="7" goto EXIT

echo Invalid choice. Please try again.
goto MENU

:TEST_MT5
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Testing MT5 Connection...
echo ════════════════════════════════════════════════════════════════════════════
python mt5_trader.py
pause
goto MENU

:BACKTEST
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Running Full Backtest...
echo ════════════════════════════════════════════════════════════════════════════
python xauusd_trading_bot.py --mode backtest
pause
goto MENU

:QUICK_TEST
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Running Quick Test (30 days)...
echo ════════════════════════════════════════════════════════════════════════════
python xauusd_trading_bot.py --mode quick
pause
goto MENU

:MT5_LIVE
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   ⚠️  WARNING: MT5 LIVE TRADING MODE ⚠️
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo   This will execute REAL trades on your MT5 account!
echo.
echo   Make sure you have:
echo   1. Configured mt5_config.json with correct credentials
echo   2. Tested on a DEMO account first
echo   3. MT5 terminal is running and logged in
echo.
set /p confirm="Are you sure you want to continue? (yes/no): "
if /i "%confirm%"=="yes" (
    echo.
    echo Starting live trading... Press Ctrl+C to stop
    python xauusd_trading_bot.py --mode mt5
) else (
    echo Live trading cancelled.
)
pause
goto MENU

:LONG_ONLY
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Running LONG-Only Backtest...
echo ════════════════════════════════════════════════════════════════════════════
python xauusd_trading_bot.py --mode backtest --long-only
pause
goto MENU

:SHORT_ONLY
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Running SHORT-Only Backtest...
echo ════════════════════════════════════════════════════════════════════════════
python xauusd_trading_bot.py --mode backtest --short-only
pause
goto MENU

:EXIT
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   Thank you for using XAUUSD Trading Bot!
echo ════════════════════════════════════════════════════════════════════════════
echo.
timeout /t 2 >nul
exit
