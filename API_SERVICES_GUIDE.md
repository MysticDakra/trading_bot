# 💰 API Services & Costs Guide

## Quick Answer: What Do I Need to Pay For?

**Minimum to get started (Recommended):**

1. ✅ **OpenRouter** ($5-10/month) - Access ALL LLMs including Claude
2. ✅ **TAAPI.io** ($9/month) - Technical indicators
3. ⚠️ **Nansen** ($150/month) - Smart money data (optional but powerful)
4. ✅ **Hyperliquid** (FREE API) - Exchange

**Total minimum:** **$14-19/month** (without Nansen)
**Total recommended:** **$164-179/month** (with Nansen)

---

## Option 1: OpenRouter (RECOMMENDED - One API for All) 🌟

### What It Is:
- Single API key accesses **ALL** major LLMs
- Pay-per-use pricing
- No need for separate API keys

### What You Get:
```
✅ Claude Sonnet 4.5, Claude Opus 4     (Anthropic)
✅ GPT-5 Pro, GPT-4o, o1-preview        (OpenAI)
✅ DeepSeek Chat, DeepSeek R1           (DeepSeek)
✅ Grok 4, Grok Beta                    (xAI)
✅ Gemini 2.5 Pro                        (Google)
✅ Qwen 3 Max                            (Alibaba)
```

### Cost:
- **No monthly fee**
- Pay per token used
- Example costs per API call:
  - DeepSeek: ~$0.02/call
  - GPT-4o: ~$0.10/call
  - Claude Sonnet: ~$0.15/call
  - GPT-5: ~$0.50/call

### Monthly estimate (50 decisions/day):
- Using mostly DeepSeek: **$30/month**
- Using mix of models: **$100/month**
- Using premium models: **$500/month**

### How to Get:
1. Visit: https://openrouter.ai
2. Sign up with GitHub
3. Add credit ($10 minimum)
4. Copy API key
5. Add to .env: `OPENROUTER_API_KEY=sk-or-...`

### Our System Usage:
```python
# We configured different models for different agents:
Technical Analyst → GPT-4o (fast, good at charts)
Nansen Analyst   → DeepSeek Chat (proven for crypto)
Trader           → DeepSeek R1 (deep reasoning)
Risk Manager     → Claude Sonnet 4.5 (conservative)
```

---

## Option 2: Direct API Keys (More Expensive)

If you prefer separate accounts:

### Anthropic Claude Direct
- Website: https://console.anthropic.com
- Cost: $15-75/month depending on tier
- Pro: Direct access to Claude
- Con: More expensive than OpenRouter

### OpenAI Direct
- Website: https://platform.openai.com
- Cost: Pay-per-use (expensive for GPT-5)
- Pro: Latest models first
- Con: GPT-5 is $$$

### DeepSeek Direct (or NetMind.ai)
- Website: https://platform.deepseek.com OR https://netmind.ai
- Cost: $0 (NetMind offers up to $100k free credits!)
- Pro: FREE for DeepSeek
- Con: Only DeepSeek models

---

## Required Services Breakdown

### 1. TAAPI.io (Technical Indicators)

**What:** 100+ technical indicators (RSI, MACD, Bollinger Bands, etc.)

**Pricing:**
- **Free Tier**: 30 API calls/day (not enough for trading)
- **Basic**: $9/month - 500 calls/day ✅ RECOMMENDED
- **Pro**: $29/month - 5,000 calls/day
- **Ultra**: $79/month - Unlimited

**Get it here:** https://taapi.io/pricing

**Our usage:** ~100 calls/day (fits Basic plan)

**Setup:**
```bash
# Sign up at taapi.io
# Get API key
# Add to .env
TAAPI_API_KEY=your_key_here
```

---

### 2. Nansen (Smart Money Intelligence)

**What:** On-chain whale tracking, smart money flows, institutional data

**Why it's powerful:**
- See what whales are buying BEFORE price moves
- Track VC/Foundation accumulation
- Exchange netflow analysis
- This is what gave DeepSeek its edge!

**Pricing:**
- **No free tier**
- **Standard**: ~$150/month
- **Pro**: ~$400/month

**Get it here:** https://nansen.ai

**Is it worth it?**
- ✅ YES if trading with >$5k capital
- ❌ NO if just starting with <$1k
- 💡 TIP: Our system works WITHOUT Nansen, but it's less powerful

