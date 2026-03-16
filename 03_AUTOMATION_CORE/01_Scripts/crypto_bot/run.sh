#!/bin/bash
# Crypto Bot Runner

BOT_DIR="$(dirname "$0")"
cd "$BOT_DIR"

case "$1" in
    start)
        echo "Starting Hybrid Trading Bot..."
        python3 bot.py --interval 10
        ;;
    dry-run)
        echo "Running in dry-run mode..."
        python3 bot.py --dry-run
        ;;
    test)
        echo "Testing API connection..."
        python3 -c "
from utils.coinbase_api import CoinbaseAPI
api = CoinbaseAPI('test', 'test', sandbox=True)
print('Testing prices...')
for pair in ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD']:
    price = api.get_current_price(pair)
    print(f'  {pair}: \${price:,.2f}' if price else f'  {pair}: Failed')
print('API connection OK!')
"
        ;;
    price)
        PAIR="${2:-BTC-USD}"
        python3 -c "
from utils.coinbase_api import CoinbaseAPI
api = CoinbaseAPI('test', 'test', sandbox=True)
price = api.get_current_price('$PAIR')
print(f'$PAIR: \${price:,.2f}' if price else 'Failed')
"
        ;;
    backtest)
        PAIR="${2:-BTC-USD}"
        DAYS="${3:-14}"
        echo "Running backtest on $PAIR for $DAYS days..."
        python3 backtester.py --pair "$PAIR" --days "$DAYS" --leverage 4 --balance 1000
        ;;
    optimize)
        echo "Running strategy optimizer..."
        python3 optimizer.py
        ;;
    simulate)
        echo "Running Monte Carlo simulation..."
        python3 backtester.py --simulate --leverage 4 --balance 2000
        ;;
    perp|account)
        echo "Checking Coinbase Advanced Account..."
        python3 -c "
import json
from utils.coinbase_api import CoinbaseAPI

with open('config.json') as f:
    config = json.load(f)

api = CoinbaseAPI(
    config['exchange']['api_key'],
    config['exchange']['api_secret'],
    sandbox=config['exchange'].get('sandbox', False)
)

print()
print('═' * 50)
print('  COINBASE ADVANCED ACCOUNT')
print('═' * 50)

# Get accounts/balances
accounts = api.get_accounts()
if accounts:
    print('  BALANCES:')
    total_usd = 0
    for acc in accounts:
        balance = float(acc.get('available_balance', {}).get('value', 0))
        hold = float(acc.get('hold', {}).get('value', 0))
        currency = acc.get('currency', '?')
        if balance > 0 or hold > 0:
            if currency == 'USD':
                total_usd = balance
                print(f'  • USD: \${balance:,.2f} (hold: \${hold:,.2f})')
            else:
                # Get USD value
                price = api.get_current_price(f'{currency}-USD')
                if price and balance > 0:
                    usd_val = balance * price
                    total_usd += usd_val
                    print(f'  • {currency}: {balance:.6f} (~\${usd_val:,.2f})')
    print(f'  ─────────────────────')
    print(f'  Total: ~\${total_usd:,.2f}')
    print()
else:
    print('  Could not fetch accounts')
    print('  Check API key permissions')
    print()

# Check for futures/perp availability
print('  FUTURES STATUS:')
portfolio = api.get_perpetuals_portfolio()
if portfolio:
    print(f'  ✓ Perpetuals enabled')
    print(f'  Collateral: \${float(portfolio.get(\"collateral\", 0)):,.2f}')
else:
    print('  ✗ Perpetuals not available or not enabled')
    print('  (This is normal for most US accounts)')
    print()
    print('  For leverage, the bot will use:')
    print('  • Position sizing (trade larger amounts)')
    print('  • Tight stop losses to manage risk')
    print('  • The 4x leverage setting controls position size')

print()

# Current prices
print('  TRADING PAIRS:')
for pair in ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD']:
    price = api.get_current_price(pair)
    if price:
        print(f'  • {pair}: \${price:,.2f}')

print('═' * 50)
"
        ;;
    swing)
        echo "Weekly Swing Trading Stats..."
        python3 -c "
import json
from strategies.swing_filter import SwingFilter

with open('config.json') as f:
    config = json.load(f)

sf = SwingFilter(config)
stats = sf.get_weekly_stats()

print()
print('═' * 50)
print('  SWING TRADING STATUS')
print('═' * 50)
print(f'  Week Started:    {stats[\"week_start\"][:10]}')
print(f'  Trades This Week: {stats[\"trades_count\"]} / {stats[\"max_trades\"]}')
print(f'  Trades Remaining: {stats[\"trades_remaining\"]}')
print(f'  Total Volume:     \${stats[\"total_volume\"]:,.0f}')
print()

