# Hyperliquid Perpetuals Trading System

> **Production-grade automated trading system for Hyperliquid perpetual futures, powered by Nansen smart money intelligence and self-improving AI.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

An institutional-grade algorithmic trading system designed to trade perpetual futures on Hyperliquid DEX with:

- **$15,000** active capital deployment (scalable to $1M)
- **4-5x leverage** normal operations (up to 8x for scaling winners)
- **Multi-strategy approach** combining order book analysis, Nansen intelligence, and momentum trading
- **Self-improving AI** using reinforcement learning and continuous post-trade analysis
- **Rigorous risk management** with circuit breakers, position sizing, and daily loss limits

### Key Features

✅ **Smart Money Intelligence** - Nansen MCP integration for institutional flow tracking
✅ **Real-time Market Data** - WebSocket order book with automatic reconnection
✅ **Multi-Strategy Execution** - Parallel strategy execution with capital allocation
✅ **AI Reasoning Engine** - Continuous learning with self-questioning framework
✅ **Production-Grade Risk** - Kelly Criterion sizing, liquidation tracking, circuit breakers
✅ **Comprehensive Logging** - PostgreSQL audit trails with microsecond timestamps
✅ **Progressive Deployment** - 5-week rollout plan from $150 to $15k

## 📊 Performance Goals

| Metric | Target |
|--------|--------|
| Sharpe Ratio | > 2.0 |
| Win Rate | > 55% |
| Risk/Reward | > 1.8:1 |
| Max Drawdown | < 20% |
| System Uptime | > 99.5% |

## 🏗️ Architecture

```
hyperliquid-trader/
├── src/
│   ├── core/              # Core infrastructure
│   │   ├── config.py      # Type-safe configuration
│   │   ├── logger.py      # Structured logging
│   │   └── trading_system.py  # Main coordinator
│   ├── data/              # Market data & intelligence
│   │   ├── market_data.py # WebSocket & order book
│   │   └── nansen_client.py  # Nansen MCP client
│   ├── strategies/        # Trading strategies
│   │   ├── base_strategy.py  # Base strategy class
│   │   ├── imbalance_strategy.py  # Order book imbalance
│   │   └── smart_momentum_strategy.py  # Nansen-driven momentum
│   ├── execution/         # Order execution
│   │   └── executor.py    # Hyperliquid executor
│   ├── risk/              # Risk management
│   │   ├── risk_manager.py  # Position sizing & limits
│   │   └── circuit_breakers.py  # Emergency safeguards
│   └── ai/                # AI & learning
│       └── reasoning_engine.py  # Continuous reasoning
├── config/
│   └── trading_config.yaml  # Trading configuration
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Hyperliquid account with API access
- Nansen API key (for smart money data)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/hyperliquid-trader.git
cd hyperliquid-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` with your credentials:

```env
# Hyperliquid
HYPERLIQUID_API_KEY=your_api_key
HYPERLIQUID_PRIVATE_KEY=your_private_key

# Nansen
NANSEN_API_KEY=your_nansen_key

# Database
POSTGRES_USER=trader
POSTGRES_PASSWORD=your_password

# Risk Management
ACTIVE_CAPITAL=15000
MAX_DAILY_LOSS=750
MAX_DRAWDOWN=3000

# Start in paper trading mode
ENABLE_PAPER_TRADING=true
```

### Running the System

```bash
# Initialize database
python scripts/init_database.py

# Run in paper trading mode
python -m src.core.trading_system

# Or use Docker
docker-compose up -d
```

## 📈 Trading Strategies

### 1. Order Book Imbalance Strategy

**Entry Logic:**
- Calculate L5 imbalance: `ρ = (V_bid - V_ask) / (V_bid + V_ask)`
- Enter when `|ρ| > 0.6` AND Nansen confirms direction
- Scalping timeframe: 30-60 seconds

**Risk Parameters:**
- Stop Loss: 0.5% (50 bps)
- Take Profit: 1.0% (100 bps)
- Leverage: 4x
- Position Size: ~$1,000 risk

### 2. Smart Money Momentum Strategy

**Entry Logic:**
- Primary: Nansen smart money net buying > 30%
- Confirmation: Exchange outflows detected
- Technical: Order book supports direction

