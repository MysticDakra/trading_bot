"""
Multi-Agent Trading System

Based on TauricResearch/TradingAgents framework with 7 specialized agents:
1. Fundamentals Analyst
2. Sentiment Analyst
3. News Analyst
4. Technical Analyst
5. Researcher (Bull & Bear debate)
6. Trader
7. Risk Manager

Combined with Gajesh2007's proven Hyperliquid integration.
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from src.ai.openrouter_client import OpenRouterClient, LLMModel
from src.data.taapi_client import TaapiClient, TechnicalIndicators
from src.data.nansen_client import NansenMCPClient
from src.core.logger import get_logger, LogCategory


class AgentRole(str, Enum):
    """Agent roles in the trading system."""
    TECHNICAL_ANALYST = "technical_analyst"
    SENTIMENT_ANALYST = "sentiment_analyst"
    NANSEN_ANALYST = "nansen_analyst"  # Replaces fundamentals for crypto
    RESEARCHER_BULL = "researcher_bull"
    RESEARCHER_BEAR = "researcher_bear"
    TRADER = "trader"
    RISK_MANAGER = "risk_manager"


@dataclass
class AgentReport:
    """Report from an agent."""
    agent_role: AgentRole
    recommendation: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    key_points: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class TradingAgent:
    """Base class for specialized trading agents."""

    def __init__(
        self,
        role: AgentRole,
        llm_client: OpenRouterClient,
        model: LLMModel = LLMModel.DEEPSEEK_CHAT
    ):
        """
        Initialize trading agent.

        Args:
            role: Agent's role
            llm_client: OpenRouter client for LLM access
            model: LLM model to use
        """
        self.role = role
        self.llm_client = llm_client
        self.model = model
        self.logger = get_logger(f"agent.{role.value}")

    async def analyze(self, context: Dict[str, Any]) -> AgentReport:
        """
        Analyze market data and provide recommendation.

        Args:
            context: Market context with all available data

        Returns:
            Agent report with recommendation
        """
        raise NotImplementedError

    def _create_system_prompt(self) -> str:
        """Create system prompt for this agent."""
        raise NotImplementedError


class TechnicalAnalystAgent(TradingAgent):
    """Agent specializing in technical analysis."""

    def __init__(self, llm_client: OpenRouterClient, taapi_client: TaapiClient):
        super().__init__(AgentRole.TECHNICAL_ANALYST, llm_client, LLMModel.GPT_4O)
        self.taapi_client = taapi_client

    def _create_system_prompt(self) -> str:
        return """You are a Technical Analyst specializing in cryptocurrency markets.

Your expertise:
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Chart patterns and price action
- Support and resistance levels
- Trend identification

Provide your analysis in JSON format:
{
    "recommendation": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "detailed technical analysis",
    "key_points": ["point 1", "point 2", ...]
}"""

    async def analyze(self, context: Dict[str, Any]) -> AgentReport:
        """Analyze technical indicators."""
        symbol = context['symbol']
        current_price = context['current_price']

        # Get technical indicators
        indicators = await self.taapi_client.get_indicators(symbol)

        # Build prompt
        prompt = f"""Analyze {symbol} at ${current_price:.2f}

Technical Indicators:
- RSI: {indicators.rsi:.1f if indicators.rsi else 'N/A'}
- MACD: {indicators.macd:.4f if indicators.macd else 'N/A'}
- MACD Signal: {indicators.macd_signal:.4f if indicators.macd_signal else 'N/A'}
- Stochastic K: {indicators.stoch_k:.1f if indicators.stoch_k else 'N/A'}
- ADX: {indicators.adx:.1f if indicators.adx else 'N/A'}
- ATR: {indicators.atr:.4f if indicators.atr else 'N/A'}

