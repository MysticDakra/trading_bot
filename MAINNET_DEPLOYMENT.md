# ⚠️ MAINNET DEPLOYMENT GUIDE

## Critical Pre-Deployment Reality Check

**You asked: "Are you sure there are no errors and it'll work?"**

### Honest Answer:

❌ **NO, I cannot guarantee it will work on mainnet without errors.**

Here's the reality:

1. **Code is untested** - Written from documentation, not tested against live Hyperliquid API
2. **Dependencies not installed** - System cannot run without pip install
3. **Database not set up** - PostgreSQL tables don't exist
4. **No live verification** - Haven't executed a single real trade
5. **Potential API mismatches** - Hyperliquid API may differ from documentation

### What WILL Happen If You Deploy Now:

```
🔴 System crashes immediately (missing dependencies)
🔴 API calls fail (incorrect request format)
🔴 Orders rejected (leverage/size/format issues)
🔴 Possible capital loss (bugs in position sizing)
```

## Recommended Safe Path to Mainnet

### Phase 1: Local Setup & Testing (1-2 hours)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your REAL API keys

# 3. Test imports
python -c "from src.core.trading_system import TradingSystem; print('✓ Imports work')"

# 4. Run unit tests
pytest tests/ -v
```

**If any of these fail → FIX BEFORE CONTINUING**

### Phase 2: Paper Trading Verification (2-4 hours)

```bash
# Set paper trading mode in .env
ENABLE_PAPER_TRADING=true
ACTIVE_CAPITAL=150  # Start with Week 1 amount

# Run system
python -m src.core.trading_system
```

**Watch for:**
- ✅ WebSocket connects successfully
- ✅ Order book data streams correctly
- ✅ DeepSeek API calls work
- ✅ No crashes for 1 hour minimum
- ❌ Any errors → STOP and fix

### Phase 3: Micro-Capital Live Test ($100-500)

```bash
# Update .env for MAINNET with MINIMAL capital
ENABLE_PAPER_TRADING=false
ACTIVE_CAPITAL=100  # Start with $100 only
MAX_DAILY_LOSS=10  # 10% of $100
HYPERLIQUID_TESTNET=false

# Run for 24 hours
python -m src.core.trading_system
```

**Success criteria:**
- ✅ System runs 24h without crashes
- ✅ Orders execute correctly
- ✅ Circuit breakers work
- ✅ P&L tracking accurate
- ✅ Can close positions manually

**If $100 test fails → Fix issues before scaling**

### Phase 4: Progressive Capital Deployment

Only if Phase 3 succeeds for 3+ days:

| Week | Capital | Max Loss | Leverage | Strategies |
|------|---------|----------|----------|------------|
| 1 | $500 | $50 | 2x | DeepSeek only |
| 2 | $1,500 | $150 | 3x | + OrderBook Imbalance |
| 3 | $5,000 | $500 | 4x | + Smart Momentum |
| 4 | $15,000 | $750 | 5x | All strategies |

## DeepSeek Integration - The Game Changer

### Why DeepSeek?

**Alpha Arena Results (Hyperliquid - Jan 2025):**
- 🏆 **130% return in 10 days** ($10k → $23k)
- 📊 Only 17 trades (highly selective)
- ⏱️ 49 hour average hold time
- 📈 41% win rate, but 6.7:1 profit-to-loss ratio
- 💪 Beat GPT-5, Gemini 2.5 Pro (which lost 28%)

### DeepSeek Setup

```bash
# 1. Get NetMind.ai API key (up to $100k free credits!)
# Visit: https://www.netmind.ai/pricing

# 2. Add to .env
DEEPSEEK_API_KEY=your_netmind_api_key
DEEPSEEK_USE_NETMIND=true
DEEPSEEK_MODEL=deepseek-chat

# 3. Test DeepSeek connection
python scripts/test_deepseek.py
```

### DeepSeek Strategy Configuration

The system now includes `DeepSeekAlphaArenaStrategy` with:

```yaml
deepseek_alpha:
  enabled: true
  min_confidence: 0.7  # Only high-conviction trades
  min_risk_reward: 6.0  # Minimum 6:1 like Alpha Arena
  target_hold_hours: 48  # Patient holding
  max_trades_per_day: 2  # Highly selective
