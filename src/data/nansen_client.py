"""
Nansen MCP client for institutional smart money intelligence.

Provides:
- Smart money flow analysis
- Exchange netflow tracking
- Whale movement detection
- Token velocity metrics
- VC/Foundation accumulation patterns
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from src.core.logger import get_logger, LogCategory


class NansenSignalType(str, Enum):
    """Types of Nansen signals."""
    SMART_MONEY_FLOW = "smart_money_flow"
    EXCHANGE_NETFLOW = "exchange_netflow"
    WHALE_MOVEMENT = "whale_movement"
    TOKEN_VELOCITY = "token_velocity"
    HOLDER_CONCENTRATION = "holder_concentration"


class SignalStrength(str, Enum):
    """Signal strength classifications."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class SmartMoneyFlow:
    """Smart money flow data."""
    symbol: str
    net_position_change: float  # Percentage change
    top_100_net_buying: float  # Amount in USD
    smart_money_ratio: float  # Ratio of smart money volume
    timestamp: datetime
    signal_strength: SignalStrength


@dataclass
class ExchangeNetflow:
    """Exchange netflow data."""
    symbol: str
    netflow_24h: float  # Positive = inflow, negative = outflow
    netflow_7d: float
    major_exchange_flows: Dict[str, float]  # Exchange name -> flow
    timestamp: datetime


@dataclass
class WhaleMovement:
    """Whale/institutional movement data."""
    symbol: str
    wallet_type: str  # "VC", "Foundation", "Whale", "Institution"
    accumulation: bool  # True = accumulating, False = distributing
    amount_usd: float
    wallet_address: str
    timestamp: datetime


@dataclass
class TokenVelocity:
    """Token velocity and holder metrics."""
    symbol: str
    velocity_7d: float  # Transactions per token
    holder_count: int
    holder_concentration_top10: float  # % held by top 10
    holder_concentration_top100: float  # % held by top 100
    timestamp: datetime


@dataclass
class NansenSignal:
    """Aggregated Nansen signal."""
    symbol: str
    signal_type: NansenSignalType
    signal_strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    data: Dict[str, Any]
    timestamp: datetime
    reasoning: str