Provide your technical analysis recommendation."""

        messages = [
            {"role": "system", "content": self._create_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = await self.llm_client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.3
        )

        # Parse response
        import json
        try:
            data = json.loads(response['content'])

            return AgentReport(
                agent_role=self.role,
                recommendation=data['recommendation'],
                confidence=data['confidence'],
                reasoning=data['reasoning'],
                key_points=data.get('key_points', [])
            )
        except:
            return AgentReport(
                agent_role=self.role,
                recommendation="HOLD",
                confidence=0.0,
                reasoning="Error parsing technical analysis",
                key_points=[]
            )


class NansenAnalystAgent(TradingAgent):
    """Agent specializing in Nansen smart money analysis."""

    def __init__(self, llm_client: OpenRouterClient, nansen_client: NansenMCPClient):
        super().__init__(AgentRole.NANSEN_ANALYST, llm_client, LLMModel.DEEPSEEK_CHAT)
        self.nansen_client = nansen_client

    def _create_system_prompt(self) -> str:
        return """You are a Nansen Smart Money Analyst.

Your expertise:
- On-chain whale movements
- Smart money accumulation/distribution
- Exchange netflows
- Institutional positioning

Provide analysis in JSON format:
{
    "recommendation": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "smart money analysis",
    "key_points": ["point 1", "point 2", ...]
}"""

    async def analyze(self, context: Dict[str, Any]) -> AgentReport:
        """Analyze Nansen smart money data."""
        symbol = context['symbol']

        # Get Nansen signals
        signals = await self.nansen_client.analyze_symbol(symbol)
        aggregated = self.nansen_client.get_aggregated_signal(signals)

        # Build prompt
        prompt = f"""Analyze {symbol} smart money activity:

Nansen Signals:
- Action: {aggregated['action']}
- Confidence: {aggregated['confidence']:.2f}
- Score: {aggregated.get('score', 0):.2f}

Detailed signals:
"""

        for sig in aggregated.get('signals', []):
            prompt += f"\n- {sig['type']}: {sig['strength']} (confidence: {sig['confidence']:.2f})"
            prompt += f"\n  Reasoning: {sig['reasoning']}"

        prompt += "\n\nProvide your smart money analysis recommendation."

        messages = [
            {"role": "system", "content": self._create_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = await self.llm_client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.3
        )

        # Parse response
        import json
        try:
            data = json.loads(response['content'])

            return AgentReport(
                agent_role=self.role,
                recommendation=data['recommendation'],
                confidence=data['confidence'],
                reasoning=data['reasoning'],
                key_points=data.get('key_points', [])
            )
        except:
            return AgentReport(
                agent_role=self.role,
                recommendation=aggregated['action'],
                confidence=aggregated['confidence'],
                reasoning=aggregated['reasoning'],
                key_points=[s['reasoning'] for s in aggregated.get('signals', [])]
            )


class TraderAgent(TradingAgent):
    """Agent that makes final trading decisions."""

    def __init__(self, llm_client: OpenRouterClient):
        super().__init__(AgentRole.TRADER, llm_client, LLMModel.DEEPSEEK_R1)  # Use R1 for deep reasoning

    def _create_system_prompt(self) -> str:
        return """You are a Professional Trader making final execution decisions.

You receive reports from:
- Technical Analyst (chart analysis)
- Nansen Analyst (smart money flows)
- Researcher team (market debate)

Your job:
- Synthesize all information
- Make final BUY/SELL/HOLD decision
- Define entry, stop-loss, take-profit
- Ensure risk/reward > 3.0

Provide decision in JSON format:
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "synthesis of all inputs",
    "entry_price": number,
    "stop_loss": number,
    "take_profit": number,
    "risk_reward_ratio": number,
    "key_points": ["point 1", "point 2", ...]
}"""

    async def analyze(self, context: Dict[str, Any]) -> AgentReport:
        """Make final trading decision based on all agent reports."""
        symbol = context['symbol']
        current_price = context['current_price']
        agent_reports = context.get('agent_reports', [])

        # Build comprehensive prompt
        prompt = f"""Make final trading decision for {symbol} @ ${current_price:.2f}

