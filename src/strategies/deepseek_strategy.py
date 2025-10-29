"""
DeepSeek Alpha Arena Strategy

Based on DeepSeek's 130% return in 10 days on Hyperliquid:
- Only 17 trades (highly selective)
- 49 hour average hold time (patient)
- 41% win rate but 6.7:1 profit-to-loss ratio (excellent R:R)
- Diversification across multiple assets
- Rigid discipline with stops and targets
"""

from typing import Optional
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.ai.deepseek_client import DeepSeekClient, DeepSeekAnalysis
from src.core.logger import LogCategory


class DeepSeekAlphaArenaStrategy(BaseStrategy):
    """
    Strategy implementing DeepSeek's Alpha Arena winning approach.

    Key principles:
    1. Selective Entries - Only high-conviction setups (confidence > 0.7)
    2. High Risk/Reward - Minimum 6:1 profit-to-loss ratio
    3. Patient Holding - Average 48-50 hour hold times
    4. Rigid Discipline - Never violate stop-loss or take-profit rules
    5. Diversification - Spread risk across quality setups
    """

    def __init__(
        self,
        deepseek_client: DeepSeekClient,
        min_confidence: float = 0.7,
        min_risk_reward: float = 6.0,
        target_hold_hours: int = 48,
        max_trades_per_day: int = 2,  # Selective like DeepSeek (17 trades in 10 days)
        enabled: bool = True
    ):
        """
        Initialize DeepSeek Alpha Arena strategy.

        Args:
            deepseek_client: DeepSeek API client
            min_confidence: Minimum confidence threshold (0.7 = 70%)
            min_risk_reward: Minimum risk/reward ratio (6.0 = 6:1)
            target_hold_hours: Target holding period
            max_trades_per_day: Maximum trades per day (maintains selectivity)
            enabled: Whether strategy is enabled
        """
        super().__init__(name="DeepSeekAlphaArena", enabled=enabled)

        self.deepseek_client = deepseek_client
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.target_hold_hours = target_hold_hours
        self.max_trades_per_day = max_trades_per_day

        # Track trades per day for selectivity
        self.trades_today = 0
        self.last_trade_date = None

    async def analyze(self, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze symbol using DeepSeek AI.

        Args:
            symbol: Trading pair symbol

        Returns:
            Trading signal or None
        """
        if not self.enabled:
            return None

        # Check trade limit (maintain selectivity)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()

        if self.last_trade_date != today:
            self.trades_today = 0
            self.last_trade_date = today

        if self.trades_today >= self.max_trades_per_day:
            self.logger.debug(
                f"Daily trade limit reached ({self.max_trades_per_day}), maintaining selectivity",
                category=LogCategory.STRATEGY,
                symbol=symbol
            )
            return None

        # Gather market data
        order_book = self.order_books.get(symbol)
        if not order_book:
            return None

        current_price = order_book.get_mid_price()
        if not current_price:
            return None

        # Prepare order book data
        order_book_data = {
            'imbalance': order_book.get_imbalance(depth=5),
            'bid_liquidity': order_book.get_liquidity(depth=5)['bid_liquidity'],
            'ask_liquidity': order_book.get_liquidity(depth=5)['ask_liquidity'],
            'spread_bps': order_book.get_spread_bps()
        }

        # Get Nansen consensus
        nansen_data = None
        if self.nansen_signals.get(symbol):
            nansen_data = self._format_nansen_data(symbol)

        # Get DeepSeek analysis
        try:
            analysis = await self.deepseek_client.analyze_market(
                symbol=symbol,
                current_price=current_price,
                order_book_data=order_book_data,
                nansen_data=nansen_data,
                market_context=self._build_market_context(symbol)
            )

            # Convert DeepSeek analysis to trading signal
            if analysis.action != "HOLD":
                signal = self._create_signal_from_analysis(analysis)

                if signal:
                    self.trades_today += 1

                    self.logger.info(
                        f"DeepSeek signal: {signal.signal_type.value} {symbol} "
                        f"(R:R: {analysis.risk_reward_ratio:.1f}:1, Hold: {analysis.hold_duration_hours}h)",
                        category=LogCategory.STRATEGY,
                        symbol=symbol,
                        confidence=analysis.confidence,
                        risk_reward=analysis.risk_reward_ratio
                    )

                return signal

        except Exception as e:
            self.logger.error(
                f"Error in DeepSeek analysis: {e}",
                category=LogCategory.STRATEGY,
                symbol=symbol,
                error=str(e)
            )

        return None

    def _format_nansen_data(self, symbol: str) -> dict:
        """Format Nansen signals for DeepSeek analysis."""
        signals = self.nansen_signals.get(symbol, [])

        if not signals:
            return None

        # Calculate aggregate metrics
        buy_count = sum(1 for s in signals if 'buy' in s.signal_strength.value.lower())
        sell_count = sum(1 for s in signals if 'sell' in s.signal_strength.value.lower())

        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        # Determine action
        if buy_count > sell_count:
            action = "BUY"
            score = (buy_count - sell_count) / len(signals)
        elif sell_count > buy_count:
            action = "SELL"
            score = (sell_count - buy_count) / len(signals)
        else:
            action = "NEUTRAL"
            score = 0.0

        return {
            'action': action,
            'confidence': avg_confidence,
            'score': score,
            'signals': [
                {
                    'type': s.signal_type.value,
                    'strength': s.signal_strength.value,
                    'confidence': s.confidence,
                    'reasoning': s.reasoning
                }
                for s in signals
            ]
        }

    def _build_market_context(self, symbol: str) -> str:
        """Build additional market context for DeepSeek."""
        context_parts = []

        # Add recent performance
        if self.performance.total_trades > 0:
            context_parts.append(
                f"Strategy performance: {self.performance.win_rate*100:.1f}% win rate, "
                f"{self.performance.total_trades} total trades, "
                f"${self.performance.total_pnl:.2f} total P&L"
            )

        # Add symbol-specific context
        context_parts.append(f"Symbol: {symbol} (Hyperliquid perpetual)")

        return " | ".join(context_parts)

    def _create_signal_from_analysis(self, analysis: DeepSeekAnalysis) -> Optional[TradingSignal]:
        """Convert DeepSeek analysis to trading signal."""

        # Validate analysis meets criteria
        if analysis.confidence < self.min_confidence:
            self.logger.debug(
                f"DeepSeek analysis below confidence threshold: {analysis.confidence:.2f} < {self.min_confidence}",
                category=LogCategory.STRATEGY
            )
            return None

        if analysis.risk_reward_ratio and analysis.risk_reward_ratio < self.min_risk_reward:
            self.logger.debug(
                f"DeepSeek analysis below R:R threshold: {analysis.risk_reward_ratio:.1f} < {self.min_risk_reward}",
                category=LogCategory.STRATEGY
            )
            return None

        # Map action to signal type
        if analysis.action == "BUY":
            signal_type = SignalType.BUY
        elif analysis.action == "SELL":
            signal_type = SignalType.SELL
        else:
            return None

        # Create signal
        signal = TradingSignal(
            strategy_name=self.name,
            symbol=analysis.symbol,
            signal_type=signal_type,
            confidence=analysis.confidence,
            entry_price=analysis.entry_price,
            stop_loss=analysis.stop_loss,
            take_profit=analysis.take_profit,
            leverage=5,  # Conservative leverage for longer holds
            metadata={
                'deepseek_reasoning': analysis.reasoning,
                'risk_reward_ratio': analysis.risk_reward_ratio,
                'hold_duration_target_hours': analysis.hold_duration_hours or self.target_hold_hours,
                'entry_logic': 'deepseek_alpha_arena',
                'model': self.deepseek_client.model
            }
        )

        return signal

    def get_position_management_rules(self, symbol: str) -> dict:
        """
        Get position management rules for DeepSeek strategy.

        Returns:
            Dict with position management parameters
        """
        return {
            'strategy': 'deepseek_alpha_arena',
            'min_hold_hours': 24,  # Don't exit too early
            'target_hold_hours': self.target_hold_hours,
            'max_hold_hours': 120,  # 5 days max
            'trailing_stop': False,  # Use fixed stops like DeepSeek
            'scale_out': False,  # All-in/all-out approach
            'never_move_stop_against_position': True,  # Rigid discipline
            'always_respect_take_profit': True  # Lock in wins at target
        }

    async def post_trade_learning(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        hold_hours: float
    ):
        """
        Use DeepSeek to analyze completed trade and learn.

        Args:
            symbol: Trading pair
            entry_price: Entry price
            exit_price: Exit price
            pnl: Realized P&L
            hold_hours: Actual holding period
        """
        # Build trade summary
        trade_data = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': ((exit_price - entry_price) / entry_price) * 100,
            'hold_hours': hold_hours,
            'outcome': 'WIN' if pnl > 0 else 'LOSS'
        }

        # Ask DeepSeek to analyze
        messages = [
            {
                "role": "system",
                "content": "You are analyzing a completed trade to extract learning insights."
            },
            {
                "role": "user",
                "content": f"""Analyze this trade and provide 3 key insights:

Trade: {trade_data}

Expected hold time: {self.target_hold_hours} hours
Actual hold time: {hold_hours:.1f} hours

What can we learn to improve future trades?"""
            }
        ]

        try:
            insights = await self.deepseek_client._make_request(
                messages,
                temperature=0.5,
                max_tokens=500
            )

            self.logger.info(
                f"DeepSeek trade analysis: {insights}",
                category=LogCategory.AI,
                trade_pnl=pnl
            )

        except Exception as e:
            self.logger.error(
                f"Error in post-trade analysis: {e}",
                category=LogCategory.AI,
                error=str(e)
            )
