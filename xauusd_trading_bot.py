"""
+==============================================================================+
|                    XAUUSD M30 TRADING BOT - LIVE RUNNER                      |
|           Gold (XAU/USD) Algorithmic Trading System                          |
|                   Based on Sunrise OGLE Strategy                             |
+==============================================================================+

FEATURES:
---------
[OK] Volatility Expansion Channel Entry System
[OK] 4-Phase State Machine (SCANNING → ARMED → WINDOW_OPEN → ENTRY)
[OK] Dynamic ATR-Based Risk Management
[OK] Pullback Confirmation System
[OK] EMA Multi-Crossover Detection
[OK] Automated Position Sizing (1.25% Risk Per Trade)
[OK] Advanced Time Filtering
[OK] Real-time Performance Tracking
[OK] Daily Bias Analysis with Multi-Timeframe Confirmation
[OK] Advanced Multi-Indicator Scalping System

PERFORMANCE (Backtested 2020-2025):
-----------------------------------
[STATS] Total Return: +44.75% ($44,747)
[UP] Sharpe Ratio: 0.892
[TARGET] Profit Factor: 1.64
[OK] Win Rate: 55.43%
📉 Max Drawdown: 5.81%
[MONEY] 175 Trades (3/month avg)

USAGE:
------
1. Backtest Mode:       python xauusd_trading_bot.py --mode backtest
2. MT5 Live Trading:    python xauusd_trading_bot.py --mode mt5
3. Quick Test (30 days):python xauusd_trading_bot.py --mode quick
4. Custom Period:       python xauusd_trading_bot.py --from 2024-01-01 --to 2024-12-31
5. Test MT5 Connection: python mt5_trader.py

CONFIGURATION:
--------------
Edit the CONFIG section below to customize:
- Trading direction (LONG/SHORT/BOTH)
- Risk per trade (default 1.25%)
- ATR filters and entry parameters
- Time session filters
- Visualization options
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import backtrader as bt
import time
import numpy as np

# Add strategy path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from strategy.sunrise_ogle_xauusd import SunriseOgle

# Try to import MT5 trader (optional for backtest mode)
try:
    from mt5_trader import MT5Trader
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARNING]  MT5 module not available. Install MetaTrader5: pip install MetaTrader5")

# ===============================================================================
# 🔧 BOT CONFIGURATION - CUSTOMIZE YOUR TRADING BOT HERE
# ===============================================================================

CONFIG = {
    # === TRADING DIRECTION ===
    'enable_long': True,                # Enable LONG (BUY) trades
    'enable_short': True,               # Enable SHORT (SELL) trades

    # === CAPITAL & RISK MANAGEMENT ===
    'starting_cash': 100000,            # Starting capital in USD
    'risk_percent': 0.0125,             # Risk 1.25% per trade (aligned with MT5 config)
    'leverage': 30.0,                   # Broker leverage (30:1 for Gold)

    # === ICT CONFIDENCE-BASED POSITION SIZING ===
    'use_confidence_sizing': True,      # ✅ ENABLED - Scale position size by ICT confidence
    'confidence_min_multiplier': 0.5,   # Min size at low confidence (50%)
    'confidence_max_multiplier': 1.3,   # Max size at high confidence (130%)

    # === DATA & TIMEFRAME ===
    'data_file': 'XAUUSD_M5_2020-2025.csv',   # 5M data 2020-2025 for backtest
    'timeframe': 'M5',                        # 5-minute timeframe for scalping

    # === BACKTEST PERIOD ===
    'from_date': '2020-01-01',          # Start date (YYYY-MM-DD)
    'to_date': '2025-09-30',            # End date (YYYY-MM-DD)

    # === PULLBACK ENTRY SYSTEM ===
    'long_pullback_enabled': True,      # Enable pullback entry for LONG
    'short_pullback_enabled': True,     # Enable pullback entry for SHORT
    'long_pullback_candles': 3,         # Red candles before LONG (1-3)
    'short_pullback_candles': 2,        # Green candles before SHORT (1-3)
    'long_window_periods': 5,           # Breakout window LONG (FIXED: was 1, now 5 for better balance)
    'short_window_periods': 7,          # Breakout window SHORT (bars)

    # === VOLATILITY EXPANSION CHANNEL ===
    'use_time_offset': False,           # Enable window time delay
    'window_offset_multiplier': 1.0,    # Window delay (0.5-2.0)
    'window_price_offset': 0.001,       # Channel expansion

    # === ATR VOLATILITY FILTERS ===
    'long_atr_filter': True,            # Enable ATR filter for LONG
    'long_atr_min': 0.0,                # Minimum ATR for LONG
    'long_atr_max': 2.0,                # Maximum ATR for LONG

    'short_atr_filter': True,           # Enable ATR filter for SHORT
    'short_atr_min': 0.0004,            # Minimum ATR for SHORT
    'short_atr_max': 0.00075,           # Maximum ATR for SHORT

    # === ENTRY FILTERS ===
    'long_use_price_filter': True,      # Price above filter EMA (LONG)
    'long_use_angle_filter': False,     # EMA angle filter (LONG)
    'long_min_angle': 35.0,             # Minimum angle (LONG)
    'long_max_angle': 95.0,             # Maximum angle (LONG)

    'short_use_price_filter': True,     # Price below filter EMA (SHORT)
    'short_use_angle_filter': True,     # EMA angle filter (SHORT)
    'short_min_angle': -90.0,           # Minimum angle (SHORT)
    'short_max_angle': -20.0,           # Maximum angle (SHORT)

    # === TIME SESSION FILTER ===
    'use_time_filter': False,           # ❌ DISABLED - Filter was too aggressive (removed 55% profitable trades)
    'session_start_hour': 7,            # Session start (UTC) - London open
    'session_start_minute': 0,
    'session_end_hour': 20,             # Session end (UTC) - Before late NY close (was 17, now 20)
    'session_end_minute': 0,

    # === TECHNICAL INDICATORS ===
    'ema_fast': 14,                     # Fast EMA period
    'ema_medium': 14,                   # Medium EMA period
    'ema_slow': 24,                     # Slow EMA period
    'ema_confirm': 1,                   # Confirmation EMA
    'ema_filter': 100,                  # Price filter EMA
    'atr_period': 10,                   # ATR period

    # === RISK MULTIPLIERS ===
    'long_sl_multiplier': 4.5,          # Stop loss ATR multiplier (LONG)
    'long_tp_multiplier': 6.5,          # Take profit ATR multiplier (LONG)
    'short_sl_multiplier': 2.5,         # Stop loss ATR multiplier (SHORT)
    'short_tp_multiplier': 6.5,         # Take profit ATR multiplier (SHORT)

    # === VISUALIZATION ===
    'enable_plot': True,                # Show performance chart
    'verbose_debug': False,             # Print detailed debug info
    'plot_sltp': True,                  # Show SL/TP lines on chart

    # === MT5 LIVE TRADING ===
    'mt5_config': 'mt5_config.json',    # MT5 configuration file
    'mt5_check_interval': 30,           # Seconds between signal checks (1 min for M30 is fine)
    'mt5_warmup_bars': 500,             # Historical bars to load for indicators
}

# ===============================================================================
# [BOT] TRADING BOT CORE - DO NOT MODIFY UNLESS YOU KNOW WHAT YOU'RE DOING
# ===============================================================================

class ICTMarketAnalyzer:
    """
    ICT (Inner Circle Trader) Market Analysis Module
    
    Core Principles:
    - Price is engineered, not random
    - Liquidity is taken before real direction is revealed
    - Strong moves are preceded by manipulation and inefficiency
    - Session context matters more than individual candles
    
    Order of Reasoning: Liquidity → Intent → Entry → Target
    """
    
    def __init__(self):
        # Session tracking
        self.asian_high = None
        self.asian_low = None
        self.asian_range_set = False
        
        # London session
        self.london_displacement = None  # 'BULLISH' or 'BEARISH' or None
        self.london_displacement_high = None
        self.london_displacement_low = None
        self.liquidity_swept = None  # 'ASIAN_HIGH' or 'ASIAN_LOW' or None
        
        # Dealing range (after displacement)
        self.dealing_range_high = None
        self.dealing_range_low = None
        
        # Inefficiency zones (Fair Value Gaps)
        self.fvg_zones = []  # List of {'type': 'bullish'/'bearish', 'high': x, 'low': x, 'filled': False}
        
        # Current market state
        self.market_phase = "ACCUMULATION"  # ACCUMULATION, MANIPULATION, DISTRIBUTION, EXPANSION
        self.intent_direction = None  # 'BULLISH' or 'BEARISH' or None
        self.execution_allowed = False
        
        # Session times (UTC)
        self.ASIAN_START = 0   # 00:00 UTC
        self.ASIAN_END = 8     # 08:00 UTC
        self.LONDON_START = 8  # 08:00 UTC
        self.LONDON_END = 13   # 13:00 UTC (before NY overlap)
        self.NY_START = 13     # 13:00 UTC
        self.NY_END = 21       # 21:00 UTC
        
        # Daily reset flag
        self.last_reset_date = None

        # Market context confidence (0.0 - 1.0)
        # Acts as a WEIGHT, not a GATE
        self.market_context_confidence = 0.5  # Start neutral
        self.asian_session_progress = 0.0  # 0.0 to 1.0 (% of session complete)

        # Confidence decay tracking
        self.last_confidence_update_bar = 0
        self.confidence_decay_rate = 0.98  # 2% decay per bar without new info

        # Strategy-type confidence floors
        self.confidence_floors = {
            'MEAN_REVERSION': 0.2,    # Allow at low confidence
            'TREND_CONTINUATION': 0.5, # Medium confidence required
            'BREAKOUT': 0.6,           # Higher confidence for breakouts
            'SCALP': 0.2               # Flexible for quick trades
        }

        # Confidence logging for empirical analysis
        # DO NOT OPTIMIZE based on this data until 30-60 trading days
        self.confidence_log = []  # List of dicts with trade outcomes

    def reset_daily(self):
        """Reset all daily tracking variables"""
        self.asian_high = None
        self.asian_low = None
        self.asian_range_set = False
        self.london_displacement = None
        self.london_displacement_high = None
        self.london_displacement_low = None
        self.liquidity_swept = None
        self.dealing_range_high = None
        self.dealing_range_low = None
        self.fvg_zones = []
        self.market_phase = "ACCUMULATION"
        self.intent_direction = None
        self.execution_allowed = True  # ALWAYS TRUE - ICT only weights, never blocks
        self.market_context_confidence = 0.5  # Reset to neutral
        self.asian_session_progress = 0.0
        self.last_confidence_update_bar = 0

    def apply_confidence_decay(self, current_bar_index):
        """
        Apply time-based confidence decay to prevent stale bias lingering
        Confidence decays 2% per bar without new information
        """
        bars_since_update = current_bar_index - self.last_confidence_update_bar

        if bars_since_update > 0:
            # Apply exponential decay
            decay_factor = self.confidence_decay_rate ** bars_since_update
            old_confidence = self.market_context_confidence
            self.market_context_confidence *= decay_factor

            # Floor at minimum confidence (0.2)
            self.market_context_confidence = max(self.market_context_confidence, 0.2)

            # Only log if significant decay occurred
            if old_confidence - self.market_context_confidence > 0.05:
                return f"Confidence decayed: {old_confidence:.2f} → {self.market_context_confidence:.2f}"

        return None

    def update_confidence(self, new_confidence, current_bar_index):
        """
        Update confidence and track when it was last updated
        Call this whenever ICT context provides new information
        """
        self.market_context_confidence = max(min(new_confidence, 1.0), 0.2)
        self.last_confidence_update_bar = current_bar_index

    def log_trade_entry(self, signal_type, entry_price, stop_loss, take_profit,
                        confidence, strategy_type, priority):
        """
        Log trade entry with ICT confidence context
        DO NOT OPTIMIZE based on this data until 30-60 trading days
        """
        from datetime import datetime

        entry_log = {
            'timestamp': datetime.now().isoformat(),
            'signal_type': signal_type,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence_at_entry': confidence,
            'strategy_type': strategy_type,
            'priority': priority,
            'intent_direction': self.intent_direction,
            'market_phase': self.market_phase,
            'session': None,  # Will be filled by caller
            'exit_price': None,  # Filled on exit
            'r_multiple': None,  # Filled on exit
            'outcome': None,    # 'WIN' or 'LOSS' - filled on exit
            'hold_time_bars': None  # Filled on exit
        }

        self.confidence_log.append(entry_log)
        return len(self.confidence_log) - 1  # Return index for later update

    def log_trade_exit(self, trade_index, exit_price, outcome):
        """
        Update trade log with exit information
        """
        if trade_index < len(self.confidence_log):
            trade = self.confidence_log[trade_index]
            trade['exit_price'] = exit_price
            trade['outcome'] = outcome

            # Calculate R-multiple
            risk = abs(trade['entry_price'] - trade['stop_loss'])
            if risk > 0:
                if outcome == 'WIN':
                    reward = abs(exit_price - trade['entry_price'])
                    trade['r_multiple'] = reward / risk
                else:
                    loss = abs(trade['entry_price'] - exit_price)
                    trade['r_multiple'] = -loss / risk
            else:
                trade['r_multiple'] = 0.0

    def save_confidence_log(self, filepath='confidence_log.json'):
        """
        Save confidence log to file for analysis
        Call this periodically (e.g., daily) or on bot shutdown
        """
        import json
        from pathlib import Path

        log_dir = Path(filepath).parent
        log_dir.mkdir(exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.confidence_log, f, indent=2)

        return len(self.confidence_log)

    def analyze_confidence_performance(self, min_trades=30):
        """
        Analyze confidence vs outcome correlation
        ONLY USE THIS AFTER 30-60 TRADING DAYS
        """
        if len(self.confidence_log) < min_trades:
            return f"Insufficient data: {len(self.confidence_log)} trades (need {min_trades}+)"

        # Group by confidence bands
        bands = {
            'Very Low (0.2-0.4)': [],
            'Low (0.4-0.5)': [],
            'Medium (0.5-0.7)': [],
            'High (0.7-0.9)': [],
            'Very High (0.9-1.0)': []
        }

        for trade in self.confidence_log:
            if trade['r_multiple'] is None:
                continue  # Skip open trades

            conf = trade['confidence_at_entry']
            r = trade['r_multiple']

            if conf < 0.4:
                bands['Very Low (0.2-0.4)'].append(r)
            elif conf < 0.5:
                bands['Low (0.4-0.5)'].append(r)
            elif conf < 0.7:
                bands['Medium (0.5-0.7)'].append(r)
            elif conf < 0.9:
                bands['High (0.7-0.9)'].append(r)
            else:
                bands['Very High (0.9-1.0)'].append(r)

        # Calculate statistics per band
        results = {}
        for band_name, r_multiples in bands.items():
            if len(r_multiples) > 0:
                avg_r = sum(r_multiples) / len(r_multiples)
                win_rate = len([r for r in r_multiples if r > 0]) / len(r_multiples)
                results[band_name] = {
                    'trades': len(r_multiples),
                    'avg_r': round(avg_r, 2),
                    'win_rate': round(win_rate * 100, 1)
                }

        return results
        
    def get_session(self, utc_hour):
        """Determine current trading session"""
        if self.ASIAN_START <= utc_hour < self.ASIAN_END:
            return "ASIAN"
        elif self.LONDON_START <= utc_hour < self.NY_START:
            return "LONDON"
        elif self.NY_START <= utc_hour < self.NY_END:
            return "NEW_YORK"
        else:
            return "OFF_HOURS"
    
    def update_asian_range(self, high, low, close, session_progress=0.0):
        """
        Track Asian session high and low for liquidity reference
        session_progress: 0.0 to 1.0 indicating % of Asian session completed
        """
        if self.asian_high is None or high > self.asian_high:
            self.asian_high = high
        if self.asian_low is None or low < self.asian_low:
            self.asian_low = low

        self.asian_session_progress = session_progress

        # Progressive confidence building
        if session_progress < 0.3:
            # Early session: provisional range (low confidence)
            self.market_context_confidence = 0.3
            self.asian_range_set = True  # Mark as set even if partial
        elif session_progress < 0.7:
            # Mid session: updating range (medium confidence)
            self.market_context_confidence = 0.6
            self.asian_range_set = True
        else:
            # Late session: locked range (high confidence)
            self.market_context_confidence = 0.8
            self.asian_range_set = True
        
    def detect_liquidity_sweep(self, high, low, close):
        """
        Detect if price has swept Asian session liquidity
        A sweep occurs when price trades beyond the level then reverses
        """
        if not self.asian_range_set:
            return None
            
        # Check for sweep of Asian high (sell-side liquidity)
        if high > self.asian_high and close < self.asian_high:
            return "ASIAN_HIGH_SWEPT"
            
        # Check for sweep of Asian low (buy-side liquidity)
        if low < self.asian_low and close > self.asian_low:
            return "ASIAN_LOW_SWEPT"
            
        # Check for break (not sweep) - price stays beyond
        if close > self.asian_high:
            return "ASIAN_HIGH_BROKEN"
        if close < self.asian_low:
            return "ASIAN_LOW_BROKEN"
            
        return None
    
    def detect_displacement(self, df, lookback=3):
        """
        Detect displacement (strong impulsive move after liquidity sweep)
        Displacement = Large body candle with minimal wicks, breaking structure
        """
        if len(df) < lookback + 1:
            return None
            
        recent = df.tail(lookback + 1)
        
        # Calculate average candle range
        avg_range = (recent['high'] - recent['low']).mean()
        
        # Get latest candle
        current = recent.iloc[-1]
        body = abs(current['close'] - current['open'])
        total_range = current['high'] - current['low']
        
        # Displacement criteria:
        # 1. Body is at least 70% of total range (strong momentum)
        # 2. Range is at least 1.5x average (significant move)
        body_ratio = body / total_range if total_range > 0 else 0
        range_ratio = total_range / avg_range if avg_range > 0 else 0
        
        if body_ratio > 0.7 and range_ratio > 1.5:
            if current['close'] > current['open']:
                return "BULLISH_DISPLACEMENT"
            else:
                return "BEARISH_DISPLACEMENT"
                
        return None
    
    def detect_fvg(self, df):
        """
        Detect Fair Value Gaps (Inefficiency Zones)
        Bullish FVG: Current low > 2-candles-ago high (gap up)
        Bearish FVG: Current high < 2-candles-ago low (gap down)
        """
        if len(df) < 3:
            return None
            
        candle_0 = df.iloc[-1]  # Current
        candle_1 = df.iloc[-2]  # Previous
        candle_2 = df.iloc[-3]  # 2 candles ago
        
        # Bullish FVG: Gap between candle_2 high and candle_0 low
        if candle_0['low'] > candle_2['high']:
            return {
                'type': 'BULLISH_FVG',
                'high': candle_0['low'],
                'low': candle_2['high'],
                'midpoint': (candle_0['low'] + candle_2['high']) / 2,
                'filled': False
            }
            
        # Bearish FVG: Gap between candle_0 high and candle_2 low
        if candle_0['high'] < candle_2['low']:
            return {
                'type': 'BEARISH_FVG',
                'high': candle_2['low'],
                'low': candle_0['high'],
                'midpoint': (candle_2['low'] + candle_0['high']) / 2,
                'filled': False
            }
            
        return None
    
    def check_fvg_fill(self, current_high, current_low):
        """Check if price has filled any FVG zones"""
        for fvg in self.fvg_zones:
            if fvg['filled']:
                continue
                
            # Check if price has entered the FVG zone
            if fvg['type'] == 'BULLISH_FVG':
                if current_low <= fvg['high']:  # Price dipped into bullish FVG
                    fvg['touched'] = True
                    if current_low <= fvg['midpoint']:
                        fvg['filled'] = True
                        
            elif fvg['type'] == 'BEARISH_FVG':
                if current_high >= fvg['low']:  # Price rose into bearish FVG
                    fvg['touched'] = True
                    if current_high >= fvg['midpoint']:
                        fvg['filled'] = True
    
    def identify_liquidity_targets(self, df, direction, lookback=50):
        """
        Identify logical liquidity targets based on direction
        - Equal highs/lows (obvious liquidity pools)
        - Swing points
        - Untested levels
        """
        if len(df) < lookback:
            lookback = len(df)
            
        recent = df.tail(lookback)
        targets = []
        
        if direction == "BULLISH":
            # Look for swing highs above current price
            current_price = recent.iloc[-1]['close']
            for i in range(2, len(recent) - 2):
                if (recent.iloc[i]['high'] > recent.iloc[i-1]['high'] and 
                    recent.iloc[i]['high'] > recent.iloc[i-2]['high'] and
                    recent.iloc[i]['high'] > recent.iloc[i+1]['high'] and
                    recent.iloc[i]['high'] > recent.iloc[i+2]['high'] and
                    recent.iloc[i]['high'] > current_price):
                    targets.append(recent.iloc[i]['high'])
                    
        elif direction == "BEARISH":
            # Look for swing lows below current price
            current_price = recent.iloc[-1]['close']
            for i in range(2, len(recent) - 2):
                if (recent.iloc[i]['low'] < recent.iloc[i-1]['low'] and 
                    recent.iloc[i]['low'] < recent.iloc[i-2]['low'] and
                    recent.iloc[i]['low'] < recent.iloc[i+1]['low'] and
                    recent.iloc[i]['low'] < recent.iloc[i+2]['low'] and
                    recent.iloc[i]['low'] < current_price):
                    targets.append(recent.iloc[i]['low'])
        
        # Sort targets by proximity
        if direction == "BULLISH":
            targets.sort()  # Ascending (closest first)
        else:
            targets.sort(reverse=True)  # Descending (closest first)
            
        return targets[:3]  # Return top 3 targets
    
    def analyze(self, df, utc_hour, current_date):
        """
        Main ICT analysis function - call on each new bar
        Returns analysis dict with bias, intent, and trade permission
        """
        from datetime import timezone
        
        # Daily reset check
        if self.last_reset_date != current_date:
            self.reset_daily()
            self.last_reset_date = current_date
            
        session = self.get_session(utc_hour)
        current = df.iloc[-1]
        
        analysis = {
            'session': session,
            'market_phase': self.market_phase,
            'intent': self.intent_direction,
            'execution_allowed': self.execution_allowed,
            'asian_high': self.asian_high,
            'asian_low': self.asian_low,
            'liquidity_swept': self.liquidity_swept,
            'displacement': None,
            'fvg_zones': self.fvg_zones,
            'targets': [],
            'reasoning': []
        }
        
        # ==================== ASIAN SESSION ====================
        if session == "ASIAN":
            self.market_phase = "ACCUMULATION"

            # Calculate session progress (0-7 UTC = 7 hours)
            session_hours_elapsed = utc_hour - self.ASIAN_START
            session_progress = min(session_hours_elapsed / 7.0, 1.0)

            self.update_asian_range(current['high'], current['low'], current['close'], session_progress)

            analysis['reasoning'].append(f"📦 Asian Session: Building liquidity range ({session_progress*100:.0f}% complete)")
            analysis['reasoning'].append(f"   Range: {self.asian_low:.2f} - {self.asian_high:.2f}")
            analysis['reasoning'].append(f"   Context Confidence: {self.market_context_confidence*100:.0f}%")
            self.execution_allowed = True  # Always allow trading

        # ==================== LONDON SESSION ====================
        elif session == "LONDON":
            # IMPORTANT: Never block trading - only adjust confidence
            if not self.asian_range_set:
                analysis['reasoning'].append("⚠️ No Asian range established yet")
                analysis['reasoning'].append("   Trading allowed with reduced confidence (scalping mode)")
                self.market_context_confidence = 0.3  # Low confidence, not blocked
                self.execution_allowed = True  # ALWAYS TRUE
            else:
                # Asian range known - increase confidence
                self.market_context_confidence = max(self.market_context_confidence, 0.6)
                
            # Check for liquidity sweep
            sweep = self.detect_liquidity_sweep(current['high'], current['low'], current['close'])
            
            if sweep and not self.liquidity_swept:
                self.liquidity_swept = sweep
                self.market_phase = "MANIPULATION"
                
                if "HIGH" in sweep:
                    analysis['reasoning'].append(f"🎯 LIQUIDITY SWEEP: Asian High taken ({self.asian_high:.2f})")
                    analysis['reasoning'].append("   Sell-side liquidity grabbed - watch for bearish displacement")
                else:
                    analysis['reasoning'].append(f"🎯 LIQUIDITY SWEEP: Asian Low taken ({self.asian_low:.2f})")
                    analysis['reasoning'].append("   Buy-side liquidity grabbed - watch for bullish displacement")
            
            # After sweep, look for displacement
            if self.liquidity_swept and not self.intent_direction:
                displacement = self.detect_displacement(df)

                if displacement:
                    analysis['displacement'] = displacement
                    self.market_phase = "DISTRIBUTION"

                    if "BULLISH" in displacement:
                        self.intent_direction = "BULLISH"
                        self.dealing_range_low = df.tail(5)['low'].min()
                        self.dealing_range_high = current['high']
                        self.market_context_confidence = 0.9  # High confidence with clear direction
                        analysis['reasoning'].append("⚡ BULLISH DISPLACEMENT detected!")
                        analysis['reasoning'].append(f"   Dealing Range: {self.dealing_range_low:.2f} - {self.dealing_range_high:.2f}")

                    elif "BEARISH" in displacement:
                        self.intent_direction = "BEARISH"
                        self.dealing_range_high = df.tail(5)['high'].max()
                        self.dealing_range_low = current['low']
                        self.market_context_confidence = 0.9  # High confidence with clear direction
                        analysis['reasoning'].append("⚡ BEARISH DISPLACEMENT detected!")
                        analysis['reasoning'].append(f"   Dealing Range: {self.dealing_range_low:.2f} - {self.dealing_range_high:.2f}")
            elif not self.intent_direction:
                # No displacement yet - set NEUTRAL intent
                self.intent_direction = "NEUTRAL"
                self.market_context_confidence = 0.5  # Medium confidence, allow both directions
                analysis['reasoning'].append("↔️ NEUTRAL Intent: No clear displacement yet")
                analysis['reasoning'].append("   Trading allowed in both directions (scalping mode)")
            
            # Track FVGs after displacement
            if self.intent_direction:
                fvg = self.detect_fvg(df)
                if fvg:
                    self.fvg_zones.append(fvg)
                    analysis['reasoning'].append(f"📊 New {fvg['type']} zone: {fvg['low']:.2f} - {fvg['high']:.2f}")
                    
            # London: Allow trading if indicators give signal
            self.execution_allowed = True
            analysis['reasoning'].append("👀 London Session: Trading enabled")
            
        # ==================== NEW YORK SESSION ====================
        elif session == "NEW_YORK":
            self.market_phase = "EXPANSION"

            if self.intent_direction == "NEUTRAL":
                # NEUTRAL mode: Allow both directions with medium confidence
                analysis['reasoning'].append("↔️ NY Session: NEUTRAL bias - both directions allowed")
                analysis['reasoning'].append("   Using scalping approach with quick exits")
                self.execution_allowed = True
                self.market_context_confidence = 0.5

            elif self.intent_direction in ["BULLISH", "BEARISH"]:
                # Clear directional intent
                # Check for retracement into FVG zones
                self.check_fvg_fill(current['high'], current['low'])

                # Find unfilled FVGs aligned with intent
                valid_entry_zones = []
                for fvg in self.fvg_zones:
                    if not fvg['filled']:
                        if self.intent_direction == "BULLISH" and fvg['type'] == 'BULLISH_FVG':
                            valid_entry_zones.append(fvg)
                        elif self.intent_direction == "BEARISH" and fvg['type'] == 'BEARISH_FVG':
                            valid_entry_zones.append(fvg)

                if valid_entry_zones:
                    analysis['reasoning'].append(f"✅ NY Session: {len(valid_entry_zones)} unfilled FVG entry zones")

                # Get liquidity targets
                targets = self.identify_liquidity_targets(df, self.intent_direction)
                analysis['targets'] = targets

                if targets:
                    analysis['reasoning'].append(f"🎯 Liquidity Targets: {[f'{t:.2f}' for t in targets]}")

                # Always allow execution
                self.execution_allowed = True
                self.market_context_confidence = 0.9  # High confidence with clear direction
                analysis['reasoning'].append(f"🚀 Execution Window OPEN - Direction: {self.intent_direction}")

            else:
                # Fallback: No intent set at all (shouldn't happen with NEUTRAL default)
                self.intent_direction = "NEUTRAL"
                self.execution_allowed = True
                self.market_context_confidence = 0.4
                analysis['reasoning'].append("⚠️ NY Session: Defaulting to NEUTRAL (low confidence)")
                analysis['reasoning'].append("   Trading allowed with reduced sizing")
        
        # ==================== OFF HOURS ====================
        else:
            # Early-session rule: Allow trading before London open
            # Asia → early London often contains valid mean-reversion/scalps
            self.execution_allowed = True  # Never block completely
            self.market_context_confidence = 0.2  # Very low confidence
            analysis['reasoning'].append("🌙 Off-hours: Trading allowed with low confidence")
            analysis['reasoning'].append("   Mean-reversion and scalping opportunities only")
        
        # Update analysis with current state
        analysis['market_phase'] = self.market_phase
        analysis['intent'] = self.intent_direction
        analysis['execution_allowed'] = self.execution_allowed
        analysis['asian_high'] = self.asian_high
        analysis['asian_low'] = self.asian_low
        
        return analysis
    
    def classify_strategy_type(self, signal_type, current_price):
        """
        Classify the type of strategy being employed
        Returns: 'MEAN_REVERSION', 'TREND_CONTINUATION', 'BREAKOUT', or 'SCALP'
        """
        # If we have intent and dealing range, we can classify better
        if self.intent_direction in ["BULLISH", "BEARISH"] and self.dealing_range_high and self.dealing_range_low:
            range_size = self.dealing_range_high - self.dealing_range_low
            midpoint = self.dealing_range_low + (range_size * 0.5)

            # BREAKOUT: Trading in direction of intent near edge of dealing range
            if signal_type == "BUY" and self.intent_direction == "BULLISH":
                if current_price >= self.dealing_range_low + (range_size * 0.7):
                    return 'BREAKOUT'
                elif current_price <= midpoint:
                    return 'MEAN_REVERSION'  # Buying at lower half
                else:
                    return 'TREND_CONTINUATION'

            elif signal_type == "SELL" and self.intent_direction == "BEARISH":
                if current_price <= self.dealing_range_low + (range_size * 0.3):
                    return 'BREAKOUT'
                elif current_price >= midpoint:
                    return 'MEAN_REVERSION'  # Selling at upper half
                else:
                    return 'TREND_CONTINUATION'

            # COUNTER-TREND: Trading against intent (mean reversion)
            else:
                return 'MEAN_REVERSION'

        # Default: SCALP (when no clear structure)
        return 'SCALP'

    def get_ict_trade_filter(self, signal_type, current_price):
        """
        Evaluate trade signals based on ICT principles
        IMPORTANT: Returns context and confidence, NEVER blocks trades
        Returns: (allowed: bool, reason: str, confidence: float, strategy_type: str, priority: str)
        """
        # CRITICAL DESIGN: execution_allowed is now ALWAYS True
        # This function provides CONTEXT, not PERMISSION

        confidence = self.market_context_confidence
        reasons = []

        # Classify strategy type
        strategy_type = self.classify_strategy_type(signal_type, current_price)

        # Evaluate intent alignment
        if self.intent_direction == "NEUTRAL":
            reasons.append("NEUTRAL bias - both directions valid")
            confidence = max(confidence, 0.5)
        elif self.intent_direction == "BULLISH":
            if signal_type == "BUY":
                reasons.append(f"✅ {signal_type} aligns with BULLISH intent")
                confidence = max(confidence, 0.8)
            else:
                reasons.append(f"⚠️ {signal_type} AGAINST BULLISH intent (reduced confidence)")
                confidence = min(confidence, 0.4)
        elif self.intent_direction == "BEARISH":
            if signal_type == "SELL":
                reasons.append(f"✅ {signal_type} aligns with BEARISH intent")
                confidence = max(confidence, 0.8)
            else:
                reasons.append(f"⚠️ {signal_type} AGAINST BEARISH intent (reduced confidence)")
                confidence = min(confidence, 0.4)

        # Evaluate price position (ADVISORY, not blocking)
        if self.dealing_range_high and self.dealing_range_low:
            range_size = self.dealing_range_high - self.dealing_range_low
            midpoint = self.dealing_range_low + (range_size * 0.5)

            if signal_type == "BUY":
                if current_price <= midpoint:
                    reasons.append("✅ Price in optimal BUY zone (lower dealing range)")
                    confidence = min(confidence + 0.1, 1.0)
                else:
                    reasons.append("⚠️ Price above optimal BUY zone (reduced confidence)")
                    confidence = max(confidence - 0.1, 0.3)

            elif signal_type == "SELL":
                if current_price >= midpoint:
                    reasons.append("✅ Price in optimal SELL zone (upper dealing range)")
                    confidence = min(confidence + 0.1, 1.0)
                else:
                    reasons.append("⚠️ Price below optimal SELL zone (reduced confidence)")
                    confidence = max(confidence - 0.1, 0.3)

        # Apply strategy-type confidence floor (does NOT block, only deprioritizes)
        confidence_floor = self.confidence_floors.get(strategy_type, 0.2)
        priority = "NORMAL"

        if confidence < confidence_floor:
            priority = "LOW"
            reasons.append(f"⚠️ Below {strategy_type} floor ({confidence_floor*100:.0f}%) - LOW PRIORITY")

        # ALWAYS allow trade - just provide confidence rating and priority
        reason_text = " | ".join(reasons) if reasons else "No specific ICT context"
        return True, f"[{strategy_type}] [Confidence: {confidence*100:.0f}%] {reason_text}", confidence, strategy_type, priority
    
    def print_status(self):
        """Print current ICT analysis status"""
        print("\n" + "="*60)
        print("📊 ICT MARKET STRUCTURE STATUS")
        print("="*60)
        print(f"   Market Phase: {self.market_phase}")
        print(f"   Intent Direction: {self.intent_direction or 'NEUTRAL'}")
        print(f"   Context Confidence: {self.market_context_confidence*100:.0f}%")
        print(f"   Asian Session Progress: {self.asian_session_progress*100:.0f}%")
        print(f"   Execution Allowed: ✅ YES (always enabled - confidence weighting active)")
        print(f"   Asian Range: {f'{self.asian_low:.2f} - {self.asian_high:.2f}' if self.asian_range_set else 'Not set'}")
        print(f"   Liquidity Swept: {self.liquidity_swept or 'None'}")
        if self.dealing_range_high and self.dealing_range_low:
            print(f"   Dealing Range: {self.dealing_range_low:.2f} - {self.dealing_range_high:.2f}")
        print(f"   Active FVG Zones: {len([f for f in self.fvg_zones if not f.get('filled', True)])}")
        print("="*60)


class ICTChartVisualizer:
    """
    ICT Chart Visualization Module
    
    Purpose:
    - Mark important ICT concepts on the MT5 chart
    - Allow human developers to audit agent reasoning
    - Provide visual feedback for bias, intent, and targets
    
    Philosophy:
    - Visuals reflect reasoning, not predictions
    - Marks are contextual, not cluttered
    - Every mark answers: Where is liquidity? Where did intent appear? Where may price react?
    """
    
    def __init__(self, symbol="XAUUSD"):
        self.symbol = symbol
        self.object_prefix = "ICT_"  # Prefix for all ICT objects
        self.active_objects = []  # Track created objects for cleanup
        
        # Color scheme (BGR format for MT5)
        self.colors = {
            'asian_range': 0x4D4D4D,      # Gray - neutral
            'asian_range_fill': 0x3D3D3D,  # Darker gray fill
            'bullish_sweep': 0x00AA00,     # Green
            'bearish_sweep': 0x0000AA,     # Red
            'displacement_bull': 0x00FF00, # Bright green
            'displacement_bear': 0x0000FF, # Bright red
            'fvg_bullish': 0x80FF80,       # Light green
            'fvg_bearish': 0x8080FF,       # Light red
            'daily_poi': 0xFFAA00,         # Orange
            'target': 0xFFFF00,            # Yellow
            'liquidity_above': 0x00AAFF,   # Cyan
            'liquidity_below': 0xFF00AA,   # Magenta
        }
        
        # Object counters for unique naming
        self.object_count = 0
        self.last_cleanup = None
        
    def _get_unique_name(self, base_name):
        """Generate unique object name"""
        self.object_count += 1
        return f"{self.object_prefix}{base_name}_{self.object_count}"
    
    def _delete_object(self, name):
        """Delete a single chart object - DISABLED (MT5 Python API limitation)"""
        # MT5 Python API doesn't support chart object operations
        if name in self.active_objects:
            self.active_objects.remove(name)
    
    def cleanup_old_objects(self, max_age_hours=24):
        """Remove old ICT objects - DISABLED (MT5 Python API doesn't support chart objects)"""
        # Just track internally, don't try to call MT5 chart object APIs
        if len(self.active_objects) > 50:
            self.active_objects = self.active_objects[-50:]
        self.last_cleanup = datetime.now()
    
    def cleanup_by_prefix(self, prefix):
        """Remove all objects with specific prefix - DISABLED (MT5 Python API doesn't support objects_total)"""
        # MT5 Python API doesn't support objects_total, object_name, object_delete
        # Chart object management is not available in Python API
        pass
    
    def draw_asian_range(self, asian_high, asian_low, start_time, end_time):
        """
        Draw Asian Session Range as shaded horizontal zone
        
        Purpose: Represents liquidity accumulation, reference for later sweeps
        """
        try:
            import MetaTrader5 as mt5
            
            # Clean up old Asian range
            self.cleanup_by_prefix("ASIA_")
            
            name = self._get_unique_name("ASIA_RANGE")
            
            # Create rectangle for Asian range
            if not mt5.object_create(0, name, mt5.OBJ_RECTANGLE, 0, 
                                     start_time, asian_high, 
                                     end_time, asian_low):
                return False
            
            # Set properties
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, self.colors['asian_range'])
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DOT)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_integer(0, name, mt5.OBJPROP_FILL, True)
            mt5.object_set_integer(0, name, mt5.OBJPROP_BACK, True)  # Background
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, "Asia Range")
            
            self.active_objects.append(name)
            
            # Add label
            label_name = self._get_unique_name("ASIA_LABEL")
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, start_time, asian_high + 0.5)
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, f"📦 Asia Range")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, self.colors['asian_range'])
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 8)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] 📦 Drew Asian Range: {asian_low:.2f} - {asian_high:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error drawing Asian range: {e}")
            return False
    
    def mark_liquidity_sweep(self, sweep_type, price, time_point):
        """
        Mark liquidity sweep on chart
        
        sweep_type: 'ASIAN_HIGH_SWEPT' or 'ASIAN_LOW_SWEPT'
        """
        try:
            import MetaTrader5 as mt5
            
            is_high_sweep = "HIGH" in sweep_type
            color = self.colors['bearish_sweep'] if is_high_sweep else self.colors['bullish_sweep']
            label = "Sell-side liquidity taken" if is_high_sweep else "Buy-side liquidity taken"
            
            # Draw horizontal line at swept level
            name = self._get_unique_name("SWEEP_LINE")
            mt5.object_create(0, name, mt5.OBJ_HLINE, 0, time_point, price)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DASH)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, label)
            
            self.active_objects.append(name)
            
            # Add arrow marker
            arrow_name = self._get_unique_name("SWEEP_ARROW")
            arrow_code = 234 if is_high_sweep else 233  # Down/Up arrow
            mt5.object_create(0, arrow_name, mt5.OBJ_ARROW, 0, time_point, price)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_ARROWCODE, arrow_code)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_WIDTH, 2)
            
            self.active_objects.append(arrow_name)
            
            # Add text label
            text_name = self._get_unique_name("SWEEP_TEXT")
            mt5.object_create(0, text_name, mt5.OBJ_TEXT, 0, time_point, price + (1 if is_high_sweep else -1))
            mt5.object_set_string(0, text_name, mt5.OBJPROP_TEXT, f"🎯 {label}")
            mt5.object_set_integer(0, text_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, text_name, mt5.OBJPROP_FONTSIZE, 8)
            
            self.active_objects.append(text_name)
            
            print(f"[CHART] 🎯 Marked Liquidity Sweep: {label} @ {price:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error marking liquidity sweep: {e}")
            return False
    
    def mark_displacement(self, direction, start_time, end_time, high, low):
        """
        Mark displacement/intent candle(s) on chart
        
        direction: 'BULLISH' or 'BEARISH'
        """
        try:
            import MetaTrader5 as mt5
            
            is_bullish = direction == "BULLISH"
            color = self.colors['displacement_bull'] if is_bullish else self.colors['displacement_bear']
            
            # Draw rectangle around displacement candles
            name = self._get_unique_name("DISPLACE")
            mt5.object_create(0, name, mt5.OBJ_RECTANGLE, 0, start_time, high, end_time, low)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_SOLID)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 2)
            mt5.object_set_integer(0, name, mt5.OBJPROP_FILL, False)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, f"{direction} Displacement")
            
            self.active_objects.append(name)
            
            # Add vertical line to emphasize
            vline_name = self._get_unique_name("DISPLACE_VLINE")
            mt5.object_create(0, vline_name, mt5.OBJ_VLINE, 0, end_time, 0)
            mt5.object_set_integer(0, vline_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, vline_name, mt5.OBJPROP_STYLE, mt5.STYLE_DASHDOT)
            mt5.object_set_integer(0, vline_name, mt5.OBJPROP_WIDTH, 1)
            
            self.active_objects.append(vline_name)
            
            # Add label
            label_name = self._get_unique_name("DISPLACE_LABEL")
            label_price = high + 1 if is_bullish else low - 1
            emoji = "⚡🟢" if is_bullish else "⚡🔴"
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, end_time, label_price)
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, f"{emoji} DISPLACEMENT / INTENT")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 9)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] ⚡ Marked {direction} Displacement")
            return True
            
        except Exception as e:
            print(f"[CHART] Error marking displacement: {e}")
            return False
    
    def draw_fvg_zone(self, fvg_type, high, low, start_time, extend_bars=50):
        """
        Draw Fair Value Gap / Inefficiency Zone
        
        fvg_type: 'BULLISH_FVG' or 'BEARISH_FVG'
        """
        try:
            import MetaTrader5 as mt5
            
            is_bullish = "BULLISH" in fvg_type
            color = self.colors['fvg_bullish'] if is_bullish else self.colors['fvg_bearish']
            
            # Calculate end time (extend forward)
            end_time = start_time + timedelta(hours=extend_bars * 0.5)  # M30 bars
            
            # Draw semi-transparent rectangle
            name = self._get_unique_name("FVG")
            mt5.object_create(0, name, mt5.OBJ_RECTANGLE, 0, start_time, high, end_time, low)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DOT)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_integer(0, name, mt5.OBJPROP_FILL, True)
            mt5.object_set_integer(0, name, mt5.OBJPROP_BACK, True)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, f"FVG {high:.2f}-{low:.2f}")
            
            self.active_objects.append(name)
            
            # Add label
            label_name = self._get_unique_name("FVG_LABEL")
            midpoint = (high + low) / 2
            emoji = "📊🟢" if is_bullish else "📊🔴"
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, start_time, midpoint)
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, f"{emoji} FVG/Inefficiency")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 7)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] 📊 Drew FVG Zone: {low:.2f} - {high:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error drawing FVG: {e}")
            return False
    
    def mark_fvg_filled(self, fvg_name):
        """Mark an FVG as filled (fade it out)"""
        try:
            import MetaTrader5 as mt5
            
            # Change color to gray to indicate filled
            mt5.object_set_integer(0, fvg_name, mt5.OBJPROP_COLOR, 0x808080)
            mt5.object_set_integer(0, fvg_name, mt5.OBJPROP_STYLE, mt5.STYLE_DOT)
            
        except:
            pass
    
    def draw_daily_poi(self, poi_type, price, label_text):
        """
        Draw Daily Point of Interest (HTF levels)
        
        poi_type: 'LIQUIDITY', 'IMBALANCE', 'ORDER_BLOCK'
        """
        try:
            import MetaTrader5 as mt5
            
            color = self.colors['daily_poi']
            
            # Draw horizontal line
            name = self._get_unique_name("DAILY_POI")
            mt5.object_create(0, name, mt5.OBJ_HLINE, 0, datetime.now(), price)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DASHDOTDOT)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 2)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, label_text)
            
            self.active_objects.append(name)
            
            # Add right-side label
            label_name = self._get_unique_name("DAILY_POI_LABEL")
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, datetime.now(), price + 0.3)
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, f"📍 {label_text}")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 8)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_ANCHOR, mt5.ANCHOR_LEFT)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] 📍 Drew Daily POI: {label_text} @ {price:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error drawing daily POI: {e}")
            return False
    
    def draw_liquidity_target(self, direction, price, label="Likely draw on liquidity"):
        """
        Draw liquidity target projection
        
        direction: 'ABOVE' or 'BELOW'
        """
        try:
            import MetaTrader5 as mt5
            
            is_above = direction == "ABOVE"
            color = self.colors['liquidity_above'] if is_above else self.colors['liquidity_below']
            
            # Draw dashed line at target
            name = self._get_unique_name("TARGET")
            mt5.object_create(0, name, mt5.OBJ_HLINE, 0, datetime.now(), price)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DASH)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, label)
            
            self.active_objects.append(name)
            
            # Add arrow pointing to target
            arrow_name = self._get_unique_name("TARGET_ARROW")
            arrow_code = 241 if is_above else 242  # Thumb up/down
            mt5.object_create(0, arrow_name, mt5.OBJ_ARROW, 0, datetime.now(), price)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_ARROWCODE, arrow_code)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, arrow_name, mt5.OBJPROP_WIDTH, 2)
            
            self.active_objects.append(arrow_name)
            
            # Add label
            label_name = self._get_unique_name("TARGET_LABEL")
            emoji = "🎯⬆️" if is_above else "🎯⬇️"
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, datetime.now(), price + (0.5 if is_above else -0.5))
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, f"{emoji} {label}")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 8)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] 🎯 Drew Liquidity Target: {direction} @ {price:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error drawing target: {e}")
            return False
    
    def draw_dealing_range(self, high, low, start_time):
        """Draw the dealing range after displacement"""
        try:
            import MetaTrader5 as mt5
            
            # Clean old dealing range
            self.cleanup_by_prefix("DEALING_")
            
            end_time = start_time + timedelta(hours=12)  # Extend 12 hours
            
            # Draw rectangle
            name = self._get_unique_name("DEALING_RANGE")
            mt5.object_create(0, name, mt5.OBJ_RECTANGLE, 0, start_time, high, end_time, low)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, 0xFFFFFF)  # White
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DASHDOT)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_integer(0, name, mt5.OBJPROP_FILL, False)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, "Dealing Range")
            
            self.active_objects.append(name)
            
            # Draw midpoint line (equilibrium)
            midpoint = (high + low) / 2
            mid_name = self._get_unique_name("DEALING_MID")
            mt5.object_create(0, mid_name, mt5.OBJ_TREND, 0, start_time, midpoint, end_time, midpoint)
            mt5.object_set_integer(0, mid_name, mt5.OBJPROP_COLOR, 0xAAAA00)  # Yellow-ish
            mt5.object_set_integer(0, mid_name, mt5.OBJPROP_STYLE, mt5.STYLE_DOT)
            mt5.object_set_integer(0, mid_name, mt5.OBJPROP_RAY_RIGHT, False)
            
            self.active_objects.append(mid_name)
            
            # Label
            label_name = self._get_unique_name("DEALING_LABEL")
            mt5.object_create(0, label_name, mt5.OBJ_TEXT, 0, start_time, high + 0.5)
            mt5.object_set_string(0, label_name, mt5.OBJPROP_TEXT, "📐 Dealing Range")
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_COLOR, 0xFFFFFF)
            mt5.object_set_integer(0, label_name, mt5.OBJPROP_FONTSIZE, 8)
            
            self.active_objects.append(label_name)
            
            print(f"[CHART] 📐 Drew Dealing Range: {low:.2f} - {high:.2f}")
            return True
            
        except Exception as e:
            print(f"[CHART] Error drawing dealing range: {e}")
            return False
    
    def draw_session_divider(self, session_name, time_point):
        """Draw vertical line to mark session start"""
        try:
            import MetaTrader5 as mt5
            
            colors = {
                'ASIAN': 0x808080,      # Gray
                'LONDON': 0x00AA00,     # Green
                'NEW_YORK': 0x0000AA,   # Red
            }
            color = colors.get(session_name, 0xFFFFFF)
            
            name = self._get_unique_name(f"SESSION_{session_name}")
            mt5.object_create(0, name, mt5.OBJ_VLINE, 0, time_point, 0)
            mt5.object_set_integer(0, name, mt5.OBJPROP_COLOR, color)
            mt5.object_set_integer(0, name, mt5.OBJPROP_STYLE, mt5.STYLE_DOT)
            mt5.object_set_integer(0, name, mt5.OBJPROP_WIDTH, 1)
            mt5.object_set_string(0, name, mt5.OBJPROP_TEXT, f"{session_name} Start")
            
            self.active_objects.append(name)
            return True
            
        except:
            return False
    
    def update_from_ict_analysis(self, ict_analysis, df):
        """
        Main update function - sync chart visuals with ICT analysis state
        
        Called on each bar to update chart marks based on ICT analyzer state
        """
        try:
            current_time = df.iloc[-1]['time'] if 'time' in df.columns else datetime.now()
            current = df.iloc[-1]
            
            # 1. Asian Range
            if ict_analysis.get('asian_high') and ict_analysis.get('asian_low'):
                # Only draw once when range is established
                asian_high = ict_analysis['asian_high']
                asian_low = ict_analysis['asian_low']
                
                # Calculate session start time (today at 00:00 UTC)
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                asian_start = today
                asian_end = today.replace(hour=8)
                
                if ict_analysis['session'] != 'ASIAN':
                    self.draw_asian_range(asian_high, asian_low, asian_start, asian_end)
            
            # 2. Liquidity Sweep
            if ict_analysis.get('liquidity_swept'):
                sweep = ict_analysis['liquidity_swept']
                if 'HIGH' in sweep:
                    self.mark_liquidity_sweep(sweep, ict_analysis['asian_high'], current_time)
                else:
                    self.mark_liquidity_sweep(sweep, ict_analysis['asian_low'], current_time)
            
            # 3. Displacement
            if ict_analysis.get('displacement'):
                direction = "BULLISH" if "BULLISH" in ict_analysis['displacement'] else "BEARISH"
                # Use last 3 candles for displacement zone
                recent = df.tail(3)
                self.mark_displacement(
                    direction,
                    recent.iloc[0]['time'] if 'time' in recent.columns else datetime.now() - timedelta(hours=1.5),
                    current_time,
                    recent['high'].max(),
                    recent['low'].min()
                )
            
            # 4. FVG Zones
            for fvg in ict_analysis.get('fvg_zones', []):
                if not fvg.get('drawn', False):
                    self.draw_fvg_zone(
                        fvg['type'],
                        fvg['high'],
                        fvg['low'],
                        current_time
                    )
                    fvg['drawn'] = True
                elif fvg.get('filled', False) and not fvg.get('marked_filled', False):
                    # FVG was filled - could fade it
                    fvg['marked_filled'] = True
            
            # 5. Targets
            for target in ict_analysis.get('targets', [])[:2]:  # Max 2 targets
                direction = "ABOVE" if target > current['close'] else "BELOW"
                self.draw_liquidity_target(direction, target)
            
            # 6. Periodic cleanup (every hour)
            if self.last_cleanup is None or (datetime.now() - self.last_cleanup).seconds > 3600:
                self.cleanup_old_objects()
                
        except Exception as e:
            print(f"[CHART] Error updating visuals: {e}")
    
    def print_legend(self):
        """Print chart legend to console"""
        print("\n" + "="*60)
        print("📊 ICT CHART VISUALIZATION LEGEND")
        print("="*60)
        print("   📦 Gray Box      = Asian Session Range (Liquidity Pool)")
        print("   🎯 Arrow+Line    = Liquidity Sweep (Stop Hunt)")
        print("   ⚡ Bordered Box  = Displacement (Intent Revealed)")
        print("   📊 Shaded Zone   = FVG/Inefficiency (Reaction Area)")
        print("   📍 Orange Dash   = Daily POI (HTF Reference)")
        print("   🎯 Colored Line  = Liquidity Target (Draw Direction)")
        print("   📐 White Box     = Dealing Range (Trade Zone)")
        print("="*60)