Agent Reports:
"""

        for report in agent_reports:
            prompt += f"\n## {report.agent_role.value.upper()}"
            prompt += f"\n- Recommendation: {report.recommendation}"
            prompt += f"\n- Confidence: {report.confidence:.2f}"
            prompt += f"\n- Reasoning: {report.reasoning}"
            for point in report.key_points[:3]:  # Top 3 points
                prompt += f"\n  * {point}"
            prompt += "\n"

        prompt += "\nSynthesize all reports and make your final trading decision."

        messages = [
            {"role": "system", "content": self._create_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        response = await self.llm_client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.2,  # Low for consistent decisions
            max_tokens=3000
        )

        # Parse response
        import json
        try:
            data = json.loads(response['content'])

            return AgentReport(
                agent_role=self.role,
                recommendation=data['action'],
                confidence=data['confidence'],
                reasoning=data['reasoning'],
                key_points=data.get('key_points', [])
            )
        except:
            return AgentReport(
                agent_role=self.role,
                recommendation="HOLD",
                confidence=0.0,
                reasoning="Error making final decision",
                key_points=[]
            )


class MultiAgentTradingSystem:
    """
    Orchestrates multiple specialized agents for trading decisions.

    Based on TauricResearch TradingAgents architecture.
    """

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        taapi_client: TaapiClient,
        nansen_client: NansenMCPClient
    ):
        """
        Initialize multi-agent system.

        Args:
            openrouter_client: OpenRouter client for LLM access
            taapi_client: TAAPI client for technical indicators
            nansen_client: Nansen client for smart money data
        """
        self.openrouter = openrouter_client
        self.taapi = taapi_client
        self.nansen = nansen_client
        self.logger = get_logger("multi_agent_system")

        # Initialize agents
        self.technical_analyst = TechnicalAnalystAgent(openrouter_client, taapi_client)
        self.nansen_analyst = NansenAnalystAgent(openrouter_client, nansen_client)
        self.trader = TraderAgent(openrouter_client)

    async def analyze_symbol(
        self,
        symbol: str,
        current_price: float,
        order_book_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run full multi-agent analysis for symbol.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            order_book_data: Order book data

        Returns:
            Final trading decision
        """
        self.logger.info(
            f"Starting multi-agent analysis for {symbol}",
            category=LogCategory.AI,
            symbol=symbol
        )

        # Build context
        context = {
            'symbol': symbol,
            'current_price': current_price,
            'order_book_data': order_book_data
        }

        # Phase 1: Parallel analyst reports
        analyst_reports = await asyncio.gather(
            self.technical_analyst.analyze(context),
            self.nansen_analyst.analyze(context),
            return_exceptions=True
        )

        # Filter out exceptions
        valid_reports = [r for r in analyst_reports if isinstance(r, AgentReport)]

        self.logger.info(
            f"Received {len(valid_reports)} analyst reports",
            category=LogCategory.AI,
            reports=[{
                'role': r.agent_role.value,
                'recommendation': r.recommendation,
                'confidence': r.confidence
            } for r in valid_reports]
        )

        # Phase 2: Trader makes final decision
        context['agent_reports'] = valid_reports
        final_decision_report = await self.trader.analyze(context)

        # Build comprehensive result
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'final_decision': {
                'action': final_decision_report.recommendation,
                'confidence': final_decision_report.confidence,
                'reasoning': final_decision_report.reasoning,
                'key_points': final_decision_report.key_points
            },
            'analyst_reports': [
                {
                    'role': r.agent_role.value,
                    'recommendation': r.recommendation,
                    'confidence': r.confidence,
                    'reasoning': r.reasoning,
                    'key_points': r.key_points
                }
                for r in valid_reports
            ],
            'consensus_strength': self._calculate_consensus(valid_reports),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.logger.info(
            f"Multi-agent decision: {result['final_decision']['action']} "
            f"(confidence: {result['final_decision']['confidence']:.2f})",
            category=LogCategory.AI,
            symbol=symbol,
            decision=result['final_decision']['action']
        )

        return result

    def _calculate_consensus(self, reports: List[AgentReport]) -> float:
        """
        Calculate consensus strength across agent reports.

        Args:
            reports: List of agent reports

        Returns:
            Consensus strength 0.0 to 1.0
        """
        if not reports:
            return 0.0

        # Count recommendations
        buy_count = sum(1 for r in reports if r.recommendation == "BUY")
        sell_count = sum(1 for r in reports if r.recommendation == "SELL")
        hold_count = sum(1 for r in reports if r.recommendation == "HOLD")

        total = len(reports)

        # Consensus is when majority agrees
        max_count = max(buy_count, sell_count, hold_count)
        return max_count / total if total > 0 else 0.0