strat = config['strategy']
print('  SETTINGS:')
print(f'  • Leverage:       {strat.get(\"leverage\", 4)}x')
print(f'  • Min Move:       {strat.get(\"min_move_percent\", 3)}%')
print(f'  • Swing Threshold: {strat.get(\"swing_threshold_percent\", 5)}%')
print(f'  • Lot Size:       \${strat.get(\"lot_size_usd\", 500)}')
print(f'  • Stop Loss:      {strat.get(\"stop_loss_percent\", 2)}%')
print(f'  • Take Profit:    {strat.get(\"take_profit_percent\", 6)}%')
print()

mp = config.get('margin_protection', {})
if mp.get('enabled'):
    print('  MARGIN PROTECTION:')
    print(f'  • Auto-add at:    {mp.get(\"auto_add_margin_at_percent\", 50)}% usage')
    print(f'  • Topup Amount:   \${mp.get(\"margin_topup_usd\", 100)}')
    print(f'  • Max Topups:     {mp.get(\"max_topups_per_position\", 3)}')
    print()

if stats['trades']:
    print('  RECENT TRADES:')
    for t in stats['trades'][-5:]:
        print(f'  • {t[\"time\"]} | {t[\"pair\"]} {t[\"side\"].upper()} | {t[\"size\"]}')

print('═' * 50)
"
        ;;
    mtf)
        PAIR="${2:-BTC-USD}"
        echo "Testing MTF Strategy on $PAIR..."
        python3 -c "
import json
from strategies.mtf_strategy import MTFStrategy
from utils.coinbase_api import CoinbaseAPI

# Load config
with open('config.json') as f:
    config = json.load(f)

api = CoinbaseAPI(
    config['exchange']['api_key'],
    config['exchange']['api_secret'],
    sandbox=config['exchange']['sandbox']
)

strategy = MTFStrategy(api, config['strategy'], '$PAIR')

# Get current price
price = api.get_current_price('$PAIR')
if price:
    print(f'\n📊 {chr(36)}PAIR @ \${price:,.2f}')
    print('─' * 50)

    # Analyze
    result = strategy.analyze({'price': price})

    # Show status
    status = strategy.get_status()
    print(f'Data Points: {status[\"data_points\"]}')
    print(f'Yearly Range: {status[\"yearly_range\"]}')
    print(f'Monthly Range: {status[\"monthly_range\"]}')
    print(f'Weekly Range: {status[\"weekly_range\"]}')
    print(f'EMA Alignment: {status[\"ema_alignment\"]}')
    print(f'RSI: {status[\"rsi\"]}')
    print(f'Nearest Level: {status[\"nearest_level\"]}')
    print('─' * 50)

    # Show key levels
    levels = strategy.get_key_levels()
    if levels:
        print('Key Levels:')
        for lvl in levels:
            marker = '🔴' if lvl['type'] == 'high' else '🟢'
            print(f'  {marker} {lvl[\"timeframe\"].capitalize()} {lvl[\"type\"]}: \${lvl[\"price\"]:,.0f}')

    print('─' * 50)
    print(f'Signal: {result[\"action\"].upper()}')
    print(f'Reason: {result[\"reason\"]}')
else:
    print('Failed to get price')
"
        ;;
    dashboard)
        echo "Starting Streamlit dashboard..."
        echo "Open http://localhost:8501 in your browser"
        streamlit run dashboard.py --server.port 8501 --server.headless true
        ;;
    install)
        echo "Installing dependencies..."
        pip install -r requirements.txt
        ;;
    status)
        echo "=== Bot Status ==="
        echo ""
        echo "Recent logs:"
        tail -30 logs/bot_*.log 2>/dev/null || echo "No logs found"
        ;;
    *)
        echo "Crypto Trading Bot"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  start           Start the trading bot"
        echo "  dry-run         Test without executing trades"
        echo "  test            Test API connection"
        echo "  price [PAIR]    Get current price (default: BTC-USD)"
        echo "  mtf [PAIR]      Test MTF strategy with key levels + Fibonacci"
        echo "  swing           Show weekly swing trading stats & settings"
        echo "  perp            Check perpetuals portfolio & positions"
        echo "  backtest [PAIR] [DAYS]  Run backtest"
        echo "  optimize        Find optimal parameters"
        echo "  simulate        Run Monte Carlo simulation"
        echo "  dashboard       Start Streamlit web dashboard"
        echo "  install         Install Python dependencies"
        echo "  status          Show recent logs"
        echo ""
        echo "Examples:"
        echo "  $0 test"
        echo "  $0 price ETH-USD"
        echo "  $0 backtest SOL-USD 30"
        echo "  $0 dashboard"
        ;;
esac