**Alternative (FREE):**
```python
# Use our order book analysis instead
# Not as good as Nansen, but free
imbalance = order_book.get_imbalance(depth=5)
if imbalance > 0.6:
    print("Bullish pressure detected")
```

---

### 3. Hyperliquid (Exchange)

**What:** DEX for perpetual futures (where we trade)

**Cost:** **FREE API** ✅

**Get it here:** https://hyperliquid.xyz

**Setup:**
```bash
# Create account on Hyperliquid
# Generate API key in Settings
# Add to .env
HYPERLIQUID_API_KEY=your_key_here
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
```

**Note:** Requires ETH on Arbitrum for gas fees (~$5-10 should last months)

---

## Recommended Setup by Budget

### Broke AF Budget ($0-14/month)

```
✅ NetMind.ai          → FREE DeepSeek access ($100k credits)
✅ TAAPI Free Tier     → 30 calls/day (limited but works)
✅ Hyperliquid         → FREE
✅ Skip Nansen         → Use order book analysis instead
---
Total: $0-9/month (if you pay for TAAPI Basic)
```

**Limitations:**
- Single LLM (DeepSeek only)
- Limited technical indicator calls
- No Nansen smart money data
- Still profitable if strategy is good!

### Starter Budget ($14-50/month)

```
✅ OpenRouter          → $10-30/month (mostly DeepSeek)
✅ TAAPI Basic         → $9/month
✅ Hyperliquid         → FREE
✅ Skip Nansen         → Use alternatives
---
Total: $19-39/month
```

**What you get:**
- Multi-LLM access (try different models)
- 500 technical indicator calls/day
- Multi-agent system works
- Good enough for $1k-5k trading capital

### Professional Budget ($164-250/month) ⭐ RECOMMENDED

```
✅ OpenRouter          → $30-100/month (mix of models)
✅ TAAPI Basic         → $9/month
✅ Nansen              → $150/month
✅ Hyperliquid         → FREE
---
Total: $189-259/month
```

**What you get:**
- Full multi-agent system
- Smart money intelligence (HUGE edge)
- Multiple LLM consensus
- Worth it for >$5k capital

### Whale Budget ($500+/month)

```
✅ OpenRouter Premium  → $200-500/month (GPT-5, Claude heavy usage)
✅ TAAPI Pro/Ultra     → $29-79/month
✅ Nansen Pro          → $400/month
✅ Hyperliquid         → FREE
---
Total: $629-979/month
```

**What you get:**
- Best-in-class everything
- No API limits
- Maximum edge
- For $50k+ capital only

---

## How to Use Claude in Our System

### Via OpenRouter (Easiest):

```python
from src.ai.openrouter_client import OpenRouterClient, LLMModel

# Initialize with OpenRouter
client = OpenRouterClient(api_key="your_openrouter_key")

# Use Claude for risk management
decision = await client.analyze_trade(
    symbol="SOL",
    current_price=100.50,
    technical_data=indicators,
    model=LLMModel.CLAUDE_SONNET_4_5  # ← Claude via OpenRouter
)
```

### Configure agents to use Claude:

```python
# In src/ai/multi_agent_system.py

# Risk Manager uses Claude (conservative, safe)
self.risk_manager = RiskManagerAgent(
    openrouter_client,
    model=LLMModel.CLAUDE_SONNET_4_5  # ← Claude
)

# Trader uses DeepSeek R1 (proven winner)
self.trader = TraderAgent(
    openrouter_client,
    model=LLMModel.DEEPSEEK_R1  # ← DeepSeek
)

# Technical uses GPT-4o (fast, good at charts)
self.technical_analyst = TechnicalAnalystAgent(
    openrouter_client,
    model=LLMModel.GPT_4O  # ← GPT-4o
)
```

### Why this combination works:
- **Claude** = Best for safety/risk (conservative)
- **DeepSeek** = Best for trading decisions (proven 130% returns)
- **GPT-4o** = Best for technical analysis (fast)

---

## Nansen Integration

### How Nansen Works in Our System:

