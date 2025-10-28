# Hyperliquid Perpetuals Trading System

## Project Overview
Production-grade automated perpetual futures trading system for Hyperliquid DEX, leveraging institutional-grade smart money intelligence via Nansen MCP integration and self-improving AI agents.

## Capital & Risk Parameters
- **Active Capital**: $15,000 (initial deployment)
- **Total Capital**: $1,000,000 (reserved)
- **Leverage**: 4-5x normal operations, up to 8x for DCA on winning positions
- **Risk per Trade**: ~$1,000-$1,300 split across 3-4 positions
- **Daily Loss Limit**: $750 (5% of active capital)
- **Maximum Drawdown**: $3,000 (20% of active capital)

## Primary Trading Pairs
- SOL/USD (Solana)
- HYPE/USD (Hyperliquid native token)
- DOGE/USD (Dogecoin)

## Competitive Edge Sources
1. **Nansen MCP Integration**: Real-time smart money flows, whale movements, VC/foundation accumulation
2. **Order Book Analysis**: Level 5 imbalance detection with institutional backing validation
3. **Self-Improving AI**: Reinforcement learning with continuous post-trade analysis
4. **Multi-Strategy Approach**: Parallel execution of complementary strategies

## Architecture Philosophy
- **Safety First**: Comprehensive error handling, circuit breakers, kill switches
- **Production Quality**: 95%+ test coverage, type hints, structured logging
- **Institutional Grade**: Microsecond timestamps, audit trails, PostgreSQL persistence
- **Continuous Learning**: Every trade improves the system

## Key Technical Components
- WebSocket market data with automatic reconnection
- Nansen MCP queries every 2-3 minutes
- PPO reinforcement learning agent
- Multi-strategy signal aggregation
- Real-time monitoring dashboard
- Progressive capital deployment (Week 1: $150 → Week 5: $15,000)

## Performance Goals
- Target Sharpe Ratio: >2.0
- Win Rate: >55%
- Average Risk/Reward: >1.8:1
- Maximum Consecutive Losses: <5
- System Uptime: >99.5%

## Development Status
Building systematically through 5 phases:
1. ✓ Core Infrastructure
2. ⏳ Nansen MCP Integration
3. ⏳ Multi-Strategy Trading System
4. ⏳ Autonomous Learning & Adaptation
5. ⏳ Production-Ready Execution & Monitoring