class XAUUSDTradingBot:
    """XAUUSD M30 Trading Bot - Main Controller"""

    def __init__(self, config=None):
        self.config = config or CONFIG
        self.cerebro = None
        self.results = None
        self.daily_bias = None  # Will store daily bias analysis
        self.bias_confidence = 0  # Confidence level 0-100
        self.last_bias_update = None  # Track when bias was last updated
        self.ict_analyzer = ICTMarketAnalyzer()  # ICT Market Analysis Module
        self.chart_visualizer = ICTChartVisualizer()  # ICT Chart Visualization

    def setup_cerebro(self):
        """Initialize Backtrader Cerebro with strategy and analyzers"""
        print("\n" + "="*80)
        print("[BOT] XAUUSD M30 TRADING BOT - INITIALIZING")
        print("="*80)

        # Create Cerebro instance
        self.cerebro = bt.Cerebro(stdstats=False)

        # Load data
        data_path = Path(__file__).parent / 'data' / self.config['data_file']
        if not data_path.exists():
            raise FileNotFoundError(f"[ERROR] Data file not found: {data_path}")

        print(f"[DATA] Loading data: {self.config['data_file']}")

        # Parse dates
        from_date = datetime.strptime(self.config['from_date'], '%Y-%m-%d')
        to_date = datetime.strptime(self.config['to_date'], '%Y-%m-%d')

        print(f"[DATE] Backtest Period: {self.config['from_date']} to {self.config['to_date']}")
        print(f"[TIMER]  Timeframe: {self.config['timeframe']} (5-minute candles)")

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
            compression=30,  # FIXED: 30-minute compression (was 1)
            fromdate=from_date,
            todate=to_date
        )

        self.cerebro.adddata(data)

        # Set broker parameters
        self.cerebro.broker.setcash(self.config['starting_cash'])
        self.cerebro.broker.setcommission(leverage=self.config['leverage'])

        print(f"[MONEY] Starting Capital: ${self.config['starting_cash']:,.2f}")
        print(f"[STATS] Leverage: {self.config['leverage']}:1")
        print(f"[TARGET] Risk Per Trade: {self.config['risk_percent']*100:.2f}%")

        # Prepare strategy parameters
        strat_params = {
            # Trading direction
            'enable_long_trades': self.config['enable_long'],
            'enable_short_trades': self.config['enable_short'],

            # EMA parameters
            'ema_fast_length': self.config['ema_fast'],
            'ema_medium_length': self.config['ema_medium'],
            'ema_slow_length': self.config['ema_slow'],
            'ema_confirm_length': self.config['ema_confirm'],
            'ema_filter_price_length': self.config['ema_filter'],
            'atr_length': self.config['atr_period'],

            # Pullback system
            'long_use_pullback_entry': self.config['long_pullback_enabled'],
            'short_use_pullback_entry': self.config['short_pullback_enabled'],
            'long_pullback_max_candles': self.config['long_pullback_candles'],
            'short_pullback_max_candles': self.config['short_pullback_candles'],
            'long_entry_window_periods': self.config['long_window_periods'],
            'short_entry_window_periods': self.config['short_window_periods'],

            # Volatility expansion
            'use_window_time_offset': self.config['use_time_offset'],
            'window_offset_multiplier': self.config['window_offset_multiplier'],
            'window_price_offset_multiplier': self.config['window_price_offset'],

            # ATR filters
            'long_use_atr_filter': self.config['long_atr_filter'],
            'long_atr_min_threshold': self.config['long_atr_min'],
            'long_atr_max_threshold': self.config['long_atr_max'],
            'short_use_atr_filter': self.config['short_atr_filter'],
            'short_atr_min_threshold': self.config['short_atr_min'],
            'short_atr_max_threshold': self.config['short_atr_max'],

            # Entry filters
            'long_use_price_filter_ema': self.config['long_use_price_filter'],
            'long_use_angle_filter': self.config['long_use_angle_filter'],
            'long_min_angle': self.config['long_min_angle'],
            'long_max_angle': self.config['long_max_angle'],
            'short_use_price_filter_ema': self.config['short_use_price_filter'],
            'short_use_angle_filter': self.config['short_use_angle_filter'],
            'short_min_angle': self.config['short_min_angle'],
            'short_max_angle': self.config['short_max_angle'],

            # Time filter
            'use_time_range_filter': self.config['use_time_filter'],
            'entry_start_hour': self.config['session_start_hour'],
            'entry_start_minute': self.config['session_start_minute'],
            'entry_end_hour': self.config['session_end_hour'],
            'entry_end_minute': self.config['session_end_minute'],

            # Risk management
            'enable_risk_sizing': True,
            'risk_percent': self.config['risk_percent'],
            'long_atr_sl_multiplier': self.config['long_sl_multiplier'],
            'long_atr_tp_multiplier': self.config['long_tp_multiplier'],
            'short_atr_sl_multiplier': self.config['short_sl_multiplier'],
            'short_atr_tp_multiplier': self.config['short_tp_multiplier'],

            # Other settings
            'use_forex_position_calc': True,
            'forex_instrument': 'XAUUSD',
            'print_signals': False,
            'verbose_debug': self.config['verbose_debug'],
            'plot_result': self.config['enable_plot'],
            'plot_sltp_lines': self.config['plot_sltp'],
        }

        # Add strategy
        self.cerebro.addstrategy(SunriseOgle, **strat_params)

        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                                timeframe=bt.TimeFrame.Days, riskfreerate=0.0)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # Add observers for visualization
        if self.config['enable_plot']:
            try:
                self.cerebro.addobserver(bt.observers.BuySell, barplot=False,
                                        plotdist=0.0005)
                self.cerebro.addobserver(bt.observers.Value)
            except:
                pass

        # Print strategy configuration
        trading_modes = []
        if self.config['enable_long']:
            trading_modes.append("[GREEN] LONG")
        if self.config['enable_short']:
            trading_modes.append("[RED] SHORT")

        print(f"\n[TARGET] Trading Mode: {' & '.join(trading_modes)}")
        print(f"[STATS] Pullback Entry: {'[OK] ENABLED' if self.config['long_pullback_enabled'] or self.config['short_pullback_enabled'] else '[ERROR] DISABLED'}")
        print(f"[FILTER] ATR Filters: {'[OK] ENABLED' if self.config['long_atr_filter'] or self.config['short_atr_filter'] else '[ERROR] DISABLED'}")
        print(f"[FILTER] Time Filter: {'[OK] ENABLED' if self.config['use_time_filter'] else '[ERROR] DISABLED'}")
        print(f"[WINDOW] LONG Window: {self.config['long_window_periods']} bars | SHORT Window: {self.config['short_window_periods']} bars")
        print("="*80 + "\n")

    def run(self):
        """Execute the trading bot"""
        if not self.cerebro:
            self.setup_cerebro()

        print("[ROCKET] Starting backtest...\n")

        # Run strategy
        self.results = self.cerebro.run()

        # Print results
        self.print_results()

        # Plot if enabled
        if self.config['enable_plot']:
            self.plot_results()

        return self.results

    def print_results(self):
        """Print performance metrics"""
        final_value = self.cerebro.broker.getvalue()
        starting_cash = self.config['starting_cash']
        pnl = final_value - starting_cash
        returns = (pnl / starting_cash) * 100

        print("\n" + "="*80)
        print("[STATS] BACKTEST RESULTS - XAUUSD M30 TRADING BOT")
        print("="*80)

        # Portfolio metrics
        print(f"\n[ACCOUNT] PORTFOLIO PERFORMANCE:")
        print(f"   Starting Capital:    ${starting_cash:,.2f}")
        print(f"   Final Value:         ${final_value:,.2f}")
        print(f"   Total P&L:           ${pnl:+,.2f}")
        print(f"   Return:              {returns:+.2f}%")

        # Get strategy results
        strategy = self.results[0]

        # Sharpe Ratio
        try:
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            sharpe = sharpe_analysis.get('sharperatio', None)
            if sharpe is not None:
                print(f"\n[UP] RISK-ADJUSTED METRICS:")
                print(f"   Sharpe Ratio:        {sharpe:.3f}")
        except:
            pass

        # Drawdown
        try:
            dd_analysis = strategy.analyzers.drawdown.get_analysis()
            max_dd = dd_analysis.get('max', {}).get('drawdown', 0)
            max_dd_money = dd_analysis.get('max', {}).get('moneydown', 0)

            # Ensure percentage format
            if abs(max_dd) <= 1.0:
                max_dd = abs(max_dd) * 100
            else:
                max_dd = abs(max_dd)

            print(f"   Max Drawdown:        {max_dd:.2f}%")
            print(f"   Max Drawdown ($):    ${abs(max_dd_money):,.2f}")
        except:
            pass

        # Trade statistics
        try:
            trade_analysis = strategy.analyzers.trades.get_analysis()
            total_trades = trade_analysis.get('total', {}).get('total', 0)
            won_trades = trade_analysis.get('won', {}).get('total', 0)
            lost_trades = trade_analysis.get('lost', {}).get('total', 0)

            if total_trades > 0:
                win_rate = (won_trades / total_trades) * 100

                # Profit factor
                won_dict = trade_analysis.get('won', {})
                lost_dict = trade_analysis.get('lost', {})

                gross_profit = won_dict.get('pnl', {}).get('total', 0)
                gross_loss = abs(lost_dict.get('pnl', {}).get('total', 0))

                if gross_loss > 0:
                    profit_factor = gross_profit / gross_loss
                else:
                    profit_factor = float('inf')

                avg_win = won_dict.get('pnl', {}).get('average', 0)
                avg_loss = lost_dict.get('pnl', {}).get('average', 0)

                print(f"\n[TARGET] TRADE STATISTICS:")
                print(f"   Total Trades:        {total_trades}")
                print(f"   Winning Trades:      {won_trades} ({win_rate:.2f}%)")
                print(f"   Losing Trades:       {lost_trades}")

                pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
                print(f"\n[MONEY] PROFITABILITY:")
                print(f"   Profit Factor:       {pf_str}")
                print(f"   Gross Profit:        ${gross_profit:,.2f}")
                print(f"   Gross Loss:          ${gross_loss:,.2f}")
                print(f"   Average Win:         ${avg_win:,.2f}")
                print(f"   Average Loss:        ${avg_loss:,.2f}")

                if avg_loss != 0:
                    expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * abs(avg_loss))
                    print(f"   Expectancy/Trade:    ${expectancy:,.2f}")
        except Exception as e:
            print(f"[WARNING]  Error analyzing trades: {e}")

        # ICT Confidence Distribution Analysis
        self.print_confidence_analysis()

        print("\n" + "="*80 + "\n")

    def print_confidence_analysis(self):
        """Analyze and print ICT confidence distribution"""
        confidence_log = self.ict_analyzer.confidence_log

        if not confidence_log:
            print("\n[ICT] No confidence data logged")
            return

        import statistics

        # Extract confidence values
        confidences = [log['confidence_at_entry'] for log in confidence_log]

        print("\n[ICT] CONFIDENCE DISTRIBUTION ANALYSIS:")
        print(f"   Total Signals:       {len(confidences)}")
        print(f"   Mean Confidence:     {statistics.mean(confidences):.3f}")
        print(f"   Median Confidence:   {statistics.median(confidences):.3f}")
        print(f"   Min Confidence:      {min(confidences):.3f}")
        print(f"   Max Confidence:      {max(confidences):.3f}")
        print(f"   Std Deviation:       {statistics.stdev(confidences) if len(confidences) > 1 else 0:.3f}")

        # Confidence distribution buckets
        buckets = {
            '0.2-0.4 (Very Low)': 0,
            '0.4-0.6 (Low)': 0,
            '0.6-0.8 (Medium)': 0,
            '0.8-1.0 (High)': 0
        }

        for conf in confidences:
            if conf < 0.4:
                buckets['0.2-0.4 (Very Low)'] += 1
            elif conf < 0.6:
                buckets['0.4-0.6 (Low)'] += 1
            elif conf < 0.8:
                buckets['0.6-0.8 (Medium)'] += 1
            else:
                buckets['0.8-1.0 (High)'] += 1

        print("\n   Distribution:")
        for bucket, count in buckets.items():
            pct = (count / len(confidences)) * 100 if confidences else 0
            print(f"   {bucket:20s} {count:3d} ({pct:5.1f}%)")

        # Strategy type distribution
        strategy_types = {}
        for log in confidence_log:
            st = log.get('strategy_type', 'UNKNOWN')
            strategy_types[st] = strategy_types.get(st, 0) + 1

        print("\n   Strategy Types:")
        for st, count in sorted(strategy_types.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(confidence_log)) * 100
            print(f"   {st:20s} {count:3d} ({pct:5.1f}%)")

    def plot_results(self):
        """Display performance chart"""
        try:
            print("[STATS] Generating performance chart...\n")

            # Determine trading mode for title
            modes = []
            if self.config['enable_long']:
                modes.append("LONG")
            if self.config['enable_short']:
                modes.append("SHORT")
            mode_str = " & ".join(modes)

            strategy = self.results[0]
            final_value = self.cerebro.broker.getvalue()
            pnl = final_value - self.config['starting_cash']

            # Create title
            title = f"XAUUSD M30 Bot ({mode_str})\n"
            title += f"P&L: ${pnl:+,.0f} | "

            try:
                total_trades = strategy.analyzers.trades.get_analysis().get('total', {}).get('total', 0)
                won = strategy.analyzers.trades.get_analysis().get('won', {}).get('total', 0)
                win_rate = (won/total_trades*100) if total_trades > 0 else 0
                title += f"Trades: {total_trades} | Win Rate: {win_rate:.1f}%"
            except:
                pass

            self.cerebro.plot(style='candlestick', subtitle=title)

        except Exception as e:
            print(f"[WARNING]  Plot error: {e}")

    def analyze_daily_bias(self, mt5_trader):
        """
        ICT Daily Bias Analysis - Determine Market Direction
        
        ICT Principles Applied:
        1. Daily Timeframe Order Flow (Higher Highs/Lows = Bullish, Lower Lows/Highs = Bearish)
        2. Imbalance to Rebalance (Price seeks to fill Fair Value Gaps)
        3. Draw on Liquidity (Price hunts old highs/lows as targets)
        """
        print("\n" + "="*70)
        print("[CHART] ICT DAILY BIAS ANALYSIS - Determining Market Direction")
        print("="*70)

        try:
            import MetaTrader5 as mt5

            bias_scores = {
                'bullish': 0,
                'bearish': 0,
                'neutral': 0
            }

            analysis_details = []

            # ==================== 1. DAILY ORDER FLOW (ICT Core) ====================
            print("\n[1] 📊 ICT DAILY ORDER FLOW (Higher Highs/Lows Structure)...")

            d1_rates = mt5.copy_rates_from_pos(mt5_trader.symbol, mt5.TIMEFRAME_D1, 0, 15)
            if d1_rates is not None and len(d1_rates) >= 10:
                import pandas as pd
                d1_df = pd.DataFrame(d1_rates)
                
                # Identify swing highs and lows (last 10 days)
                swing_highs = []
                swing_lows = []
                
                for i in range(2, len(d1_df) - 2):
                    # Swing High: Higher than 2 candles on each side
                    if (d1_df.iloc[i]['high'] > d1_df.iloc[i-1]['high'] and 
                        d1_df.iloc[i]['high'] > d1_df.iloc[i-2]['high'] and
                        d1_df.iloc[i]['high'] > d1_df.iloc[i+1]['high'] and 
                        d1_df.iloc[i]['high'] > d1_df.iloc[i+2]['high']):
                        swing_highs.append({'index': i, 'price': d1_df.iloc[i]['high']})
                    
                    # Swing Low: Lower than 2 candles on each side
                    if (d1_df.iloc[i]['low'] < d1_df.iloc[i-1]['low'] and 
                        d1_df.iloc[i]['low'] < d1_df.iloc[i-2]['low'] and
                        d1_df.iloc[i]['low'] < d1_df.iloc[i+1]['low'] and 
                        d1_df.iloc[i]['low'] < d1_df.iloc[i+2]['low']):
                        swing_lows.append({'index': i, 'price': d1_df.iloc[i]['low']})
                
                # Determine Order Flow based on swing structure
                order_flow = "NEUTRAL"
                
                if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                    # Check if making Higher Highs and Higher Lows (Bullish Order Flow)
                    recent_highs = sorted(swing_highs, key=lambda x: x['index'])[-2:]
                    recent_lows = sorted(swing_lows, key=lambda x: x['index'])[-2:]
                    
                    higher_highs = recent_highs[-1]['price'] > recent_highs[-2]['price'] if len(recent_highs) >= 2 else False
                    higher_lows = recent_lows[-1]['price'] > recent_lows[-2]['price'] if len(recent_lows) >= 2 else False
                    lower_highs = recent_highs[-1]['price'] < recent_highs[-2]['price'] if len(recent_highs) >= 2 else False
                    lower_lows = recent_lows[-1]['price'] < recent_lows[-2]['price'] if len(recent_lows) >= 2 else False
                    
                    if higher_highs and higher_lows:
                        order_flow = "BULLISH"
                        bias_scores['bullish'] += 25  # Heavy weight for order flow
                        analysis_details.append("   ✅ Daily Order Flow: BULLISH (Higher Highs & Higher Lows)")
                        analysis_details.append(f"      Last Swing High: {recent_highs[-1]['price']:.2f} > Previous: {recent_highs[-2]['price']:.2f}")
                        analysis_details.append(f"      Last Swing Low: {recent_lows[-1]['price']:.2f} > Previous: {recent_lows[-2]['price']:.2f}")
                    elif lower_highs and lower_lows:
                        order_flow = "BEARISH"
                        bias_scores['bearish'] += 25  # Heavy weight for order flow
                        analysis_details.append("   ✅ Daily Order Flow: BEARISH (Lower Highs & Lower Lows)")
                        analysis_details.append(f"      Last Swing High: {recent_highs[-1]['price']:.2f} < Previous: {recent_highs[-2]['price']:.2f}")
                        analysis_details.append(f"      Last Swing Low: {recent_lows[-1]['price']:.2f} < Previous: {recent_lows[-2]['price']:.2f}")
                    elif higher_highs and not higher_lows:
                        order_flow = "BULLISH_WEAK"
                        bias_scores['bullish'] += 12
                        analysis_details.append("   ⚠️ Daily Order Flow: WEAK BULLISH (Higher High but no Higher Low yet)")
                    elif lower_lows and not lower_highs:
                        order_flow = "BEARISH_WEAK"
                        bias_scores['bearish'] += 12
                        analysis_details.append("   ⚠️ Daily Order Flow: WEAK BEARISH (Lower Low but no Lower High yet)")
                    else:
                        bias_scores['neutral'] += 10
                        analysis_details.append("   ⚠️ Daily Order Flow: CONSOLIDATING (No clear structure)")
                else:
                    analysis_details.append("   ⚠️ Insufficient swing points to determine order flow")

            # ==================== 2. IMBALANCE TO REBALANCE (FVG Detection) ====================
            print("[2] 📊 ICT IMBALANCE ANALYSIS (Fair Value Gaps)...")

            if d1_rates is not None and len(d1_rates) >= 5:
                # Look for unfilled FVGs on daily timeframe
                unfilled_bullish_fvg = None
                unfilled_bearish_fvg = None
                current_price = d1_df.iloc[-1]['close']
                
                for i in range(2, min(len(d1_df), 10)):  # Check last 10 days
                    candle_0 = d1_df.iloc[-i]      # Current in loop
                    candle_2 = d1_df.iloc[-i-2]    # 2 back
                    
                    # Bullish FVG: Gap up (candle_0 low > candle_2 high)
                    if candle_0['low'] > candle_2['high']:
                        fvg_high = candle_0['low']
                        fvg_low = candle_2['high']
                        fvg_mid = (fvg_high + fvg_low) / 2
                        
                        # Check if unfilled (price hasn't reached midpoint)
                        if current_price > fvg_mid:
                            unfilled_bullish_fvg = {'high': fvg_high, 'low': fvg_low, 'mid': fvg_mid}
                    
                    # Bearish FVG: Gap down (candle_0 high < candle_2 low)
                    if candle_0['high'] < candle_2['low']:
                        fvg_high = candle_2['low']
                        fvg_low = candle_0['high']
                        fvg_mid = (fvg_high + fvg_low) / 2
                        
                        # Check if unfilled
                        if current_price < fvg_mid:
                            unfilled_bearish_fvg = {'high': fvg_high, 'low': fvg_low, 'mid': fvg_mid}
                
                if unfilled_bullish_fvg and current_price > unfilled_bullish_fvg['mid']:
                    # Price above unfilled bullish FVG - may retrace to fill it
                    analysis_details.append(f"   📍 Bullish FVG below: {unfilled_bullish_fvg['low']:.2f} - {unfilled_bullish_fvg['high']:.2f}")
                    analysis_details.append(f"      Price may retrace to fill before continuing up")
                    
                if unfilled_bearish_fvg and current_price < unfilled_bearish_fvg['mid']:
                    # Price below unfilled bearish FVG - may retrace to fill it
                    analysis_details.append(f"   📍 Bearish FVG above: {unfilled_bearish_fvg['low']:.2f} - {unfilled_bearish_fvg['high']:.2f}")
                    analysis_details.append(f"      Price may retrace to fill before continuing down")
                
                if not unfilled_bullish_fvg and not unfilled_bearish_fvg:
                    analysis_details.append("   ⚪ No significant unfilled FVGs detected on Daily")

            # ==================== 3. DRAW ON LIQUIDITY (Old Highs/Lows) ====================
            print("[3] 📊 ICT DRAW ON LIQUIDITY (Price Targets)...")

            if d1_rates is not None and len(d1_rates) >= 10:
                current_price = d1_df.iloc[-1]['close']
                
                # Find significant highs above current price (sell-side liquidity)
                highs_above = []
                lows_below = []
                
                for i in range(len(d1_df) - 1):  # Exclude current day
                    if d1_df.iloc[i]['high'] > current_price:
                        highs_above.append(d1_df.iloc[i]['high'])
                    if d1_df.iloc[i]['low'] < current_price:
                        lows_below.append(d1_df.iloc[i]['low'])
                
                # Nearest liquidity targets
                if highs_above:
                    nearest_high = min(highs_above)
                    distance_to_high = nearest_high - current_price
                    analysis_details.append(f"   🎯 Draw on Liquidity ABOVE: {nearest_high:.2f} ({distance_to_high:.2f} points)")
                    
                    # If price is close to taking liquidity above, bias slightly bearish after
                    if distance_to_high < 50:
                        analysis_details.append(f"      ⚠️ Price near sell-side liquidity - potential reversal zone")
                        bias_scores['bearish'] += 5
                
                if lows_below:
                    nearest_low = max(lows_below)
                    distance_to_low = current_price - nearest_low
                    analysis_details.append(f"   🎯 Draw on Liquidity BELOW: {nearest_low:.2f} ({distance_to_low:.2f} points)")
                    
                    # If price is close to taking liquidity below, bias slightly bullish after
                    if distance_to_low < 50:
                        analysis_details.append(f"      ⚠️ Price near buy-side liquidity - potential reversal zone")
                        bias_scores['bullish'] += 5
                
                # Determine which liquidity pool is more likely target
                if highs_above and lows_below:
                    if min(highs_above) - current_price < current_price - max(lows_below):
                        bias_scores['bullish'] += 8
                        analysis_details.append("   → Price drawn to HIGHER liquidity (bullish bias)")
                    else:
                        bias_scores['bearish'] += 8
                        analysis_details.append("   → Price drawn to LOWER liquidity (bearish bias)")

            # ==================== 4. HIGHER TIMEFRAME CONFIRMATION (H4) ====================
            print("[4] 📊 HIGHER TIMEFRAME TREND CONFIRMATION...")

            h4_rates = mt5.copy_rates_from_pos(mt5_trader.symbol, mt5.TIMEFRAME_H4, 0, 50)
            if h4_rates is not None and len(h4_rates) > 20:
                import pandas as pd
                h4_df = pd.DataFrame(h4_rates)

                # H4 EMAs
                h4_df['ema20'] = h4_df['close'].ewm(span=20, adjust=False).mean()
                h4_df['ema50'] = h4_df['close'].ewm(span=50, adjust=False).mean()

                current_h4 = h4_df.iloc[-1]

                # H4 Trend direction
                if current_h4['close'] > current_h4['ema20'] > current_h4['ema50']:
                    bias_scores['bullish'] += 10
                    analysis_details.append("   ✅ H4: Bullish (Price > EMA20 > EMA50)")
                elif current_h4['close'] < current_h4['ema20'] < current_h4['ema50']:
                    bias_scores['bearish'] += 10
                    analysis_details.append("   ✅ H4: Bearish (Price < EMA20 < EMA50)")
                else:
                    bias_scores['neutral'] += 5
                    analysis_details.append("   ⚠️ H4: Mixed/Consolidating")

            # Get H1 data for additional confirmation
            h1_rates = mt5.copy_rates_from_pos(mt5_trader.symbol, mt5.TIMEFRAME_H1, 0, 100)
            if h1_rates is not None and len(h1_rates) > 50:
                import pandas as pd
                h1_df = pd.DataFrame(h1_rates)

                h1_df['ema50'] = h1_df['close'].ewm(span=50, adjust=False).mean()
                current_h1 = h1_df.iloc[-1]

                if current_h1['close'] > current_h1['ema50']:
                    bias_scores['bullish'] += 5
                    analysis_details.append("   ✅ H1: Price above EMA50")
                else:
                    bias_scores['bearish'] += 5
                    analysis_details.append("   ✅ H1: Price below EMA50")

            # ==================== 5. SESSION ANALYSIS ====================
            print("[5] 📊 SESSION ANALYSIS...")

            utc_now = datetime.now(timezone.utc)
            current_hour_utc = utc_now.hour
            local_hour = datetime.now().hour

            if 0 <= current_hour_utc < 8:
                session = "ASIAN"
                analysis_details.append(f"   📍 Current Session: {session} (Range Building)")
                analysis_details.append(f"      UTC: {utc_now.strftime('%H:%M')} | Local: {local_hour:02d}:{datetime.now().minute:02d} (GMT+3)")
            elif 8 <= current_hour_utc < 13:
                session = "LONDON"
                analysis_details.append(f"   📍 Current Session: {session} (Liquidity Hunt Phase)")
                analysis_details.append(f"      UTC: {utc_now.strftime('%H:%M')} | Local: {local_hour:02d}:{datetime.now().minute:02d} (GMT+3)")
            elif 13 <= current_hour_utc < 16:
                session = "LONDON/NY OVERLAP"
                analysis_details.append(f"   📍 Current Session: {session} (Execution Window)")
                analysis_details.append(f"      UTC: {utc_now.strftime('%H:%M')} | Local: {local_hour:02d}:{datetime.now().minute:02d} (GMT+3)")
            elif 16 <= current_hour_utc < 21:
                session = "NEW YORK"
                analysis_details.append(f"   📍 Current Session: {session} (Expansion Phase)")
                analysis_details.append(f"      UTC: {utc_now.strftime('%H:%M')} | Local: {local_hour:02d}:{datetime.now().minute:02d} (GMT+3)")
            else:
                session = "OFF-HOURS"
                analysis_details.append(f"   📍 Current Session: {session} (Low Liquidity)")
                analysis_details.append(f"      UTC: {utc_now.strftime('%H:%M')} | Local: {local_hour:02d}:{datetime.now().minute:02d} (GMT+3)")

            # ==================== 6. MOMENTUM CONFIRMATION ====================
            print("[6] 📊 MOMENTUM ANALYSIS...")

            if h1_rates is not None and len(h1_rates) > 26:
                # RSI on H1
                delta = h1_df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                h1_df['rsi'] = 100 - (100 / (1 + rs))

                # MACD on H1
                ema12 = h1_df['close'].ewm(span=12, adjust=False).mean()
                ema26 = h1_df['close'].ewm(span=26, adjust=False).mean()
                h1_df['macd'] = ema12 - ema26
                h1_df['macd_signal'] = h1_df['macd'].ewm(span=9, adjust=False).mean()

                current = h1_df.iloc[-1]

                if current['rsi'] > 60:
                    bias_scores['bullish'] += 5
                    analysis_details.append(f"   ✅ H1 RSI: {current['rsi']:.1f} (Bullish momentum)")
                elif current['rsi'] < 40:
                    bias_scores['bearish'] += 5
                    analysis_details.append(f"   ✅ H1 RSI: {current['rsi']:.1f} (Bearish momentum)")
                else:
                    analysis_details.append(f"   ⚠️ H1 RSI: {current['rsi']:.1f} (Neutral)")

                if current['macd'] > current['macd_signal'] and current['macd'] > 0:
                    bias_scores['bullish'] += 5
                    analysis_details.append(f"   ✅ H1 MACD: Bullish")
                elif current['macd'] < current['macd_signal'] and current['macd'] < 0:
                    bias_scores['bearish'] += 5
                    analysis_details.append(f"   ✅ H1 MACD: Bearish")

            # ==================== CALCULATE FINAL BIAS ====================
            print("\n" + "-"*50)

            total_score = bias_scores['bullish'] + bias_scores['bearish'] + bias_scores['neutral']

            bullish_pct = (bias_scores['bullish'] / total_score * 100) if total_score > 0 else 0
            bearish_pct = (bias_scores['bearish'] / total_score * 100) if total_score > 0 else 0
            neutral_pct = (bias_scores['neutral'] / total_score * 100) if total_score > 0 else 0

            # Determine bias
            if bullish_pct > bearish_pct + 15:
                self.daily_bias = "BULLISH"
                self.bias_confidence = int(bullish_pct)
            elif bearish_pct > bullish_pct + 15:
                self.daily_bias = "BEARISH"
                self.bias_confidence = int(bearish_pct)
            else:
                self.daily_bias = "NEUTRAL"
                self.bias_confidence = max(int(bullish_pct), int(bearish_pct))

            self.last_bias_update = datetime.now()

            # Print analysis details
            print("\n📋 ICT ANALYSIS DETAILS:")
            for detail in analysis_details:
                print(detail)

            # Print summary
            print("\n" + "="*70)
            print(f"[ICT] BIAS SCORES:")
            print(f"   [BULL] BULLISH: {bias_scores['bullish']} points ({bullish_pct:.1f}%)")
            print(f"   [BEAR] BEARISH: {bias_scores['bearish']} points ({bearish_pct:.1f}%)")
            print(f"   [NEUT] NEUTRAL: {bias_scores['neutral']} points ({neutral_pct:.1f}%)")
            print("-"*50)

            if self.daily_bias == "BULLISH":
                print(f"[ICT] DAILY BIAS: [BULL] {self.daily_bias} (Confidence: {self.bias_confidence}%)")
                print("   -> Daily Order Flow BULLISH - Look for BUY setups")
                print("   -> Price seeking liquidity above old highs")
            elif self.daily_bias == "BEARISH":
                print(f"[ICT] DAILY BIAS: [BEAR] {self.daily_bias} (Confidence: {self.bias_confidence}%)")
                print("   -> Daily Order Flow BEARISH - Look for SELL setups")
                print("   -> Price seeking liquidity below old lows")
            else:
                print(f"[ICT] DAILY BIAS: [NEUT] {self.daily_bias} (Confidence: {self.bias_confidence}%)")
                print("   -> No clear order flow - Wait for structure break")
                print("   -> Monitor for liquidity sweep to reveal intent")

            print("="*70 + "\n")

            return {
                'bias': self.daily_bias,
                'confidence': self.bias_confidence,
                'scores': bias_scores,
                'updated': self.last_bias_update
            }

        except Exception as e:
            print(f"[WARNING] Error analyzing daily bias: {e}")
            import traceback
            traceback.print_exc()
            self.daily_bias = "NEUTRAL"
            self.bias_confidence = 50
            return {'bias': 'NEUTRAL', 'confidence': 50, 'scores': {}, 'updated': None}

    def run_mt5_live(self):
        """Run bot in MT5 live trading mode with M30 scalping strategy"""
        if not MT5_AVAILABLE:
            print("[ERROR] MT5 module not available. Install: pip install MetaTrader5")
            return

        print("\n" + "="*80)
        print("[BOT] XAUUSD M30 SCALPING BOT - MT5 LIVE TRADING MODE")
        print("      + ICT Smart Money Analysis Module")
        print("="*80)

        # Initialize MT5 trader
        mt5_trader = MT5Trader(self.config.get('mt5_config', 'mt5_config.json'))

        if not mt5_trader.connect():
            print("[ERROR] Failed to connect to MT5")
            return

        # ====== DAILY BIAS ANALYSIS AT STARTUP ======
        bias_result = self.analyze_daily_bias(mt5_trader)

        print(f"[TARGET] Trading Mode: {'🟢 LONG' if self.config['enable_long'] else ''} {'🔴 SHORT' if self.config['enable_short'] else ''}")
        print(f"[CHART] Daily Bias: {self.daily_bias} (Confidence: {self.bias_confidence}%)")
        print(f"[TIMER]  Check Interval: {self.config['mt5_check_interval']} seconds")
        print(f"[SHIELD]  Risk Per Trade: {self.config['risk_percent']*100:.2f}%")
        print(f"[STATS] Max Open Positions: {mt5_trader.max_open_positions}")
        print(f"[UP] Max Daily Trades: {mt5_trader.max_daily_trades}")
        
        # Print chart visualization legend
        self.chart_visualizer.print_legend()
        
        print("\n[ROCKET] Bot is now running... Press Ctrl+C to stop")
        print("="*80 + "\n")

        try:
            last_bar_time = None
            last_bias_check = datetime.now()
            last_ict_status_print = datetime.now()
            last_confidence_log_save = datetime.now()

            while True:
                # ====== RE-ANALYZE BIAS EVERY 4 HOURS OR ON NEW DAY ======
                current_time = datetime.now()
                hours_since_bias = (current_time - last_bias_check).total_seconds() / 3600

                if hours_since_bias >= 4 or (self.last_bias_update and
                    current_time.date() != self.last_bias_update.date()):
                    print("\n[UPDATE] Re-analyzing daily bias (4-hour update)...")
                    self.analyze_daily_bias(mt5_trader)
                    last_bias_check = current_time

                # Get current market data
                df = mt5_trader.get_historical_data(bars=self.config['mt5_warmup_bars'])

                if df is None or len(df) < 100:
                    print("[WARNING]  Insufficient data, retrying...")
                    time.sleep(self.config['mt5_check_interval'])
                    continue

                # Track new bars for ICT analysis updates
                current_bar_time = df.iloc[-1]['time']
                is_new_bar = (last_bar_time != current_bar_time)
                
                if is_new_bar:
                    last_bar_time = current_bar_time

                # ====== ICT ANALYSIS (on new bars only) ======
                utc_now = datetime.now(timezone.utc)
                utc_hour = utc_now.hour
                current_date = utc_now.date()
                
                if is_new_bar:
                    ict_analysis = self.ict_analyzer.analyze(df, utc_hour, current_date)
                    
