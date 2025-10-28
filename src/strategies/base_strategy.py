"""
Base strategy class and common utilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from src.data.market_data import OrderBook
from src.data.nansen_client import NansenSignal
from src.core.logger import get_logger, LogCategory


class SignalType(str, Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """Trading signal from a strategy."""
    strategy_name: str
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    leverage: Optional[int] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StrategyPerformance:
    """Strategy performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

    def update(self, pnl: float):
        """Update performance metrics with new trade result."""
        self.total_trades += 1

        if pnl > 0:
            self.winning_trades += 1
            self.avg_win = (
                (self.avg_win * (self.winning_trades - 1) + pnl) / self.winning_trades
            )
        elif pnl < 0:
            self.losing_trades += 1
            self.avg_loss = (
                (self.avg_loss * (self.losing_trades - 1) + abs(pnl)) / self.losing_trades
            )

        self.total_pnl += pnl

        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    All strategies must implement:
    - analyze(): Generate trading signals
    - on_order_book_update(): React to order book changes
    - on_nansen_signal(): React to Nansen signals
    """

    def __init__(self, name: str, enabled: bool = True):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            enabled: Whether strategy is enabled
        """
        self.name = name
        self.enabled = enabled
        self.logger = get_logger(f"strategy.{name}")

        # Performance tracking
        self.performance = StrategyPerformance()

        # State
        self.order_books: Dict[str, OrderBook] = {}
        self.nansen_signals: Dict[str, List[NansenSignal]] = {}
        self.current_prices: Dict[str, float] = {}

    @abstractmethod
    async def analyze(self, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze symbol and generate trading signal.

        Args:
            symbol: Trading pair symbol

        Returns:
            Trading signal or None
        """
        pass

    def update_order_book(self, symbol: str, order_book: OrderBook):
        """
        Update order book for symbol.

        Args:
            symbol: Trading pair symbol
            order_book: Updated order book
        """
        self.order_books[symbol] = order_book

    def update_nansen_signals(self, symbol: str, signals: List[NansenSignal]):
        """
        Update Nansen signals for symbol.

        Args:
            symbol: Trading pair symbol
            signals: List of Nansen signals
        """
        self.nansen_signals[symbol] = signals

    def update_price(self, symbol: str, price: float):
        """
        Update current price for symbol.

        Args:
            symbol: Trading pair symbol
            price: Current price
        """
        self.current_prices[symbol] = price

    def get_nansen_consensus(self, symbol: str) -> Dict[str, Any]:
        """
        Get Nansen signal consensus for symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict with consensus action and confidence
        """
        signals = self.nansen_signals.get(symbol, [])
        if not signals:
            return {"action": "HOLD", "confidence": 0.0}

        buy_signals = sum(1 for s in signals if "buy" in s.signal_strength.value)
        sell_signals = sum(1 for s in signals if "sell" in s.signal_strength.value)

        total_confidence = sum(s.confidence for s in signals)
        avg_confidence = total_confidence / len(signals) if signals else 0.0

        if buy_signals > sell_signals:
            return {"action": "BUY", "confidence": avg_confidence}
        elif sell_signals > buy_signals:
            return {"action": "SELL", "confidence": avg_confidence}
        else:
            return {"action": "HOLD", "confidence": avg_confidence}

    def record_trade_result(self, pnl: float):
        """
        Record trade result for performance tracking.

        Args:
            pnl: Trade P&L
        """
        self.performance.update(pnl)

        self.logger.info(
            f"Trade result recorded: ${pnl:.2f}",
            category=LogCategory.STRATEGY,
            strategy=self.name,
            pnl=pnl,
            win_rate=self.performance.win_rate,
            total_trades=self.performance.total_trades
        )

    def get_performance(self) -> StrategyPerformance:
        """Get strategy performance metrics."""
        return self.performance

    def enable(self):
        """Enable strategy."""
        self.enabled = True
        self.logger.info(
            f"Strategy {self.name} enabled",
            category=LogCategory.STRATEGY
        )

    def disable(self):
        """Disable strategy."""
        self.enabled = False
        self.logger.info(
            f"Strategy {self.name} disabled",
            category=LogCategory.STRATEGY
        )
