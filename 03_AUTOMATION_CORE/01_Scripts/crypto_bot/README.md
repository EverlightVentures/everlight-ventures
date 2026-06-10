# Hybrid Crypto Trading Bot

A multi-strategy trading bot for Coinbase combining Grid, DCA, Scalping, and Signal-based trading.

## Quick Start

```bash
# 1. Test connection (no API key needed)
./run.sh test

# 2. Check current price
./run.sh price BTC-USD

# 3. Dry run (no trades)
./run.sh dry-run

# 4. Start bot (after configuring API)
./run.sh start
```

## Setup

### 1. Install Dependencies
```bash
pip install requests
```

### 2. Get Coinbase API Keys
1. Go to [Coinbase Advanced](https://www.coinbase.com/settings/api)
2. Create new API key
3. Enable **Trade** and **View** permissions
4. Save the API key and secret

### 3. Configure
Edit `config.json`:
```json
{
  "exchange": {
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "sandbox": true  // Set false for real trading
  }
}
```

### 4. (Optional) Telegram Alerts
1. Create bot via [@BotFather](https://t.me/botfather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Add to config:
```json
"notifications": {
  "enabled": true,
  "telegram_bot_token": "123456:ABC-DEF...",
  "telegram_chat_id": "your_chat_id"
}
```

## Strategies

### Grid Trading
- Places buy/sell orders at price intervals
- Profits from sideways movement
- Config: `grid_levels`, `grid_spacing_percent`, `order_size`

### DCA (Dollar Cost Average)
- Regular scheduled buys
- Extra buys on dips
- Config: `buy_amount_usd`, `dip_threshold_percent`, `interval_hours`

### Scalping
- Quick trades on momentum/volume
- Small profit targets, tight stops
- Config: `profit_target_percent`, `max_hold_minutes`

### Signal-Based
- RSI overbought/oversold
- MACD crossovers
- EMA crosses
- Config: `rsi_oversold`, `rsi_overbought`, `ema_cross`

## Risk Management

| Setting | Description |
|---------|-------------|
| `max_drawdown_percent` | Stop trading at X% loss from peak |
| `daily_loss_limit_usd` | Max loss per day |
| `max_daily_trades` | Trade limit per day |
| `stop_loss_percent` | Per-trade stop loss |
| `emergency_stop` | Kill switch |

## File Structure
```
crypto_bot/
├── bot.py              # Main bot
├── config.json         # Settings
├── run.sh              # Runner script
├── strategies/
│   ├── grid_strategy.py
│   ├── dca_strategy.py
│   ├── scalp_strategy.py
│   └── signal_strategy.py
├── utils/
│   ├── coinbase_api.py
│   ├── risk_manager.py
│   └── notifier.py
└── logs/               # Trade logs
```

## Usage Examples

```bash
# Run with custom interval (30 seconds)
python3 bot.py --interval 30

# Check status
./run.sh status

# Get ETH price
./run.sh price ETH-USD
```

## Safety Notes

1. **Start with sandbox mode** (`"sandbox": true`)
2. **Test with small amounts first**
3. **Never risk more than you can lose**
4. **Monitor the bot regularly**
5. **Use the emergency stop if needed**

## Logs

Logs are saved to `logs/bot_YYYYMMDD.log`

View live:
```bash
tail -f logs/bot_*.log
```

---
*Use at your own risk. This is not financial advice.*
