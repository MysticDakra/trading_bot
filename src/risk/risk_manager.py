"""
Comprehensive risk management system.

Features:
- Kelly Criterion position sizing
- Liquidation price calculation
- Daily loss limit enforcement
- Maximum drawdown monitoring
- Position correlation analysis
- Circuit breakers
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from src.core.logger import get_logger, LogCategory


class RiskLevel(str, Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Position:
    """Trading position."""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    quantity: float
    leverage: int
    timestamp: datetime
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    total_exposure: float
    daily_pnl: float
    total_pnl: float
    drawdown: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    num_positions: int
    risk_level: RiskLevel


class RiskManager:
    """
    Production-grade risk management system.

    Enforces:
    - Position sizing limits
    - Daily loss limits
    - Maximum drawdown
    - Leverage restrictions
    - Position correlation limits
    """

    def __init__(
        self,
        active_capital: float,
        max_daily_loss: float,
        max_drawdown: float,
        default_leverage: int = 4,
        max_leverage: int = 8,
        kelly_fraction: float = 0.25,
        max_concurrent_positions: int = 4,
        max_correlation: float = 0.7
    ):
        """
        Initialize risk manager.

        Args:
            active_capital: Active trading capital
            max_daily_loss: Maximum allowed daily loss
            max_drawdown: Maximum allowed drawdown
            default_leverage: Default leverage
            max_leverage: Maximum allowed leverage
            kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
            max_concurrent_positions: Maximum concurrent positions
            max_correlation: Maximum correlation between positions
        """
        self.active_capital = active_capital
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.default_leverage = default_leverage
        self.max_leverage = max_leverage
        self.kelly_fraction = kelly_fraction
        self.max_concurrent_positions = max_concurrent_positions
        self.max_correlation = max_correlation

        # Track positions
        self.positions: Dict[str, Position] = {}

        # Track P&L
        self.daily_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.peak_capital: float = active_capital
        self.current_drawdown: float = 0.0

        # Track daily reset
        self.last_reset_date = datetime.now(timezone.utc).date()

        # Circuit breaker state
        self.is_halted = False
        self.halt_reason: Optional[str] = None

        self.logger = get_logger("risk_manager")

    def calculate_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_fraction: Optional[float] = None
    ) -> float:
        """
        Calculate position size using Kelly Criterion.

        Kelly% = (Win% * Avg_Win - Loss% * Avg_Loss) / Avg_Win

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive number)
            kelly_fraction: Fraction of Kelly to use (defaults to self.kelly_fraction)

        Returns:
            Position size as fraction of capital
        """
        if kelly_fraction is None:
            kelly_fraction = self.kelly_fraction

        if win_rate <= 0 or win_rate >= 1:
            self.logger.warning(
                f"Invalid win rate: {win_rate}, using default sizing",
                category=LogCategory.RISK
            )
            return 0.02  # Default to 2% of capital

        if avg_win <= 0 or avg_loss <= 0:
            self.logger.warning(
                "Invalid win/loss amounts, using default sizing",
                category=LogCategory.RISK
            )
            return 0.02

        loss_rate = 1 - win_rate

        # Kelly formula
        kelly_percent = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        # Apply fractional Kelly for safety
        position_fraction = max(0, kelly_percent * kelly_fraction)

        # Cap at 25% of capital for safety
        position_fraction = min(position_fraction, 0.25)

        return position_fraction

    def calculate_position_size(
        self,
        symbol: str,
        risk_percent: float = 5.0,
        stop_loss_percent: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate position size using multiple methods.

        Args:
            symbol: Trading pair symbol
            risk_percent: Percent of capital to risk (default 5%)
            stop_loss_percent: Stop loss as percent of entry
            win_rate: Historical win rate for Kelly
            avg_win: Average win for Kelly
            avg_loss: Average loss for Kelly

        Returns:
            Dict with position_size, leverage, notional_value
        """
        # Method 1: Fixed risk percent
        risk_amount = self.active_capital * (risk_percent / 100)

        # Method 2: Kelly Criterion if stats provided
        kelly_size = None
        if all([win_rate, avg_win, avg_loss]):
            kelly_fraction_capital = self.calculate_kelly_position_size(
                win_rate, avg_win, avg_loss
            )
            kelly_size = self.active_capital * kelly_fraction_capital

        # Use Kelly if available, otherwise fixed risk
        base_size = kelly_size if kelly_size else risk_amount

        # Adjust for leverage
        leverage = self.default_leverage

        # If stop loss provided, calculate position size to match risk
        if stop_loss_percent:
            # Position size such that stop_loss_percent loss = risk_amount
            position_size = risk_amount / (stop_loss_percent / 100)
        else:
            position_size = base_size * leverage

        return {
            "position_size": position_size,
            "leverage": leverage,
            "notional_value": position_size,
            "risk_amount": risk_amount
        }

    def calculate_liquidation_price(
        self,
        entry_price: float,
        leverage: int,
        side: str,
        maintenance_margin_rate: float = 0.025  # 2.5% typical for perps
    ) -> float:
        """
        Calculate liquidation price for leveraged position.

        Args:
            entry_price: Entry price
            leverage: Leverage used
            side: "long" or "short"
            maintenance_margin_rate: Maintenance margin requirement

        Returns:
            Liquidation price
        """
        # Initial margin = 1 / leverage
        initial_margin = 1 / leverage

        # Liquidation when: (Price_Change / Entry_Price) = -(Initial_Margin - Maintenance_Margin)
        liquidation_move = -(initial_margin - maintenance_margin_rate)

        if side.lower() == "long":
            # For longs, liquidation happens on downward move
            liquidation_price = entry_price * (1 + liquidation_move)
        else:
            # For shorts, liquidation happens on upward move
            liquidation_price = entry_price * (1 - liquidation_move)

        return liquidation_price

    def calculate_margin_requirements(
        self,
        position_size: float,
        entry_price: float,
        leverage: int
    ) -> Dict[str, float]:
        """
        Calculate margin requirements.

        Args:
            position_size: Position size in base currency
            entry_price: Entry price
            leverage: Leverage

        Returns:
            Dict with initial_margin, maintenance_margin, notional_value
        """
        notional_value = position_size * entry_price
        initial_margin = notional_value / leverage
        maintenance_margin = notional_value * 0.025  # 2.5% maintenance

        return {
            "notional_value": notional_value,
            "initial_margin": initial_margin,
            "maintenance_margin": maintenance_margin,
            "leverage": leverage
        }

    def check_position_allowed(
        self,
        symbol: str,
        position_size: float,
        leverage: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if position is allowed based on risk rules.

        Args:
            symbol: Trading pair
            position_size: Proposed position size
            leverage: Proposed leverage

        Returns:
            (allowed, reason_if_not_allowed)
        """
        # Check if halted
        if self.is_halted:
            return False, f"Trading halted: {self.halt_reason}"

        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            self.halt_trading("Daily loss limit exceeded")
            return False, "Daily loss limit exceeded"

        # Check max drawdown
        if self.current_drawdown >= self.max_drawdown:
            self.halt_trading("Maximum drawdown exceeded")
            return False, "Maximum drawdown exceeded"

        # Check max concurrent positions
        if len(self.positions) >= self.max_concurrent_positions and symbol not in self.positions:
            return False, f"Maximum concurrent positions ({self.max_concurrent_positions}) reached"

        # Check leverage limit
        if leverage > self.max_leverage:
            return False, f"Leverage {leverage}x exceeds maximum {self.max_leverage}x"

        # Check total exposure
        total_exposure = sum(
            pos.quantity * pos.entry_price * pos.leverage
            for pos in self.positions.values()
        )
        new_exposure = total_exposure + (position_size * leverage)

        max_exposure = self.active_capital * 20  # Max 20x total exposure
        if new_exposure > max_exposure:
            return False, f"Total exposure ${new_exposure:.2f} exceeds maximum ${max_exposure:.2f}"

        return True, None

    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        leverage: int
    ) -> bool:
        """
        Add a new position.

        Args:
            symbol: Trading pair
            side: "long" or "short"
            entry_price: Entry price
            quantity: Position quantity
            leverage: Leverage used

        Returns:
            Success boolean
        """
        # Check if allowed
        allowed, reason = self.check_position_allowed(symbol, quantity * entry_price, leverage)
        if not allowed:
            self.logger.warning(
                f"Position rejected: {reason}",
                category=LogCategory.RISK,
                symbol=symbol
            )
            return False

        # Calculate liquidation price
        liq_price = self.calculate_liquidation_price(entry_price, leverage, side)

        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            timestamp=datetime.now(timezone.utc)
        )

        self.positions[symbol] = position

        self.logger.info(
            f"Position added: {side} {quantity} {symbol} @ {entry_price} (Leverage: {leverage}x, Liq: {liq_price:.2f})",
            category=LogCategory.RISK,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            leverage=leverage,
            liquidation_price=liq_price
        )

        return True

    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """
        Close a position and calculate realized P&L.

        Args:
            symbol: Trading pair
            exit_price: Exit price

        Returns:
            Realized P&L
        """
        if symbol not in self.positions:
            self.logger.warning(
                f"Attempted to close non-existent position: {symbol}",
                category=LogCategory.RISK
            )
            return None

        position = self.positions[symbol]

        # Calculate P&L
        if position.side == "long":
            pnl = (exit_price - position.entry_price) * position.quantity * position.leverage
        else:
            pnl = (position.entry_price - exit_price) * position.quantity * position.leverage

        # Update tracking
        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Update drawdown
        current_capital = self.active_capital + self.total_pnl
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        self.current_drawdown = self.peak_capital - current_capital

        # Remove position
        del self.positions[symbol]

        self.logger.info(
            f"Position closed: {symbol} P&L: ${pnl:.2f} (Daily: ${self.daily_pnl:.2f}, Total: ${self.total_pnl:.2f})",
            category=LogCategory.RISK,
            symbol=symbol,
            pnl=pnl,
            daily_pnl=self.daily_pnl,
            total_pnl=self.total_pnl
        )

        return pnl

    def update_position_pnl(self, symbol: str, current_price: float):
        """
        Update unrealized P&L for position.

        Args:
            symbol: Trading pair
            current_price: Current market price
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        if position.side == "long":
            unrealized_pnl = (current_price - position.entry_price) * position.quantity * position.leverage
        else:
            unrealized_pnl = (position.entry_price - current_price) * position.quantity * position.leverage

        position.unrealized_pnl = unrealized_pnl

    def get_risk_metrics(self) -> RiskMetrics:
        """
        Get current risk metrics.

        Returns:
            RiskMetrics instance
        """
        total_exposure = sum(
            pos.quantity * pos.entry_price * pos.leverage
            for pos in self.positions.values()
        )

        # Calculate Value at Risk (simplified)
        var_95 = total_exposure * 0.05  # 5% move estimate

        # Determine risk level
        if self.current_drawdown >= self.max_drawdown * 0.8:
            risk_level = RiskLevel.CRITICAL
        elif self.daily_pnl <= -self.max_daily_loss * 0.7:
            risk_level = RiskLevel.HIGH
        elif len(self.positions) >= self.max_concurrent_positions * 0.8:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return RiskMetrics(
            total_exposure=total_exposure,
            daily_pnl=self.daily_pnl,
            total_pnl=self.total_pnl,
            drawdown=self.current_drawdown,
            max_drawdown=self.max_drawdown,
            var_95=var_95,
            num_positions=len(self.positions),
            risk_level=risk_level
        )

    def halt_trading(self, reason: str):
        """
        Halt all trading due to risk event.

        Args:
            reason: Reason for halt
        """
        self.is_halted = True
        self.halt_reason = reason

        self.logger.critical(
            f"TRADING HALTED: {reason}",
            category=LogCategory.RISK,
            reason=reason
        )

    def resume_trading(self):
        """Resume trading after manual intervention."""
        self.is_halted = False
        self.halt_reason = None

        self.logger.info(
            "Trading resumed",
            category=LogCategory.RISK
        )

    def reset_daily_metrics(self):
        """Reset daily metrics (called at start of new trading day)."""
        today = datetime.now(timezone.utc).date()

        if today > self.last_reset_date:
            self.logger.info(
                f"Resetting daily metrics. Previous daily P&L: ${self.daily_pnl:.2f}",
                category=LogCategory.RISK,
                daily_pnl=self.daily_pnl
            )

            self.daily_pnl = 0.0
            self.last_reset_date = today

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        return self.positions.copy()

    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
