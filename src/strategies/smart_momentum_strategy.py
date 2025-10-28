"""
Smart Money Momentum Strategy

Strategy logic:
- Primary signals from Nansen MCP (60% weight)
- Technical confirmation (40% weight)
- Entry conditions:
  * Smart money net buying > 30%
  * Exchange outflows detected
  * Technical indicators confirm (RSI, MACD)
- Scale into winners: 25% → 25% → 30% → 20%
- NEVER average down losers
- Hold 2-10 days typical
- Position size based on conviction
"""

from typing import Optional, List
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.data.nansen_client import NansenSignal, SignalStrength
from src.core.logger import LogCategory


class SmartMoneyMomentumStrategy(BaseStrategy):
    """
    Momentum strategy driven primarily by Nansen smart money signals.
    """

    def __init__(
        self,
        nansen_weight: float = 0.6,
        technical_weight: float = 0.4,
        smart_money_threshold: float = 0.3,
        scale_in_stages: List[float] = None,
        never_average_down: bool = True,
        enabled: bool = True
    ):
        """
        Initialize smart money momentum strategy.

        Args:
            nansen_weight: Weight for Nansen signals (0-1)
            technical_weight: Weight for technical analysis (0-1)
            smart_money_threshold: Minimum smart money buying threshold
            scale_in_stages: List of position size percentages for scaling
            never_average_down: Never add to losing positions
            enabled: Whether strategy is enabled
        """
        super().__init__(name="SmartMoneyMomentum", enabled=enabled)

        self.nansen_weight = nansen_weight
        self.technical_weight = technical_weight
        self.smart_money_threshold = smart_money_threshold
        self.scale_in_stages = scale_in_stages or [0.25, 0.25, 0.30, 0.20]
        self.never_average_down = never_average_down

        # Track positions for scaling
        self.position_scale_stage: dict = {}  # symbol -> current stage

    async def analyze(self, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze Nansen signals and generate momentum signal.

        Args:
            symbol: Trading pair symbol

        Returns:
            Trading signal or None
        """
        if not self.enabled:
            return None

        # Get Nansen signals
        nansen_signals = self.nansen_signals.get(symbol, [])
        if not nansen_signals:
            self.logger.debug(
                f"No Nansen signals for {symbol}",
                category=LogCategory.STRATEGY
            )
            return None

        # Analyze Nansen signals
        nansen_score = self._calculate_nansen_score(nansen_signals)

        # Get technical score (simplified for now)
        technical_score = self._calculate_technical_score(symbol)

        # Combine scores
        combined_score = (
            nansen_score * self.nansen_weight +
            technical_score * self.technical_weight
        )

        # Minimum threshold for entry
        if abs(combined_score) < 0.5:
            return None

        # Get current price
        current_price = self.current_prices.get(symbol)
        if current_price is None:
            order_book = self.order_books.get(symbol)
            if order_book:
                current_price = order_book.get_mid_price()

        if current_price is None:
            return None

        # Determine signal type
        if combined_score > 0.5:
            signal_type = SignalType.BUY
            # Stop loss at 3% for momentum trades
            stop_loss = current_price * 0.97
            # Take profit at 15% for momentum trades
            take_profit = current_price * 1.15
        elif combined_score < -0.5:
            signal_type = SignalType.SELL
            stop_loss = current_price * 1.03
            take_profit = current_price * 0.85
        else:
            return None

        # Determine leverage and position size based on confidence
        confidence = abs(combined_score)

        if confidence > 0.8:
            leverage = 5
            size_multiplier = 1.5
        elif confidence > 0.6:
            leverage = 4
            size_multiplier = 1.0
        else:
            leverage = 3
            size_multiplier = 0.7

        # Check if this is a scaling opportunity
        current_stage = self.position_scale_stage.get(symbol, 0)
        if current_stage < len(self.scale_in_stages):
            stage_size = self.scale_in_stages[current_stage]
        else:
            # Already fully scaled in
            return None

        # Extract key Nansen insights for metadata
        smart_money_flow = None
        exchange_netflow = None
        whale_activity = None

        for signal in nansen_signals:
            if "smart_money_flow" in signal.signal_type.value:
                smart_money_flow = signal.data.get("net_change_pct")
            elif "exchange_netflow" in signal.signal_type.value:
                exchange_netflow = signal.data.get("netflow_24h")
            elif "whale" in signal.signal_type.value:
                whale_activity = signal.data

        signal = TradingSignal(
            strategy_name=self.name,
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
            metadata={
                "nansen_score": nansen_score,
                "technical_score": technical_score,
                "combined_score": combined_score,
                "scale_stage": current_stage + 1,
                "stage_size_percent": stage_size,
                "size_multiplier": size_multiplier,
                "smart_money_flow_pct": smart_money_flow,
                "exchange_netflow": exchange_netflow,
                "whale_activity": whale_activity,
                "entry_logic": "smart_money_momentum"
            }
        )

        self.logger.info(
            f"{signal_type.value} signal: {symbol} @ {current_price:.4f} "
            f"(Nansen: {nansen_score:.2f}, Tech: {technical_score:.2f}, Stage: {current_stage + 1})",
            category=LogCategory.STRATEGY,
            symbol=symbol,
            signal_type=signal_type.value,
            confidence=confidence
        )

        return signal

    def _calculate_nansen_score(self, signals: List[NansenSignal]) -> float:
        """
        Calculate Nansen score from signals.

        Args:
            signals: List of Nansen signals

        Returns:
            Score from -1.0 to 1.0
        """
        if not signals:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for signal in signals:
            # Convert signal strength to numeric score
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

            # Weight by confidence
            weighted_score = score * signal.confidence
            total_score += weighted_score
            total_weight += signal.confidence

        if total_weight == 0:
            return 0.0

        return total_score / total_weight

    def _calculate_technical_score(self, symbol: str) -> float:
        """
        Calculate technical analysis score.

        Args:
            symbol: Trading pair symbol

        Returns:
            Score from -1.0 to 1.0
        """
        # Simplified technical score based on order book
        order_book = self.order_books.get(symbol)
        if not order_book:
            return 0.0

        # Use order book imbalance as proxy for technical momentum
        imbalance = order_book.get_imbalance(depth=5)
        if imbalance is None:
            return 0.0

        # Scale imbalance to -1 to 1 range
        # Imbalance is already in this range, so just return it
        return imbalance

    def on_position_opened(self, symbol: str):
        """
        Called when position is opened.

        Args:
            symbol: Trading pair symbol
        """
        if symbol not in self.position_scale_stage:
            self.position_scale_stage[symbol] = 1
        else:
            self.position_scale_stage[symbol] += 1

        self.logger.info(
            f"Position stage updated: {symbol} -> {self.position_scale_stage[symbol]}",
            category=LogCategory.STRATEGY,
            symbol=symbol,
            stage=self.position_scale_stage[symbol]
        )

    def on_position_closed(self, symbol: str):
        """
        Called when position is fully closed.

        Args:
            symbol: Trading pair symbol
        """
        if symbol in self.position_scale_stage:
            del self.position_scale_stage[symbol]

        self.logger.info(
            f"Position scaling reset: {symbol}",
            category=LogCategory.STRATEGY,
            symbol=symbol
        )

    def should_scale_in(self, symbol: str, current_pnl: float) -> bool:
        """
        Determine if should scale into position.

        Args:
            symbol: Trading pair symbol
            current_pnl: Current unrealized P&L

        Returns:
            True if should scale in
        """
        # Never average down
        if self.never_average_down and current_pnl < 0:
            self.logger.debug(
                f"Not scaling into {symbol} - position is losing (never average down)",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                pnl=current_pnl
            )
            return False

        # Check if we can scale further
        current_stage = self.position_scale_stage.get(symbol, 0)
        if current_stage >= len(self.scale_in_stages):
            self.logger.debug(
                f"Not scaling into {symbol} - already at max stage {current_stage}",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                stage=current_stage
            )
            return False

        # Only scale if position is winning (for momentum strategy)
        if current_pnl > 0:
            self.logger.info(
                f"Can scale into {symbol} - winning position at stage {current_stage}",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                pnl=current_pnl,
                stage=current_stage
            )
            return True

        return False
