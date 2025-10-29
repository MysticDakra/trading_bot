# 🤝 Integration Guide: Multi-Agent Trading System

## Overview

This system integrates the best from three proven frameworks:

1. **TauricResearch/TradingAgents** - Multi-agent architecture
2. **Gajesh2007/ai-trading-agent** - Proven Hyperliquid integration
3. **Our Custom System** - DeepSeek Alpha Arena strategy + advanced risk management

## Architecture Comparison

| Component | Source | What We Took |
|-----------|--------|--------------|
| **Multi-Agent System** | TauricResearch | 7 specialized agents, LangGraph orchestration |
| **Hyperliquid Integration** | Gajesh2007 | Proven API patterns, execution logic |
| **Technical Indicators** | Gajesh2007 | TAAPI.io integration |
| **Multi-LLM Support** | Gajesh2007 | OpenRouter client (GPT-5, DeepSeek, Grok, Claude) |
| **DeepSeek Strategy** | Our System | Alpha Arena winning approach (130% in 10 days) |
| **Risk Management** | Our System | Circuit breakers, position sizing, liquidation tracking |
| **Nansen Intelligence** | Our System | Smart money flow analysis |

## How It Works

### 1. Multi-Agent Decision Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Phase 1: Parallel Analysis (All agents work simultaneously) │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Technical   │  │   Nansen     │  │   Sentiment  │      │
│  │   Analyst    │  │   Analyst    │  │   Analyst    │      │
│  │  (TAAPI.io)  │  │(Smart Money) │  │  (Social)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│  Phase 2: Research Debate                                   │
│  ┌──────────────────────────────────────┐                  │
│  │  Bull Researcher    Bear Researcher   │                  │
│  │  (Pro arguments)  vs (Con arguments)  │                  │
│  └────────────────┬─────────────────────┘                  │
│                   │                                          │
│  Phase 3: Trading Decision                                  │
│  ┌────────────────┴─────────────────────┐                  │
│  │           Trader Agent                │                  │
│  │  (Synthesizes all inputs)             │                  │
│  │  - Makes final BUY/SELL/HOLD decision │                  │
│  │  - Sets entry, stop-loss, take-profit │                  │
│  │  - Calculates risk/reward ratio       │                  │
│  └────────────────┬─────────────────────┘                  │
│                   │                                          │
│  Phase 4: Risk Validation                                   │
│  ┌────────────────┴─────────────────────┐                  │
│  │        Risk Manager Agent             │                  │
│  │  - Validates position size            │                  │
│  │  - Checks daily loss limits           │                  │
│  │  - Approves or rejects trade          │                  │
│  └────────────────┬─────────────────────┘                  │
│                   │                                          │
│                   ▼                                          │
│            EXECUTE TRADE                                     │
│           (Hyperliquid)                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2. Data Sources Integration

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  TAAPI.io    │    │  Nansen MCP  │    │ Hyperliquid│ │
│  │  (Technical) │    │(Smart Money) │    │ (Order Book)│ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬────┘ │
│         │                    │                    │      │
│         └────────────────────┴────────────────────┘      │
│                              │                           │
│                              ▼                           │
│                    ┌──────────────────┐                 │
│                    │  Data Aggregator │                 │
│                    │  (Our System)    │                 │
│                    └──────────────────┘                 │
│                              │                           │
│                              ▼                           │
│                     Multi-Agent Analysis                 │
└─────────────────────────────────────────────────────────┘
```

### 3. LLM Model Selection

```python
# OpenRouter supports multiple models:

Technical Analyst  → GPT-4o          (Fast, good for charts)
Nansen Analyst    → DeepSeek Chat   (Proven for crypto)
Trader            → DeepSeek R1     (Deep reasoning)
Risk Manager      → Claude Sonnet 4.5 (Conservative, safety-focused)