```python
# 1. Nansen Client fetches smart money data
nansen_client = NansenMCPClient(api_key="your_key")
signals = await nansen_client.analyze_symbol("SOL")

# Example signals:
# - Top 100 wallets net buying: +45%
# - Exchange outflow: -$20M (bullish)
# - VC/Foundation accumulating
# - Whale wallet activity

# 2. Nansen Analyst Agent analyzes the data
nansen_agent = NansenAnalystAgent(openrouter_client, nansen_client)
report = await nansen_agent.analyze(context)

# 3. Trader synthesizes Nansen + Technical + Order Book
trader_decision = await trader.analyze({
    'technical_analysis': technical_report,
    'nansen_analysis': nansen_report,  # ← Smart money intel
    'order_book': order_book_data
})
```

### Without Nansen (FREE alternative):

```python
# Use order book imbalance as proxy
order_book = websocket.get_order_book("SOL")
imbalance = order_book.get_imbalance(depth=5)

# Strong imbalance = "dumb money" signal (vs Nansen's "smart money")
if imbalance > 0.6:
    # Looks bullish, but we don't know if whales agree
    # With Nansen, we would know if this aligns with smart money
```

**Bottom line:** System works without Nansen, but Nansen adds **significant edge**

---

## My Recommendation for YOU

### If you have <$1,000 capital:

```bash
Budget: $14/month

1. OpenRouter: $5-10/month
   - Use mostly DeepSeek (cheap, proven)
   - Occasional Claude for risk checks

2. TAAPI Basic: $9/month
   - 500 calls/day is enough

3. Skip Nansen
   - Not worth $150/month on small capital
   - Use order book analysis instead

4. Start with single DeepSeek strategy
   - Proven 130% returns
   - Simpler and cheaper
   - Add multi-agent later if profitable
```

### If you have $5,000+ capital:

```bash
Budget: $189/month

1. OpenRouter: $30-80/month
   - Use model consensus for large trades
   - Mix of DeepSeek, Claude, GPT

2. TAAPI Basic: $9/month

3. Nansen: $150/month
   - THIS IS THE GAME CHANGER
   - See what whales see
   - Worth every penny at this capital level

4. Use full multi-agent system
   - Technical + Nansen + Trader + Risk Manager
   - Multiple perspectives = higher quality
```

### If you have $50,000+ capital:

```bash
Budget: $500+/month

Go all-in:
- OpenRouter premium usage
- TAAPI Pro/Ultra
- Nansen Pro
- Multiple strategies in parallel
- API costs become negligible vs returns
```

---

## Setup Steps (For Starter Budget)

```bash
# 1. Get OpenRouter (ONE API FOR ALL LLMs)
# Visit: https://openrouter.ai
# Sign up → Add $10 credit → Copy API key

# 2. Get TAAPI
# Visit: https://taapi.io
# Sign up → Subscribe to Basic ($9/month) → Copy API key

# 3. Configure .env
OPENROUTER_API_KEY=sk-or-v1-...
TAAPI_API_KEY=your_taapi_key
DEFAULT_LLM_MODEL=deepseek/deepseek-chat

# Optional: Add Nansen if you have budget
# NANSEN_API_KEY=your_nansen_key

# 4. Test everything
python scripts/test_multi_agent.py
```

---

## Cost vs Return Calculator

If your system makes **10% per month**:

| Capital | Monthly Profit | API Costs | Net Profit | Worth It? |
|---------|---------------|-----------|------------|-----------|
| $500 | $50 | $14 | $36 | ✅ Maybe |
| $1,000 | $100 | $14 | $86 | ✅ Yes |
| $5,000 | $500 | $189 | $311 | ✅ Definitely |
| $15,000 | $1,500 | $189 | $1,311 | ✅ No-brainer |
| $50,000 | $5,000 | $500 | $4,500 | ✅ Obviously |

**Bottom line:** If you're profitable, API costs are tiny compared to returns!

---

## Final Recommendations:

### Start Here (First Month):
1. ✅ OpenRouter with DeepSeek ($10)
2. ✅ TAAPI Basic ($9)
3. ❌ Skip Nansen initially
4. ✅ Test with $100-500 capital
5. ✅ Paper trade first

### If Profitable (Second Month):
1. ✅ Add Nansen ($150)
2. ✅ Scale to $5,000 capital
3. ✅ Enable multi-agent system
4. ✅ Use model consensus

### After Proven Results:
1. ✅ Scale capital to $15,000+
2. ✅ API costs become irrelevant
3. ✅ Focus on strategy optimization
4. 🚀 Make money!

---

**Questions? Let me know what budget you're working with and I'll tailor the setup!**
