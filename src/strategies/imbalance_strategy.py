"""
Order Book Imbalance Strategy

Strategy logic:
- Calculate L5 order book imbalance: ρ = (V^bid - V^ask) / (V^bid + V^ask)
- Enter when ρ > 0.6 (strong buying pressure) AND Nansen shows accumulation
- Or ρ < -0.6 (strong selling pressure) AND Nansen shows distribution
- Hold for 30-60 seconds (scalping)
- Position size: $1,000 risk, 4x leverage
- Stop loss: 0.5% (50 bps)
- Take profit: 1.0% (100 bps)
"""

from typing import Optional
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.data.market_data import OrderBook
from src.core.logger import LogCategory


class OrderBookImbalanceStrategy(BaseStrategy):
    """
    Scalping strategy based on order book imbalance and Nansen confirmation.
    """

    def __init__(
        self,
        imbalance_threshold: float = 0.6,
        holding_period_seconds: int = 45,
        stop_loss_bps: float = 50,
        take_profit_bps: float = 100,
        nansen_confirmation_required: bool = True,
        enabled: bool = True
    ):
        """
        Initialize order book imbalance strategy.

        Args:
            imbalance_threshold: Minimum imbalance to trigger (0.6 = 60% on one side)
            holding_period_seconds: Target holding period
            stop_loss_bps: Stop loss in basis points
            take_profit_bps: Take profit in basis points
            nansen_confirmation_required: Require Nansen signal confirmation
            enabled: Whether strategy is enabled
        """
        super().__init__(name="OrderBookImbalance", enabled=enabled)

        self.imbalance_threshold = imbalance_threshold
        self.holding_period_seconds = holding_period_seconds
        self.stop_loss_bps = stop_loss_bps
        self.take_profit_bps = take_profit_bps
        self.nansen_confirmation_required = nansen_confirmation_required

    async def analyze(self, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze order book imbalance and generate signal.

        Args:
            symbol: Trading pair symbol

        Returns:
            Trading signal or None
        """
        if not self.enabled:
            return None

        # Get order book
        order_book = self.order_books.get(symbol)
        if not order_book:
            self.logger.debug(
                f"No order book data for {symbol}",
                category=LogCategory.STRATEGY
            )
            return None

        # Calculate imbalance
        imbalance = order_book.get_imbalance(depth=5)
        if imbalance is None:
            return None

        # Get current price
        current_price = order_book.get_mid_price()
        if current_price is None:
            return None

        # Check Nansen confirmation if required
        nansen_consensus = self.get_nansen_consensus(symbol)
        nansen_aligned = True

        if self.nansen_confirmation_required:
            if imbalance > self.imbalance_threshold:
                # Need bullish Nansen signal
                nansen_aligned = nansen_consensus["action"] == "BUY"
            elif imbalance < -self.imbalance_threshold:
                # Need bearish Nansen signal
                nansen_aligned = nansen_consensus["action"] == "SELL"
            else:
                nansen_aligned = False

        # Generate signal based on imbalance
        signal = None

        # Bullish imbalance
        if imbalance > self.imbalance_threshold and nansen_aligned:
            stop_loss = current_price * (1 - self.stop_loss_bps / 10000)
            take_profit = current_price * (1 + self.take_profit_bps / 10000)

            # Confidence based on imbalance strength and Nansen
            base_confidence = min(abs(imbalance), 1.0)
            nansen_boost = nansen_consensus.get("confidence", 0) * 0.2
            confidence = min(base_confidence + nansen_boost, 1.0)

            signal = TradingSignal(
                strategy_name=self.name,
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=4,
                metadata={
                    "imbalance": imbalance,
                    "nansen_action": nansen_consensus["action"],
                    "nansen_confidence": nansen_consensus["confidence"],
                    "holding_period_target": self.holding_period_seconds,
                    "entry_logic": "orderbook_imbalance_bullish"
                }
            )

            self.logger.info(
                f"BUY signal: {symbol} @ {current_price:.4f} (imbalance: {imbalance:.2f})",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                imbalance=imbalance,
                confidence=confidence
            )

        # Bearish imbalance
        elif imbalance < -self.imbalance_threshold and nansen_aligned:
            stop_loss = current_price * (1 + self.stop_loss_bps / 10000)
            take_profit = current_price * (1 - self.take_profit_bps / 10000)

            base_confidence = min(abs(imbalance), 1.0)
            nansen_boost = nansen_consensus.get("confidence", 0) * 0.2
            confidence = min(base_confidence + nansen_boost, 1.0)

            signal = TradingSignal(
                strategy_name=self.name,
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=4,
                metadata={
                    "imbalance": imbalance,
                    "nansen_action": nansen_consensus["action"],
                    "nansen_confidence": nansen_consensus["confidence"],
                    "holding_period_target": self.holding_period_seconds,
                    "entry_logic": "orderbook_imbalance_bearish"
                }
            )

            self.logger.info(
                f"SELL signal: {symbol} @ {current_price:.4f} (imbalance: {imbalance:.2f})",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                imbalance=imbalance,
                confidence=confidence
            )

        return signal
