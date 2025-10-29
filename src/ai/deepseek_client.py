"""
DeepSeek API client for advanced trading analysis.

Based on Alpha Arena results:
- 130% return in 10 days on Hyperliquid
- Only 17 trades, 49 hour avg hold time
- 41% win rate, 6.7:1 profit-to-loss ratio
- Strategy: Diversification, rigid discipline, balanced risk
"""

import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from src.core.logger import get_logger, LogCategory


@dataclass
class DeepSeekAnalysis:
    """DeepSeek market analysis result."""
    symbol: str
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    hold_duration_hours: Optional[int] = None
    risk_reward_ratio: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DeepSeekClient:
    """
    Client for DeepSeek API via NetMind.ai or direct API.

    DeepSeek's winning Alpha Arena strategy:
    - Long holding periods (avg 49 hours)
    - High profit-to-loss ratio (6.7:1)
    - Selective entries (only 17 trades in 10 days)
    - Diversified across multiple assets
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        use_netmind: bool = False
    ):
        """
        Initialize DeepSeek client.

        Args:
            api_key: API key for DeepSeek or NetMind.ai
            api_url: API endpoint URL
            model: Model to use (deepseek-chat, deepseek-coder, etc.)
            use_netmind: Use NetMind.ai infrastructure
        """
        self.api_key = api_key
        self.api_url = "https://inference.netmind.ai/v1" if use_netmind else api_url
        self.model = model

        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger("deepseek_client")

        # Track DeepSeek's strategy principles
        self.min_risk_reward_ratio = 6.0  # Target 6:1 like Alpha Arena
        self.min_confidence_threshold = 0.7  # Only high-confidence trades
        self.target_hold_hours = 48  # Similar to 49 hour avg

    async def init(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=60)
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Make request to DeepSeek API.

        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response text
        """
        if not self.session:
            await self.init()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with self.session.post(
                f"{self.api_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()

                return data["choices"][0]["message"]["content"]

        except Exception as e:
            self.logger.error(
                f"DeepSeek API error: {e}",
                category=LogCategory.AI,
                error=str(e)
            )
            raise

    async def analyze_market(
        self,
        symbol: str,
        current_price: float,
        order_book_data: Dict[str, Any],
        nansen_data: Optional[Dict[str, Any]] = None,
        technical_data: Optional[Dict[str, Any]] = None,
        market_context: Optional[str] = None
    ) -> DeepSeekAnalysis:
        """
        Analyze market using DeepSeek's Alpha Arena winning approach.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            order_book_data: Order book imbalance and liquidity data
            nansen_data: Nansen smart money signals
            technical_data: Technical indicators
            market_context: Additional market context

        Returns:
            DeepSeek analysis with trading recommendation
        """
        # Build comprehensive market analysis prompt
        prompt = self._build_analysis_prompt(
            symbol=symbol,
            current_price=current_price,
            order_book_data=order_book_data,
            nansen_data=nansen_data,
            technical_data=technical_data,
            market_context=market_context
        )

        messages = [
            {
                "role": "system",
                "content": """You are DeepSeek, an elite quantitative trading AI that achieved 130% returns in 10 days on Hyperliquid.

Your winning strategy principles:
1. SELECTIVE: Only take high-conviction trades (you made only 17 trades in 10 days)
2. PATIENT: Average hold time is 49 hours - don't scalp, let winners run
3. HIGH R:R: Target 6:1+ profit-to-loss ratios minimum
4. DISCIPLINED: Never break stop-loss or take-profit rules
5. DIVERSIFIED: Spread risk across multiple quality setups

Analyze the market data and provide a trading recommendation in JSON format:
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation",
    "entry_price": number,
    "stop_loss": number,
    "take_profit": number,
    "hold_duration_hours": number,
    "risk_reward_ratio": number
}

Only recommend BUY/SELL if:
- Confidence > 0.7
- Risk/Reward ratio > 6.0
- Clear edge identified
- Aligns with smart money flow

Otherwise, recommend HOLD."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Get DeepSeek analysis
        response = await self._make_request(messages, temperature=0.3)

        # Parse response
        analysis = self._parse_analysis(symbol, response)

        self.logger.info(
            f"DeepSeek analysis: {symbol} -> {analysis.action} (confidence: {analysis.confidence:.2f})",
            category=LogCategory.AI,
            symbol=symbol,
            action=analysis.action,
            confidence=analysis.confidence,
            risk_reward=analysis.risk_reward_ratio
        )

        return analysis

    def _build_analysis_prompt(
        self,
        symbol: str,
        current_price: float,
        order_book_data: Dict[str, Any],
        nansen_data: Optional[Dict[str, Any]],
        technical_data: Optional[Dict[str, Any]],
        market_context: Optional[str]
    ) -> str:
        """Build comprehensive analysis prompt."""
        prompt_parts = [
            f"# Market Analysis for {symbol}",
            f"Current Price: ${current_price:.4f}",
            "",
            "## Order Book Data",
            f"- Imbalance: {order_book_data.get('imbalance', 0):.2f}",
            f"- Bid Liquidity: ${order_book_data.get('bid_liquidity', 0):,.0f}",
            f"- Ask Liquidity: ${order_book_data.get('ask_liquidity', 0):,.0f}",
            f"- Spread (bps): {order_book_data.get('spread_bps', 0):.1f}",
        ]

        if nansen_data:
            prompt_parts.extend([
                "",
                "## Nansen Smart Money Analysis",
                f"- Smart Money Action: {nansen_data.get('action', 'UNKNOWN')}",
                f"- Smart Money Confidence: {nansen_data.get('confidence', 0):.2f}",
                f"- Net Position Change: {nansen_data.get('score', 0):.2f}",
                f"- Signal Count: {len(nansen_data.get('signals', []))}",
            ])

            # Add individual signals
            for signal in nansen_data.get('signals', []):
                prompt_parts.append(
                    f"  - {signal.get('type')}: {signal.get('strength')} "
                    f"(confidence: {signal.get('confidence', 0):.2f})"
                )

        if technical_data:
            prompt_parts.extend([
                "",
                "## Technical Indicators",
                f"- RSI: {technical_data.get('rsi', 0):.1f}",
                f"- MACD: {technical_data.get('macd', 0):.4f}",
                f"- Volume: {technical_data.get('volume', 0):,.0f}",
            ])

        if market_context:
            prompt_parts.extend([
                "",
                "## Market Context",
                market_context
            ])

        prompt_parts.extend([
            "",
            "## Your Task",
            "Based on the above data and your Alpha Arena winning strategy:",
            "1. Determine if this is a high-conviction setup (confidence > 0.7)",
            "2. Calculate realistic stop-loss and take-profit for 6:1+ R:R",
            "3. Estimate optimal hold duration based on setup type",
            "4. Only recommend entry if all criteria are met",
            "",
            "Provide your analysis in the JSON format specified."
        ])

        return "\n".join(prompt_parts)

    def _parse_analysis(self, symbol: str, response: str) -> DeepSeekAnalysis:
        """Parse DeepSeek response into analysis object."""
        import json

        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]

            data = json.loads(json_str)

            # Validate risk/reward ratio
            risk_reward = data.get('risk_reward_ratio', 0)
            confidence = data.get('confidence', 0)

            # Override action if doesn't meet criteria
            action = data.get('action', 'HOLD')
            if action in ['BUY', 'SELL']:
                if confidence < self.min_confidence_threshold:
                    self.logger.warning(
                        f"Overriding {action} to HOLD: confidence {confidence:.2f} < {self.min_confidence_threshold}",
                        category=LogCategory.AI
                    )
                    action = 'HOLD'
                elif risk_reward < self.min_risk_reward_ratio:
                    self.logger.warning(
                        f"Overriding {action} to HOLD: R:R {risk_reward:.1f} < {self.min_risk_reward_ratio}",
                        category=LogCategory.AI
                    )
                    action = 'HOLD'

            return DeepSeekAnalysis(
                symbol=symbol,
                action=action,
                confidence=confidence,
                reasoning=data.get('reasoning', ''),
                entry_price=data.get('entry_price'),
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                hold_duration_hours=data.get('hold_duration_hours'),
                risk_reward_ratio=risk_reward
            )

        except Exception as e:
            self.logger.error(
                f"Error parsing DeepSeek response: {e}",
                category=LogCategory.AI,
                error=str(e),
                response=response
            )

            # Return safe default
            return DeepSeekAnalysis(
                symbol=symbol,
                action='HOLD',
                confidence=0.0,
                reasoning=f"Error parsing response: {e}"
            )

    async def backtest_analysis(
        self,
        historical_trades: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Have DeepSeek analyze historical trades and provide improvement suggestions.

        Args:
            historical_trades: List of past trades with outcomes

        Returns:
            Performance metrics and suggestions
        """
        prompt = f"""Analyze these {len(historical_trades)} historical trades and identify patterns.

Trades data:
{historical_trades}

Provide:
1. Win rate analysis
2. Average profit/loss ratios
3. Best performing setups
4. Common mistakes
5. Suggested improvements

Remember your Alpha Arena strategy: selective entries, high R:R, patience."""

        messages = [
            {"role": "system", "content": "You are analyzing trading performance."},
            {"role": "user", "content": prompt}
        ]

        response = await self._make_request(messages, temperature=0.5)

        # Parse insights (simplified for now)
        return {
            "analysis": response,
            "suggestions_count": response.count("suggest")
        }
