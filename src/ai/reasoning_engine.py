"""
Continuous AI reasoning engine that queries Nansen data and makes trading decisions.

Implements self-questioning framework:
- "What Nansen insight gives edge right now?"
- "How do smart money flows align with price?"
- "What institutional accumulation patterns exist?"
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from src.data.nansen_client import NansenMCPClient, NansenSignal
from src.data.market_data import OrderBook
from src.core.logger import get_logger, LogCategory


class TradingAction(str, Enum):
    """Trading actions."""
    BUY = "BUY"
    SELL = "SELL"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass
class TradingDecision:
    """Trading decision output from reasoning engine."""
    cycle_id: str
    timestamp: datetime
    asset: str
    action: TradingAction
    size_percent: float  # Percentage of capital to deploy
    leverage: int
    confidence: float  # 0.0 to 1.0
    entry_logic: str
    nansen_insights: Dict[str, Any]
    technical_insights: Optional[Dict[str, Any]] = None
    reasoning: str = ""


class ReasoningCycle:
    """Single reasoning cycle."""

    def __init__(
        self,
        cycle_id: str,
        symbol: str,
        nansen_signals: List[NansenSignal],
        order_book: Optional[OrderBook] = None,
        current_price: Optional[float] = None
    ):
        self.cycle_id = cycle_id
        self.symbol = symbol
        self.nansen_signals = nansen_signals
        self.order_book = order_book
        self.current_price = current_price
        self.timestamp = datetime.now(timezone.utc)

        self.questions: List[str] = []
        self.answers: Dict[str, str] = {}
        self.insights: List[str] = []

    def ask_question(self, question: str) -> str:
        """
        Ask a self-reflective question and generate answer.

        Args:
            question: Question to ask

        Returns:
            Answer based on available data
        """
        self.questions.append(question)

        # Answer based on available data
        answer = self._answer_question(question)
        self.answers[question] = answer

        return answer

    def _answer_question(self, question: str) -> str:
        """Generate answer to question based on data."""

        question_lower = question.lower()

        # Question about Nansen insights
        if "nansen" in question_lower or "smart money" in question_lower:
            if not self.nansen_signals:
                return "No Nansen data available for analysis."

            insights = []
            for signal in self.nansen_signals:
                insights.append(
                    f"{signal.signal_type.value}: {signal.signal_strength.value} "
                    f"(confidence: {signal.confidence:.2f}) - {signal.reasoning}"
                )

            return " | ".join(insights)

        # Question about price alignment
        elif "price" in question_lower or "align" in question_lower:
            if not self.order_book or not self.current_price:
                return "Insufficient price data for alignment analysis."

            imbalance = self.order_book.get_imbalance(depth=5)
            if imbalance is None:
                return "Unable to calculate order book imbalance."

            # Check if smart money aligns with price action
            bullish_signals = sum(
                1 for s in self.nansen_signals
                if "buy" in s.signal_strength.value
            )
            bearish_signals = sum(
                1 for s in self.nansen_signals
                if "sell" in s.signal_strength.value
            )

            if bullish_signals > bearish_signals and imbalance > 0.3:
                return f"ALIGNED: {bullish_signals} bullish Nansen signals + {imbalance:.2f} order book imbalance"
            elif bearish_signals > bullish_signals and imbalance < -0.3:
                return f"ALIGNED: {bearish_signals} bearish Nansen signals + {imbalance:.2f} order book imbalance"
            else:
                return "MISALIGNED: Nansen signals don't match order book dynamics"

        # Question about accumulation patterns
        elif "accumulation" in question_lower or "pattern" in question_lower:
            whale_signals = [
                s for s in self.nansen_signals
                if "whale" in s.signal_type.value
            ]

            if not whale_signals:
                return "No whale movement data available."

            whale_signal = whale_signals[0]
            acc_count = whale_signal.data.get("accumulating_count", 0)
            dist_count = whale_signal.data.get("distributing_count", 0)

            if acc_count > dist_count:
                return f"ACCUMULATION PATTERN: {acc_count} whales accumulating, {dist_count} distributing"
            else:
                return f"DISTRIBUTION PATTERN: {dist_count} whales distributing, {acc_count} accumulating"

        # Default answer
        return "Insufficient data to answer this question."

    def generate_insights(self) -> List[str]:
        """Generate trading insights from Q&A."""
        self.insights = []

        # Analyze Nansen signal consensus
        buy_signals = sum(1 for s in self.nansen_signals if "buy" in s.signal_strength.value)
        sell_signals = sum(1 for s in self.nansen_signals if "sell" in s.signal_strength.value)

        if buy_signals >= 3:
            self.insights.append(f"STRONG NANSEN CONSENSUS: {buy_signals} bullish signals")
        elif sell_signals >= 3:
            self.insights.append(f"STRONG NANSEN CONSENSUS: {sell_signals} bearish signals")

        # Check for rare high-conviction setups
        high_confidence_signals = [s for s in self.nansen_signals if s.confidence > 0.8]
        if high_confidence_signals:
            self.insights.append(
                f"HIGH CONVICTION: {len(high_confidence_signals)} signals with >0.8 confidence"
            )

        # Order book analysis
        if self.order_book:
            imbalance = self.order_book.get_imbalance(depth=5)
            if imbalance and abs(imbalance) > 0.6:
                direction = "bullish" if imbalance > 0 else "bearish"
                self.insights.append(f"STRONG ORDER BOOK IMBALANCE: {imbalance:.2f} ({direction})")

        return self.insights


class ContinuousReasoningEngine:
    """
    Continuous reasoning engine that queries Nansen every 2-3 minutes
    and generates trading decisions through self-questioning.
    """

    def __init__(
        self,
        nansen_client: NansenMCPClient,
        symbols: List[str],
        query_interval: int = 150  # 2.5 minutes
    ):
        """
        Initialize reasoning engine.

        Args:
            nansen_client: Nansen MCP client
            symbols: List of symbols to analyze
            query_interval: Query interval in seconds
        """
        self.nansen_client = nansen_client
        self.symbols = symbols
        self.query_interval = query_interval

        self.logger = get_logger("reasoning_engine")

        # Tracking
        self.cycle_count = 0
        self.decisions: List[TradingDecision] = []

        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Market data (to be updated externally)
        self.order_books: Dict[str, OrderBook] = {}
        self.current_prices: Dict[str, float] = {}

    def update_market_data(self, symbol: str, order_book: OrderBook, price: float):
        """
        Update market data for symbol.

        Args:
            symbol: Trading pair symbol
            order_book: Current order book
            price: Current price
        """
        self.order_books[symbol] = order_book
        self.current_prices[symbol] = price

    async def run_reasoning_cycle(self, symbol: str) -> Optional[TradingDecision]:
        """
        Run a single reasoning cycle for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Trading decision or None
        """
        self.cycle_count += 1
        cycle_id = f"cycle_{self.cycle_count:06d}_{symbol}"

        self.logger.info(
            f"Starting reasoning cycle {cycle_id}",
            category=LogCategory.AI,
            cycle_id=cycle_id,
            symbol=symbol
        )

        try:
            # Query Nansen
            nansen_signals = await self.nansen_client.analyze_symbol(symbol)

            # Create reasoning cycle
            cycle = ReasoningCycle(
                cycle_id=cycle_id,
                symbol=symbol,
                nansen_signals=nansen_signals,
                order_book=self.order_books.get(symbol),
                current_price=self.current_prices.get(symbol)
            )

            # Self-questioning framework
            q1 = "What Nansen insight gives edge right now?"
            a1 = cycle.ask_question(q1)

            q2 = "How do smart money flows align with price?"
            a2 = cycle.ask_question(q2)

            q3 = "What institutional accumulation patterns exist?"
            a3 = cycle.ask_question(q3)

            # Generate insights
            insights = cycle.generate_insights()

            # Log reasoning process
            self.logger.info(
                f"Reasoning cycle Q&A completed",
                category=LogCategory.AI,
                cycle_id=cycle_id,
                questions=[q1, q2, q3],
                answers=[a1, a2, a3],
                insights=insights
            )

            # Make trading decision
            decision = self._make_decision(cycle)

            if decision:
                self.decisions.append(decision)

                # Log decision to database
                await self.logger.log_decision(
                    cycle_id=cycle_id,
                    decision_type="trading",
                    asset=symbol,
                    action=decision.action.value,
                    confidence=decision.confidence,
                    reasoning=decision.reasoning,
                    nansen_data={
                        "signals": [
                            {
                                "type": s.signal_type.value,
                                "strength": s.signal_strength.value,
                                "confidence": s.confidence
                            }
                            for s in nansen_signals
                        ],
                        "aggregated": decision.nansen_insights
                    }
                )

            return decision

        except Exception as e:
            self.logger.error(
                f"Error in reasoning cycle: {e}",
                category=LogCategory.AI,
                cycle_id=cycle_id,
                error=str(e)
            )
            return None

    def _make_decision(self, cycle: ReasoningCycle) -> Optional[TradingDecision]:
        """
        Make trading decision based on reasoning cycle.

        Args:
            cycle: Completed reasoning cycle

        Returns:
            Trading decision or None
        """
        # Get aggregated Nansen signal
        nansen_aggregated = self.nansen_client.get_aggregated_signal(cycle.nansen_signals)

        action_str = nansen_aggregated.get("action", "HOLD")
        confidence = nansen_aggregated.get("confidence", 0.0)

        # Minimum confidence threshold
        if confidence < 0.5:
            self.logger.debug(
                f"Confidence {confidence:.2f} below threshold, no action",
                category=LogCategory.AI,
                symbol=cycle.symbol
            )
            return None

        # Determine position size based on confidence
        if confidence > 0.9:
            size_percent = 25  # 25% of capital
            leverage = 5
        elif confidence > 0.75:
            size_percent = 18  # 18% of capital
            leverage = 4
        else:
            size_percent = 12  # 12% of capital
            leverage = 3

        # Check for order book confirmation
        entry_logic = "nansen_signal"
        if cycle.order_book:
            imbalance = cycle.order_book.get_imbalance(depth=5)
            if imbalance and abs(imbalance) > 0.6:
                entry_logic = "nansen_plus_orderbook"
                # Boost confidence slightly
                confidence = min(confidence * 1.1, 1.0)

        # Map action
        if action_str == "BUY":
            action = TradingAction.BUY
        elif action_str == "SELL":
            action = TradingAction.SELL
        else:
            action = TradingAction.HOLD

        # Build reasoning
        reasoning_parts = [
            f"Nansen: {nansen_aggregated.get('reasoning', '')}",
            f"Insights: {', '.join(cycle.insights)}",
            f"Q&A highlights: {list(cycle.answers.values())[:2]}"
        ]

        decision = TradingDecision(
            cycle_id=cycle.cycle_id,
            timestamp=cycle.timestamp,
            asset=cycle.symbol,
            action=action,
            size_percent=size_percent,
            leverage=leverage,
            confidence=confidence,
            entry_logic=entry_logic,
            nansen_insights=nansen_aggregated,
            reasoning=" | ".join(reasoning_parts)
        )

        self.logger.info(
            f"Decision: {action.value} {cycle.symbol} (confidence: {confidence:.2f})",
            category=LogCategory.AI,
            decision=decision.__dict__
        )

        return decision

    async def _reasoning_loop(self):
        """Main continuous reasoning loop."""
        while self._running:
            try:
                # Run reasoning cycle for each symbol
                for symbol in self.symbols:
                    if not self._running:
                        break

                    await self.run_reasoning_cycle(symbol)

                # Wait for next cycle
                await asyncio.sleep(self.query_interval)

            except Exception as e:
                self.logger.error(
                    f"Error in reasoning loop: {e}",
                    category=LogCategory.AI,
                    error=str(e)
                )
                await asyncio.sleep(60)  # Wait before retry

    async def start(self):
        """Start continuous reasoning engine."""
        if self._running:
            self.logger.warning(
                "Reasoning engine already running",
                category=LogCategory.AI
            )
            return

        self._running = True
        self._task = asyncio.create_task(self._reasoning_loop())

        self.logger.info(
            f"Reasoning engine started (interval: {self.query_interval}s)",
            category=LogCategory.AI,
            symbols=self.symbols
        )

    async def stop(self):
        """Stop reasoning engine."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.logger.info(
            "Reasoning engine stopped",
            category=LogCategory.AI
        )

    def get_latest_decision(self, symbol: str) -> Optional[TradingDecision]:
        """Get latest decision for symbol."""
        for decision in reversed(self.decisions):
            if decision.asset == symbol:
                return decision
        return None

    def get_decision_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[TradingDecision]:
        """
        Get decision history.

        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of decisions to return

        Returns:
            List of decisions
        """
        if symbol:
            decisions = [d for d in self.decisions if d.asset == symbol]
        else:
            decisions = self.decisions

        return decisions[-limit:]