# Or use model consensus:
models = [LLMModel.GPT_5_PRO, LLMModel.DEEPSEEK_R1, LLMModel.GROK_4]
consensus = await openrouter.get_consensus(results_from_models)
```

## Setup Instructions

### 1. Get Required API Keys

```bash
# OpenRouter (Multi-LLM access)
# Visit: https://openrouter.ai
# Get API key → Add to .env: OPENROUTER_API_KEY=sk-or-...

# TAAPI.io (Technical Indicators)
# Visit: https://taapi.io
# Get API key → Add to .env: TAAPI_API_KEY=...

# Nansen (Smart Money - optional but recommended)
# Visit: https://nansen.ai
# Get API key → Add to .env: NANSEN_API_KEY=...

# Hyperliquid (Exchange)
# Visit: https://hyperliquid.xyz
# Get API key → Add to .env: HYPERLIQUID_API_KEY=...
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Add your API keys

# Key configuration:
ENABLE_MULTI_AGENT=true  # Use multi-agent system
USE_OPENROUTER=true      # Use OpenRouter for LLMs
DEFAULT_LLM_MODEL=deepseek/deepseek-chat  # Default model
```

### 4. Test Components

```bash
# Test TAAPI connection
python -c "
import asyncio
from src.data.taapi_client import TaapiClient
client = TaapiClient('your_taapi_key')
asyncio.run(client.get_indicators('SOL'))
"

# Test OpenRouter
python -c "
import asyncio
from src.ai.openrouter_client import OpenRouterClient, LLMModel
client = OpenRouterClient('your_openrouter_key')
asyncio.run(client.chat_completion(
    [{'role': 'user', 'content': 'Analyze SOL/USDT'}],
    model=LLMModel.DEEPSEEK_CHAT
))
"

# Test multi-agent system
python scripts/test_multi_agent.py
```

## Usage Examples

### Basic Multi-Agent Analysis

```python
from src.ai.multi_agent_system import MultiAgentTradingSystem
from src.ai.openrouter_client import OpenRouterClient
from src.data.taapi_client import TaapiClient
from src.data.nansen_client import NansenMCPClient

# Initialize clients
openrouter = OpenRouterClient(api_key="your_key")
taapi = TaapiClient(api_key="your_key")
nansen = NansenMCPClient(api_key="your_key")

# Create multi-agent system
system = MultiAgentTradingSystem(
    openrouter_client=openrouter,
    taapi_client=taapi,
    nansen_client=nansen
)

# Analyze symbol
result = await system.analyze_symbol(
    symbol="SOL",
    current_price=100.50,
    order_book_data={
        'imbalance': 0.65,
        'spread_bps': 25
    }
)

print(f"Decision: {result['final_decision']['action']}")
print(f"Confidence: {result['final_decision']['confidence']:.2%}")
print(f"Reasoning: {result['final_decision']['reasoning']}")
```

### Multi-LLM Consensus

```python
from src.ai.openrouter_client import LLMModel

# Get recommendations from multiple models
models = [
    LLMModel.GPT_5_PRO,
    LLMModel.DEEPSEEK_R1,
    LLMModel.GROK_4,
    LLMModel.CLAUDE_SONNET_4_5
]

results = await openrouter.compare_models(
    symbol="SOL",
    current_price=100.50,
    technical_data=technical_indicators,
    models=models
)

# Get consensus
consensus = openrouter.get_consensus(results)

print(f"Consensus: {consensus['action']}")
print(f"Votes: BUY={consensus['votes']['BUY']}, "
      f"SELL={consensus['votes']['SELL']}, "
      f"HOLD={consensus['votes']['HOLD']}")
```

## Performance Comparison

| Approach | Trades/Day | Complexity | Cost | Best For |
|----------|-----------|------------|------|----------|
| **Single DeepSeek** | 1-2 | Low | $ | Simple, proven |
| **Multi-Agent** | 0.5-1 | High | $$$ | High-stakes decisions |
| **Multi-LLM Consensus** | 0.3-0.8 | Medium | $$$$ | Maximum confidence |
| **Hybrid** | 1-3 | Medium | $$ | Best balance ⭐ |

### Recommended Hybrid Approach:

```python
# Use multi-agent for large positions (>$5k)
if position_size > 5000:
    decision = await multi_agent_system.analyze_symbol(symbol, price)