# ====== CHART VISUALS DISABLED (MT5 Python API limitation) ======
                # Chart object drawing not supported in MT5 Python API
                # ICT analysis is logged to console instead
                
                # Print ICT status every 30 minutes
                if (current_time - last_ict_status_print).total_seconds() >= 1800:
                    self.ict_analyzer.print_status()
                    self.chart_visualizer.print_legend()  # Show legend periodically
                    last_ict_status_print = current_time

                # Save confidence log every hour
                if (current_time - last_confidence_log_save).total_seconds() >= 3600:
                    log_path = 'logs/confidence_log.json'
                    trades_logged = self.ict_analyzer.save_confidence_log(log_path)
                    print(f"\n[LOG] Saved confidence log: {trades_logged} trades logged to {log_path}")
                    last_confidence_log_save = current_time

                # Log market status with bias and ICT phase
                current_price = df.iloc[-1]['close']
                bias_icon = "🟢" if self.daily_bias == "BULLISH" else ("🔴" if self.daily_bias == "BEARISH" else "⚪")
                ict_session = ict_analysis['session']
                ict_phase = ict_analysis['market_phase']
                
                print(f"\n[TIMER] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Price: {current_price:.2f} | Bias: {bias_icon} {self.daily_bias}")
                print(f"   ICT: {ict_session} Session | Phase: {ict_phase} | Intent: {ict_analysis['intent'] or 'None'}")
                
                # Print ICT reasoning
                for reason in ict_analysis['reasoning']:
                    print(f"   {reason}")

                # Calculate indicators and check for signals (pass bias info)
                signal = self._check_trading_signals(df, mt5_trader)

                if not signal:
                    print(f"   No signal detected. Waiting for next bar...")

                if signal:
                    signal_type = signal['type']
                    entry_price = signal['entry_price']
                    stop_loss = signal['stop_loss']
                    take_profit = signal['take_profit']

                    # ====== ICT TRADE CONTEXT (ADVISORY ONLY - NEVER BLOCKS) ======
                    ict_allowed, ict_reason, ict_confidence, strategy_type, priority = self.ict_analyzer.get_ict_trade_filter(
                        signal_type, entry_price
                    )

                    # ICT provides CONTEXT and CONFIDENCE, never blocks
                    confidence_emoji = "🟢" if ict_confidence >= 0.7 else ("🟡" if ict_confidence >= 0.5 else "🟠")
                    priority_emoji = "⚠️" if priority == "LOW" else "✅"
                    print(f"\n[ICT CONTEXT] {confidence_emoji} {priority_emoji} {ict_reason}")

                    # Adjust TP to ICT target if available
                    if ict_analysis['targets']:
                        if signal_type == 'BUY':
                            ict_target = min(ict_analysis['targets'])  # Nearest target for buys
                        else:
                            ict_target = max(ict_analysis['targets'])  # Nearest target for sells

                        # Use ICT target if it provides better R:R
                        current_rr = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
                        ict_rr = abs(ict_target - entry_price) / abs(entry_price - stop_loss)

                        if ict_rr > current_rr and ict_rr <= 5:  # Cap at 5:1 R:R
                            print(f"   [ICT] Adjusting TP to liquidity target: {ict_target:.2f} (R:R {ict_rr:.1f})")
                            take_profit = ict_target

                    # Calculate position size with ICT confidence scaling
                    base_volume = mt5_trader.calculate_position_size(entry_price, stop_loss)

                    # Apply confidence-based sizing (Quick Win #2)
                    if self.config.get('use_confidence_sizing', False):
                        min_mult = self.config.get('confidence_min_multiplier', 0.5)
                        max_mult = self.config.get('confidence_max_multiplier', 1.3)

                        # Scale from min to max based on confidence (0.2-1.0 → min-max)
                        confidence_range = 1.0 - 0.2  # 0.8 range
                        adjusted_confidence = max(0.2, min(1.0, ict_confidence))
                        normalized_conf = (adjusted_confidence - 0.2) / confidence_range

                        confidence_multiplier = min_mult + (normalized_conf * (max_mult - min_mult))
                        volume = base_volume * confidence_multiplier

                        print(f"\n[TARGET] SIGNAL DETECTED: {signal_type}")
                        print(f"   Entry: {entry_price}")
                        print(f"   SL: {stop_loss} ({abs(entry_price-stop_loss):.2f} points)")
                        print(f"   TP: {take_profit} ({abs(take_profit-entry_price):.2f} points)")
                        print(f"   Base Volume: {base_volume:.2f} lots")
                        print(f"   Confidence Multiplier: {confidence_multiplier:.2f}x")
                        print(f"   Adjusted Volume: {volume:.2f} lots")
                    else:
                        volume = base_volume
                        print(f"\n[TARGET] SIGNAL DETECTED: {signal_type}")
                        print(f"   Entry: {entry_price}")
                        print(f"   SL: {stop_loss} ({abs(entry_price-stop_loss):.2f} points)")
                        print(f"   TP: {take_profit} ({abs(take_profit-entry_price):.2f} points)")
                        print(f"   Volume: {volume:.2f} lots")

                    # Log trade entry for empirical analysis
                    trade_log_index = self.ict_analyzer.log_trade_entry(
                        signal_type, entry_price, stop_loss, take_profit,
                        ict_confidence, strategy_type, priority
                    )
                    # Store session info
                    self.ict_analyzer.confidence_log[trade_log_index]['session'] = ict_analysis['session']

                    # Execute trade
                    result = mt5_trader.open_position(
                        order_type=signal_type,
                        volume=volume,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        comment=f"XAUUSD_M30_{signal_type}"
                    )

                    if result:
                        print(f"[OK] Trade executed successfully!")
                    else:
                        print(f"[ERROR] Trade execution failed")

                # Monitor break-even trailing stops (moves SL to entry at 50% to TP)
                mt5_trader.monitor_breakeven_trailing()

                # Monitor open positions
                positions = mt5_trader.get_open_positions()
                if positions:
                    total_profit = sum(p['profit'] for p in positions)
                    print(f"\n[STATS] Open Positions: {len(positions)} | Total P&L: ${total_profit:+.2f}")

                # Sleep until next check
                time.sleep(self.config['mt5_check_interval'])

        except KeyboardInterrupt:
            print("\n\n[STOP]  Stopping bot...")

            # Display final status
            status = mt5_trader.get_trading_status()
            print("\n" + "="*60)
            print("[STATS] FINAL TRADING STATUS")
            print("="*60)
            print(f"Open Positions: {status['open_positions']}")
            print(f"Daily Trades: {status['daily_trades']}")
            if status['account']:
                print(f"Balance: ${status['account']['balance']:,.2f}")
                print(f"Equity: ${status['account']['equity']:,.2f}")
                print(f"Profit: ${status['account']['profit']:+,.2f}")
            print("="*60)

            mt5_trader.disconnect()
            print("\n[OK] Bot stopped safely")

    def _check_trading_signals(self, df, mt5_trader):
        """Check for trading signals - M30 SCALPING with RSI, MACD, Volume, Alligator, EMA, Stochastic, Bollinger Bands
           Incorporates Daily Bias for trade filtering and confidence adjustment
        """

        # ====== DAILY BIAS INTEGRATION ======
        # Adjust required signal count based on bias alignment
        base_signal_requirement = 4  # Default: need 4/6 signals

        # If trading with the bias, reduce requirement (easier entry)
        # If trading against the bias, increase requirement (harder entry)
        long_signal_requirement = base_signal_requirement
        short_signal_requirement = base_signal_requirement

        if self.daily_bias == "BULLISH":
            long_signal_requirement = 3  # Easier LONG entries with bullish bias
            short_signal_requirement = 5  # Harder SHORT entries against bias
        elif self.daily_bias == "BEARISH":
            long_signal_requirement = 5  # Harder LONG entries against bias
            short_signal_requirement = 3  # Easier SHORT entries with bearish bias

        # Calculate Fast EMAs for scalping (5, 8, 13)
        df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
        df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()

        # Calculate ATR for dynamic SL/TP
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        # Calculate RSI (9 period - more sensitive for scalping)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=9).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=9).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Calculate Stochastic Oscillator (14, 3, 3)
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

        # Calculate Bollinger Bands (20, 2)
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # Calculate MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Calculate Volume Average (20 period)
        if 'tick_volume' in df.columns:
            df['volume_avg'] = df['tick_volume'].rolling(window=20).mean()
        else:
            df['volume_avg'] = 0

        # Calculate Alligator (13, 8, 5) - Bill Williams
        df['jaw'] = df['close'].shift(8).rolling(window=13).mean()    # Blue - Jaw
        df['teeth'] = df['close'].shift(5).rolling(window=8).mean()   # Red - Teeth
        df['lips'] = df['close'].shift(3).rolling(window=5).mean()    # Green - Lips

        # Get latest values
        current = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        # Check for LONG signal (SCALP BUY)
        if self.config['enable_long']:
            # 1. EMA Alignment: Fast EMAs trending up (5 > 8 > 13)
            ema_bullish = current['ema5'] > current['ema8'] > current['ema13']
            ema_crossover = (current['ema5'] > current['ema8']) and (prev['ema5'] <= prev['ema8'])

            # 2. RSI oversold recovery (20-50 range for scalping)
            rsi_bullish = 20 < current['rsi'] < 60 and current['rsi'] > prev['rsi']

            # 3. Stochastic Oscillator oversold crossover
            stoch_bullish = (current['stoch_k'] > current['stoch_d']) and (current['stoch_k'] < 80)
            stoch_oversold = current['stoch_k'] < 30 and current['stoch_k'] > prev['stoch_k']

            # 4. MACD bullish
            macd_bullish = current['macd'] > current['macd_signal'] and current['macd_hist'] > 0
            macd_crossover = (current['macd'] > current['macd_signal']) and (prev['macd'] <= prev['macd_signal'])

            # 5. Bollinger Bands - Price near lower band (reversal) or breakout above middle
            bb_reversal = current['close'] < current['bb_middle'] and current['close'] > current['bb_lower']
            bb_momentum = current['close'] > current['bb_middle'] and prev['close'] <= prev['bb_middle']

            # 6. Alligator trending up (Lips > Teeth > Jaw)
            alligator_bullish = current['lips'] > current['teeth'] > current['jaw']

            # 7. Volume confirmation (above average)
            volume_ok = True
            if 'tick_volume' in df.columns and current['volume_avg'] > 0:
                volume_ok = current['tick_volume'] > current['volume_avg'] * 1.1

            # Multi-indicator confirmation (bias-adjusted requirement)
            signals = [
                ema_bullish or ema_crossover,
                rsi_bullish,
                stoch_bullish or stoch_oversold,
                macd_bullish or macd_crossover,
                bb_reversal or bb_momentum,
                alligator_bullish
            ]

            bullish_count = sum(signals)

            # Use bias-adjusted signal requirement
            if bullish_count >= long_signal_requirement and volume_ok:
                entry_price = current['close']
                atr = current['atr']

                # Adjust TP based on bias alignment
                sl_multiplier = 0.9
                if self.daily_bias == "BULLISH":
                    tp_multiplier = 1.8  # Larger target with bias
                elif self.daily_bias == "BEARISH":
                    tp_multiplier = 1.2  # Smaller target against bias
                else:
                    tp_multiplier = 1.5

                stop_loss = entry_price - (atr * sl_multiplier)
                take_profit = entry_price + (atr * tp_multiplier)

                bias_align = "WITH BIAS" if self.daily_bias == "BULLISH" else ("AGAINST BIAS" if self.daily_bias == "BEARISH" else "")
                print(f"   [LONG SCALP] RSI: {current['rsi']:.1f} | Stoch: {current['stoch_k']:.1f} | MACD: {current['macd']:.2f}")
                print(f"   EMA5: {current['ema5']:.2f} | BB: {current['bb_middle']:.2f} | Signals: {bullish_count}/6 (need {long_signal_requirement}) {bias_align}")

                return {
                    'type': 'BUY',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'atr': atr
                }

        # Check for SHORT signal (SCALP SELL)
        if self.config['enable_short']:
            # 1. EMA Alignment: Fast EMAs trending down (5 < 8 < 13)
            ema_bearish = current['ema5'] < current['ema8'] < current['ema13']
            ema_crossover = (current['ema5'] < current['ema8']) and (prev['ema5'] >= prev['ema8'])

            # 2. RSI overbought reversal (40-80 range for scalping)
            rsi_bearish = 40 < current['rsi'] < 80 and current['rsi'] < prev['rsi']

            # 3. Stochastic Oscillator overbought crossover
            stoch_bearish = (current['stoch_k'] < current['stoch_d']) and (current['stoch_k'] > 20)
            stoch_overbought = current['stoch_k'] > 70 and current['stoch_k'] < prev['stoch_k']

            # 4. MACD bearish
            macd_bearish = current['macd'] < current['macd_signal'] and current['macd_hist'] < 0
            macd_crossover = (current['macd'] < current['macd_signal']) and (prev['macd'] >= prev['macd_signal'])

            # 5. Bollinger Bands - Price near upper band (reversal) or breakout below middle
            bb_reversal = current['close'] > current['bb_middle'] and current['close'] < current['bb_upper']
            bb_momentum = current['close'] < current['bb_middle'] and prev['close'] >= prev['bb_middle']

            # 6. Alligator trending down (Lips < Teeth < Jaw)
            alligator_bearish = current['lips'] < current['teeth'] < current['jaw']

            # 7. Volume confirmation (above average)
            volume_ok = True
            if 'tick_volume' in df.columns and current['volume_avg'] > 0:
                volume_ok = current['tick_volume'] > current['volume_avg'] * 1.1

            # Multi-indicator confirmation (bias-adjusted requirement)
            signals = [
                ema_bearish or ema_crossover,
                rsi_bearish,
                stoch_bearish or stoch_overbought,
                macd_bearish or macd_crossover,
                bb_reversal or bb_momentum,
                alligator_bearish
            ]

            bearish_count = sum(signals)

            # Use bias-adjusted signal requirement
            if bearish_count >= short_signal_requirement and volume_ok:
                entry_price = current['close']
                atr = current['atr']

                # Adjust TP based on bias alignment
                sl_multiplier = 0.9
                if self.daily_bias == "BEARISH":
                    tp_multiplier = 1.8  # Larger target with bias
                elif self.daily_bias == "BULLISH":
                    tp_multiplier = 1.2  # Smaller target against bias
                else:
                    tp_multiplier = 1.5

                stop_loss = entry_price + (atr * sl_multiplier)
                take_profit = entry_price - (atr * tp_multiplier)

                bias_align = "WITH BIAS" if self.daily_bias == "BEARISH" else ("AGAINST BIAS" if self.daily_bias == "BULLISH" else "")
                print(f"   [SHORT SCALP] RSI: {current['rsi']:.1f} | Stoch: {current['stoch_k']:.1f} | MACD: {current['macd']:.2f}")
                print(f"   EMA5: {current['ema5']:.2f} | BB: {current['bb_middle']:.2f} | Signals: {bearish_count}/6 (need {short_signal_requirement}) {bias_align}")

                return {
                    'type': 'SELL',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'atr': atr
                }

        return None