```

**Key differences from other strategies:**
- 🎯 **Selective** - Max 2 trades/day vs unlimited
- ⏳ **Patient** - 48h holds vs 45 second scalps
- 💰 **High R:R** - 6:1 minimum vs 2:1
- 🤖 **AI-Driven** - DeepSeek analyzes all data

## Emergency Procedures

### If System Starts Losing Money:

```bash
# 1. Activate kill switch
curl -X POST http://localhost:8080/api/killswitch

# 2. Close all positions manually via Hyperliquid UI

# 3. Stop system
pkill -f trading_system

# 4. Review logs
tail -f data/logs/trading_system_*.jsonl
```

### Daily Monitoring Checklist:

- [ ] Check daily P&L (should be within risk limits)
- [ ] Verify all positions have stop-losses
- [ ] Confirm circuit breakers armed
- [ ] Review DeepSeek decision logs
- [ ] Monitor system uptime
- [ ] Check API error rates

## Known Risks & Limitations

### Code Limitations:

1. **Untested Hyperliquid API** - May have format issues
2. **No backtesting data** - Performance unknown
3. **Database may fail** - PostgreSQL connection issues
4. **Rate limits untested** - May hit API limits
5. **WebSocket reconnection** - May lose data on disconnect

### Market Risks:

1. **Extreme volatility** - Circuit breakers may not trigger fast enough
2. **Liquidation risk** - Leverage magnifies losses
3. **Slippage** - May not get expected prices
4. **API downtime** - Hyperliquid API could go down
5. **Flash crashes** - Sudden price drops

## Absolute Minimum Requirements Before Mainnet

✅ **MUST HAVE:**

1. ✅ All dependencies installed (`pip install -r requirements.txt`)
2. ✅ PostgreSQL running and configured
3. ✅ Hyperliquid API keys working
4. ✅ DeepSeek/NetMind API key working
5. ✅ System runs for 1 hour without crashes
6. ✅ Can execute test order successfully
7. ✅ Can close test position successfully
8. ✅ Circuit breakers verified working
9. ✅ Start with $100-500 MAXIMUM
10. ✅ Monitor 24/7 for first week

❌ **DO NOT:**

1. ❌ Deploy $15k on day 1
2. ❌ Use max leverage (8x) immediately
3. ❌ Run unattended for first month
4. ❌ Ignore circuit breaker alerts
5. ❌ Disable safety features
6. ❌ Trade without stop-losses
7. ❌ Average down on losers

## Quick Start (Safest Path)

```bash
# 1. Install & test locally
pip install -r requirements.txt
python -m pytest tests/ -v

# 2. Set up environment
cp .env.example .env
nano .env  # Add your API keys

# 3. Start with paper trading
ENABLE_PAPER_TRADING=true python -m src.core.trading_system

# 4. After 24h of paper trading, try $100 live
ENABLE_PAPER_TRADING=false ACTIVE_CAPITAL=100 python -m src.core.trading_system

# 5. Monitor for 3 days, then scale if profitable
# Week 1: $500
# Week 2: $1,500
# Week 3: $5,000
# Week 4: $15,000
```

## Support & Troubleshooting

### Common Issues:

**"ModuleNotFoundError"**
```bash
pip install -r requirements.txt
```

**"Cannot connect to PostgreSQL"**
```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt-get install postgresql  # Linux

# Start service
brew services start postgresql  # macOS
sudo service postgresql start  # Linux

# Create database
createdb hyperliquid_trader
```

**"Hyperliquid API error"**
- Check API key is correct
- Verify you have trading permissions
- Check Hyperliquid API status

**"DeepSeek API error"**
- Verify NetMind.ai API key
- Check credit balance
- Try direct DeepSeek API as fallback

## Final Warning

**This is experimental software trading real money.**

- ⚠️ Only trade capital you can afford to lose
- ⚠️ Start small ($100-500)
- ⚠️ Monitor constantly
- ⚠️ Expect bugs and losses
- ⚠️ Circuit breakers are not foolproof
- ⚠️ Past performance (DeepSeek 130%) ≠ future results

**I cannot guarantee profitability or even basic functionality.**

The safest approach is:
1. Paper trade for 1 week
2. Live test with $100 for 1 week
3. Scale slowly if profitable
4. Never exceed your risk tolerance

Good luck, and trade responsibly! 🚀