# Use single DeepSeek for smaller positions
else:
    decision = await deepseek_client.analyze_market(symbol, price, data)
```

## Cost Optimization

### API Call Costs (Approximate)

| Service | Cost per Call | Calls per Day | Monthly Cost |
|---------|--------------|---------------|--------------|
| TAAPI.io | $0.001 | 100 | $3 |
| OpenRouter (DeepSeek) | $0.02 | 50 | $30 |
| OpenRouter (GPT-5) | $0.50 | 10 | $150 |
| Nansen | Subscription | - | $150 |
| **Total (Multi-Agent)** | | | **~$333/month** |

### Cost Reduction Strategies:

1. **Cache Results** - Don't re-analyze same data
2. **Smart Triggering** - Only run multi-agent on high-confidence setups
3. **Use Cheaper Models** - DeepSeek/Grok for most, GPT-5 for critical decisions
4. **Batch Analysis** - Analyze multiple symbols together

## Troubleshooting

### "OpenRouter API error: 401"
- Check API key is correct
- Verify account has credits
- Try: `curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models`

### "TAAPI rate limit exceeded"
- Free tier: 30 calls/day
- Upgrade to paid plan or reduce query frequency

### "Multi-agent analysis taking too long"
- Agents run in parallel, but LLMs can take 5-30s
- DeepSeek R1 (reasoning model) takes longer
- Use caching and reduce unnecessary calls

### "Consensus is always HOLD"
- Agents are being conservative (good!)
- Lower confidence thresholds if needed
- Ensure all data sources are working

## Migration from Old System

### If you're using our previous single-DeepSeek system:

```python
# OLD:
decision = await deepseek_client.analyze_market(symbol, price, data)

# NEW (Multi-Agent):
decision = await multi_agent_system.analyze_symbol(symbol, price, data)

# NEW (Multi-LLM):
results = await openrouter.compare_models(symbol, price, data, models)
consensus = openrouter.get_consensus(results)
```

### Configuration Changes:

```bash
# Add to .env:
OPENROUTER_API_KEY=...
TAAPI_API_KEY=...
ENABLE_MULTI_AGENT=true
USE_OPENROUTER=true
```

## Best Practices

### 1. Start Simple
- Begin with single DeepSeek strategy
- Add TAAPI technical indicators
- Then enable multi-agent if needed
- Finally add multi-LLM consensus

### 2. Monitor Costs
- Track API usage daily
- Set spending alerts
- Use cheaper models for testing

### 3. Trust the Process
- Multi-agent system is conservative (by design)
- Fewer trades = higher quality
- Consensus takes time but worth it

### 4. Paper Trade First
- Test with ENABLE_PAPER_TRADING=true
- Verify agents make sensible decisions
- Check consensus accuracy
- Only then deploy real capital

## Support & Resources

- **TauricResearch Paper**: https://arxiv.org/abs/2412.20138
- **Gajesh2007 Repo**: https://github.com/Gajesh2007/ai-trading-agent
- **OpenRouter Docs**: https://openrouter.ai/docs
- **TAAPI Docs**: https://taapi.io/documentation
- **Our Repo Issues**: https://github.com/yourusername/hyperliquid-trader/issues

## Future Enhancements

- [ ] LangGraph integration for advanced workflows
- [ ] Sentiment analysis from Twitter/Reddit
- [ ] News analyst agent
- [ ] Automated agent performance tracking
- [ ] Dynamic model selection based on market conditions
- [ ] Agent memory/learning between sessions

---

**Built with contributions from:**
- TauricResearch - Multi-agent architecture
- Gajesh2007 - Hyperliquid integration patterns
- Our team - DeepSeek strategy & risk management

Let's build the future of algorithmic trading together! 🚀