**Position Management:**
- Scale in 4 stages: 25% → 25% → 30% → 20%
- NEVER average down losers
- Only scale winners
- Hold 2-10 days typical

**Risk Parameters:**
- Stop Loss: 3% for momentum trades
- Take Profit: 15% target
- Leverage: 3-5x based on conviction

## 🛡️ Risk Management

### Position Sizing

Uses **Kelly Criterion** with 0.25 fractional Kelly for safety:

```python
kelly_percent = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
position_size = capital * kelly_percent * 0.25
```

### Circuit Breakers

| Breaker | Threshold | Action |
|---------|-----------|--------|
| Daily Loss | $750 (5% of capital) | Pause trading |
| Max Drawdown | $3,000 (20%) | Pause trading |
| API Errors | 10 consecutive | Pause trading |
| Volatility Spike | 50% in 5 min | Alert only |
| Consecutive Losses | 5 trades | Pause trading |
| Kill Switch | Manual trigger | Close all positions |

### Liquidation Protection

```python
liquidation_price = entry_price * (1 - (1/leverage - maintenance_margin))
```

System monitors all positions and reduces leverage before approaching liquidation.

## 🤖 AI & Learning

### Continuous Reasoning Engine

Queries Nansen every 2-3 minutes with self-questioning framework:

1. **"What Nansen insight gives edge right now?"**
   - Analyzes smart money flows
   - Identifies institutional accumulation

2. **"How do smart money flows align with price?"**
   - Cross-references Nansen with order book
   - Detects divergences and confirmations

3. **"What institutional accumulation patterns exist?"**
   - Tracks whale movements
   - Monitors VC/Foundation wallets

### Post-Trade Analysis

After each trade:
- Which Nansen signal was most predictive?
- Was entry timing optimal?
- What pattern led to success/failure?

Insights stored and used to:
- Update strategy weights
- Adjust Nansen query parameters
- Refine entry/exit logic

## 📊 Monitoring & Alerts

### Real-time Dashboard

Access at `http://localhost:8080` after starting:

- Current positions & P&L
- Live Nansen signals
- Strategy performance metrics
- Risk exposure gauges
- Circuit breaker status

### Alerts

Configured via Discord/Telegram:

- Trade executions
- Circuit breaker trips
- Daily P&L summary
- Performance milestones

## 🗓️ Progressive Deployment Plan

| Week | Capital | Leverage | Strategies | AI |
|------|---------|----------|------------|-----|
| 1 | $150 | 1x | Order Book Imbalance | ❌ |
| 2 | $500 | 2x | + Volume Profile | ❌ |
| 3 | $1,500 | 3x | + Smart Momentum | ❌ |
| 4 | $5,000 | 4x | All | ❌ |
| 5 | $15,000 | 5x | All | ✅ |

**Philosophy:** Prove profitability at each stage before scaling capital and complexity.

## 🧪 Testing

```bash
# Run test suite
pytest tests/ -v --cov=src --cov-report=html

# Run specific test
pytest tests/test_risk_manager.py -v

# Check coverage (target: 95%+)
coverage report
```

## 🔒 Security Best Practices

1. **Never commit `.env`** - Keep API keys secure
2. **Use testnet first** - Test with `HYPERLIQUID_TESTNET=true`
3. **Start with paper trading** - Validate before live deployment
4. **Monitor circuit breakers** - Review breach logs regularly
5. **Backup database** - Automated S3 backups configured

## 📚 Documentation

- [Strategy Details](docs/strategies.md)
- [Risk Management](docs/risk_management.md)
- [Nansen Integration](docs/nansen_integration.md)
- [API Reference](docs/api_reference.md)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

This is a personal trading system, but feedback and suggestions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Trading cryptocurrency perpetuals involves substantial risk of loss
- Past performance does not guarantee future results
- Only trade with capital you can afford to lose
- The authors are not responsible for any financial losses

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Hyperliquid team for robust DEX infrastructure
- Nansen for institutional-grade on-chain analytics
- Renaissance Technologies for inspiring systematic approaches

---

**Built with ❤️ for algorithmic trading excellence**

*"In God we trust. All others must bring data."* - W. Edwards Deming