# ===============================================================================
# COMMAND LINE INTERFACE
# ===============================================================================

def main():
    """Main entry point with CLI arguments"""
    parser = argparse.ArgumentParser(
        description='XAUUSD M30 Trading Bot - Advanced Gold Trading System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python xauusd_trading_bot.py --mode backtest
  python xauusd_trading_bot.py --mode quick
  python xauusd_trading_bot.py --from 2024-01-01 --to 2024-12-31
  python xauusd_trading_bot.py --long-only
  python xauusd_trading_bot.py --short-only --no-plot
        """
    )

    parser.add_argument('--mode', choices=['backtest', 'quick', 'mt5'],
                       default='backtest',
                       help='Trading mode (backtest=full test, quick=30days, mt5=live trading)')

    parser.add_argument('--from', dest='from_date',
                       help='Start date (YYYY-MM-DD)')

    parser.add_argument('--to', dest='to_date',
                       help='End date (YYYY-MM-DD)')

    parser.add_argument('--long-only', action='store_true',
                       help='Enable only LONG trades')

    parser.add_argument('--short-only', action='store_true',
                       help='Enable only SHORT trades')

    parser.add_argument('--no-plot', action='store_true',
                       help='Disable chart plotting')

    parser.add_argument('--cash', type=float,
                       help='Starting capital (default: 100000)')

    parser.add_argument('--risk', type=float,
                       help='Risk per trade as decimal (default: 0.0125 = 1.25%%)')

    parser.add_argument('--debug', action='store_true',
                       help='Enable verbose debug output')

    args = parser.parse_args()

    # Copy default config
    config = CONFIG.copy()

    # Apply mode presets
    if args.mode == 'quick':
        # Quick 30-day test
        to_date = datetime.strptime(config['to_date'], '%Y-%m-%d')
        from_date = to_date - timedelta(days=30)
        config['from_date'] = from_date.strftime('%Y-%m-%d')
        print(f"⚡ Quick mode: Testing last 30 days")

    elif args.mode == 'mt5':
        # MT5 live trading mode
        print("[RED] MT5 LIVE TRADING MODE")
        print("[WARNING]  WARNING: This will execute REAL trades on your MT5 account!")

        if not MT5_AVAILABLE:
            print("[ERROR] MetaTrader5 module not installed")
            print("Install it with: pip install MetaTrader5")
            return

        # Create and run bot in MT5 mode
        bot = XAUUSDTradingBot(config)
        bot.run_mt5_live()
        return

    # Apply custom dates
    if args.from_date:
        config['from_date'] = args.from_date
    if args.to_date:
        config['to_date'] = args.to_date

    # Apply trading direction
    if args.long_only:
        config['enable_long'] = True
        config['enable_short'] = False
    elif args.short_only:
        config['enable_long'] = False
        config['enable_short'] = True

    # Apply other options
    if args.no_plot:
        config['enable_plot'] = False
    if args.cash:
        config['starting_cash'] = args.cash
    if args.risk:
        config['risk_percent'] = args.risk
    if args.debug:
        config['verbose_debug'] = True

    # Create and run bot in backtest mode
    bot = XAUUSDTradingBot(config)
    bot.run()


if __name__ == '__main__':
    main()