class NansenMCPClient:
    """
    Client for Nansen MCP server.

    Queries Nansen for institutional intelligence every 2-3 minutes
    to identify smart money accumulation and distribution patterns.
    """

    def __init__(
        self,
        api_key: str,
        mcp_server_url: str = "http://localhost:3000",
        query_interval: int = 150  # 2.5 minutes
    ):
        """
        Initialize Nansen MCP client.

        Args:
            api_key: Nansen API key
            mcp_server_url: MCP server URL
            query_interval: Query interval in seconds
        """
        self.api_key = api_key
        self.mcp_server_url = mcp_server_url
        self.query_interval = query_interval

        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger("nansen_client")

        # Cache for recent signals
        self.signal_cache: Dict[str, List[NansenSignal]] = {}
        self.max_cache_age = timedelta(hours=1)

        # Signal weights (will be adjusted by AI learning)
        self.signal_weights = {
            NansenSignalType.SMART_MONEY_FLOW: 0.35,
            NansenSignalType.EXCHANGE_NETFLOW: 0.25,
            NansenSignalType.WHALE_MOVEMENT: 0.25,
            NansenSignalType.TOKEN_VELOCITY: 0.15
        }

    async def init(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make request to Nansen MCP server.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data
        """
        if not self.session:
            await self.init()

        url = f"{self.mcp_server_url}/{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                self.logger.debug(
                    f"Nansen API request: {endpoint}",
                    category=LogCategory.NANSEN,
                    endpoint=endpoint
                )

                return data

        except aiohttp.ClientError as e:
            self.logger.error(
                f"Nansen API error: {e}",
                category=LogCategory.NANSEN,
                endpoint=endpoint,
                error=str(e)
            )
            raise

    async def get_smart_money_flow(self, symbol: str) -> SmartMoneyFlow:
        """
        Get smart money flow data.

        Args:
            symbol: Trading pair symbol (e.g., "SOL")

        Returns:
            SmartMoneyFlow data
        """
        data = await self._make_request(
            "smart-money/flow",
            params={"symbol": symbol, "timeframe": "24h"}
        )

        # Parse response (adjust based on actual Nansen MCP format)
        net_change = data.get("net_position_change_pct", 0)
        top_100_buying = data.get("top_100_net_buying_usd", 0)
        smart_ratio = data.get("smart_money_volume_ratio", 0)

        # Determine signal strength
        if net_change > 30:
            strength = SignalStrength.STRONG_BUY
        elif net_change > 15:
            strength = SignalStrength.BUY
        elif net_change < -30:
            strength = SignalStrength.STRONG_SELL
        elif net_change < -15:
            strength = SignalStrength.SELL
        else:
            strength = SignalStrength.NEUTRAL

        return SmartMoneyFlow(
            symbol=symbol,
            net_position_change=net_change,
            top_100_net_buying=top_100_buying,
            smart_money_ratio=smart_ratio,
            timestamp=datetime.now(timezone.utc),
            signal_strength=strength
        )

    async def get_exchange_netflow(self, symbol: str) -> ExchangeNetflow:
        """
        Get exchange netflow data.

        Args:
            symbol: Trading pair symbol

        Returns:
            ExchangeNetflow data
        """
        data = await self._make_request(
            "exchange/netflow",
            params={"symbol": symbol}
        )

        return ExchangeNetflow(
            symbol=symbol,
            netflow_24h=data.get("netflow_24h", 0),
            netflow_7d=data.get("netflow_7d", 0),
            major_exchange_flows=data.get("exchange_flows", {}),
            timestamp=datetime.now(timezone.utc)
        )

    async def get_whale_movements(self, symbol: str, min_usd: float = 100000) -> List[WhaleMovement]:
        """
        Get whale movement data.

        Args:
            symbol: Trading pair symbol
            min_usd: Minimum movement size in USD

        Returns:
            List of whale movements
        """
        data = await self._make_request(
            "whale/movements",
            params={"symbol": symbol, "min_usd": min_usd, "timeframe": "24h"}
        )

        movements = []
        for movement in data.get("movements", []):
            movements.append(WhaleMovement(
                symbol=symbol,
                wallet_type=movement.get("wallet_type", "Unknown"),
                accumulation=movement.get("direction") == "accumulation",
                amount_usd=movement.get("amount_usd", 0),
                wallet_address=movement.get("wallet_address", ""),
                timestamp=datetime.fromisoformat(movement.get("timestamp"))
            ))

        return movements

    async def get_token_velocity(self, symbol: str) -> TokenVelocity:
        """
        Get token velocity and holder metrics.

        Args:
            symbol: Trading pair symbol

        Returns:
            TokenVelocity data
        """
        data = await self._make_request(
            "token/velocity",
            params={"symbol": symbol}
        )

        return TokenVelocity(
            symbol=symbol,
            velocity_7d=data.get("velocity_7d", 0),
            holder_count=data.get("holder_count", 0),
            holder_concentration_top10=data.get("top10_concentration_pct", 0),
            holder_concentration_top100=data.get("top100_concentration_pct", 0),
            timestamp=datetime.now(timezone.utc)
        )

    async def analyze_symbol(self, symbol: str) -> List[NansenSignal]:
        """
        Comprehensive analysis of a symbol using all Nansen data.

        Args:
            symbol: Trading pair symbol

        Returns:
            List of Nansen signals
        """
        self.logger.info(
            f"Analyzing {symbol} with Nansen data",
            category=LogCategory.NANSEN,
            symbol=symbol
        )

        signals = []

        try:
            # Get all data sources in parallel
            smart_money, netflow, whales, velocity = await asyncio.gather(
                self.get_smart_money_flow(symbol),
                self.get_exchange_netflow(symbol),
                self.get_whale_movements(symbol),
                self.get_token_velocity(symbol),
                return_exceptions=True
            )

            # Analyze smart money flow
            if isinstance(smart_money, SmartMoneyFlow):
                confidence = min(abs(smart_money.net_position_change) / 50, 1.0)
                signals.append(NansenSignal(
                    symbol=symbol,
                    signal_type=NansenSignalType.SMART_MONEY_FLOW,
                    signal_strength=smart_money.signal_strength,
                    confidence=confidence,
                    data={
                        "net_change_pct": smart_money.net_position_change,
                        "top_100_buying": smart_money.top_100_net_buying,
                        "smart_ratio": smart_money.smart_money_ratio
                    },
                    timestamp=smart_money.timestamp,
                    reasoning=f"Smart money {smart_money.net_position_change:+.1f}% position change"
                ))

            # Analyze exchange netflow
            if isinstance(netflow, ExchangeNetflow):
                # Outflow (negative) is bullish, inflow (positive) is bearish
                if netflow.netflow_24h < -1_000_000:
                    strength = SignalStrength.STRONG_BUY
                    reasoning = f"Strong outflow: ${abs(netflow.netflow_24h/1e6):.1f}M"
                elif netflow.netflow_24h < -500_000:
                    strength = SignalStrength.BUY
                    reasoning = f"Moderate outflow: ${abs(netflow.netflow_24h/1e6):.1f}M"
                elif netflow.netflow_24h > 1_000_000:
                    strength = SignalStrength.STRONG_SELL
                    reasoning = f"Strong inflow: ${netflow.netflow_24h/1e6:.1f}M"
                elif netflow.netflow_24h > 500_000:
                    strength = SignalStrength.SELL
                    reasoning = f"Moderate inflow: ${netflow.netflow_24h/1e6:.1f}M"
                else:
                    strength = SignalStrength.NEUTRAL
                    reasoning = "Neutral netflow"

                confidence = min(abs(netflow.netflow_24h) / 2_000_000, 1.0)

                signals.append(NansenSignal(
                    symbol=symbol,
                    signal_type=NansenSignalType.EXCHANGE_NETFLOW,
                    signal_strength=strength,
                    confidence=confidence,
                    data={
                        "netflow_24h": netflow.netflow_24h,
                        "netflow_7d": netflow.netflow_7d
                    },
                    timestamp=netflow.timestamp,
                    reasoning=reasoning
                ))

            # Analyze whale movements
            if isinstance(whales, list) and whales:
                accumulating = sum(1 for w in whales if w.accumulation)
                distributing = len(whales) - accumulating

                if accumulating > distributing * 2:
                    strength = SignalStrength.STRONG_BUY
                    reasoning = f"{accumulating} whales accumulating vs {distributing} distributing"
                elif accumulating > distributing:
                    strength = SignalStrength.BUY
                    reasoning = f"{accumulating} whales accumulating"
                elif distributing > accumulating * 2:
                    strength = SignalStrength.STRONG_SELL
                    reasoning = f"{distributing} whales distributing"
                elif distributing > accumulating:
                    strength = SignalStrength.SELL
                    reasoning = f"{distributing} whales distributing"
                else:
                    strength = SignalStrength.NEUTRAL
                    reasoning = "Balanced whale activity"

                total_accumulation = sum(w.amount_usd for w in whales if w.accumulation)
                confidence = min(total_accumulation / 10_000_000, 1.0)

                signals.append(NansenSignal(
                    symbol=symbol,
                    signal_type=NansenSignalType.WHALE_MOVEMENT,
                    signal_strength=strength,
                    confidence=confidence,
                    data={
                        "accumulating_count": accumulating,
                        "distributing_count": distributing,
                        "total_accumulation_usd": total_accumulation
                    },
                    timestamp=datetime.now(timezone.utc),
                    reasoning=reasoning
                ))

            # Cache signals
            self.signal_cache[symbol] = signals

            self.logger.info(
                f"Generated {len(signals)} Nansen signals for {symbol}",
                category=LogCategory.NANSEN,
                symbol=symbol,
                signal_count=len(signals)
            )

        except Exception as e:
            self.logger.error(
                f"Error analyzing {symbol}: {e}",
                category=LogCategory.NANSEN,
                error=str(e)
            )

        return signals

    def get_aggregated_signal(self, signals: List[NansenSignal]) -> Dict[str, Any]:
        """
        Aggregate multiple Nansen signals into single decision.

        Args:
            signals: List of Nansen signals

        Returns:
            Aggregated signal with action and confidence
        """
        if not signals:
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "reasoning": "No Nansen signals available"
            }

        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0

        signal_details = []

        for signal in signals:
            weight = self.signal_weights.get(signal.signal_type, 0.25)

            # Convert signal strength to numeric score (-1 to +1)
            if signal.signal_strength == SignalStrength.STRONG_BUY:
                score = 1.0
            elif signal.signal_strength == SignalStrength.BUY:
                score = 0.5
            elif signal.signal_strength == SignalStrength.SELL:
                score = -0.5
            elif signal.signal_strength == SignalStrength.STRONG_SELL:
                score = -1.0
            else:
                score = 0.0

            weighted_score = score * weight * signal.confidence
            total_score += weighted_score
            total_weight += weight

            signal_details.append({
                "type": signal.signal_type.value,
                "strength": signal.signal_strength.value,
                "confidence": signal.confidence,
                "reasoning": signal.reasoning
            })

        # Normalize score
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0.0

        # Determine action
        if normalized_score > 0.4:
            action = "BUY"
        elif normalized_score < -0.4:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "action": action,
            "confidence": abs(normalized_score),
            "score": normalized_score,
            "signals": signal_details,
            "reasoning": f"Aggregated {len(signals)} signals with weighted score {normalized_score:.2f}"
        }

    def update_signal_weights(self, new_weights: Dict[NansenSignalType, float]):
        """
        Update signal weights (used by AI learning system).

        Args:
            new_weights: New weight mapping
        """
        self.signal_weights.update(new_weights)

        self.logger.info(
            "Updated Nansen signal weights",
            category=LogCategory.NANSEN,
            weights=self.signal_weights
        )
