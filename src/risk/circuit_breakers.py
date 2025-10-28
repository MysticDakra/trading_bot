"""
Circuit breakers and kill switches for emergency risk management.

Breakers:
- Daily loss limit: Auto-stop at $750 (5% of $15k)
- Drawdown limit: Pause at $3,000 (20%)
- API error threshold: Pause after 10 consecutive errors
- Volatility spike: Halt on 50% move in 5 minutes
- Kill switch: Emergency close all positions
"""

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from src.core.logger import get_logger, LogCategory


class BreakerType(str, Enum):
    """Circuit breaker types."""
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    API_ERROR = "api_error"
    VOLATILITY = "volatility"
    MANUAL = "manual"
    CONSECUTIVE_LOSSES = "consecutive_losses"


class BreakerAction(str, Enum):
    """Actions to take when breaker trips."""
    PAUSE_TRADING = "pause_trading"
    CLOSE_ALL_POSITIONS = "close_all_positions"
    REDUCE_LEVERAGE = "reduce_leverage"
    ALERT_ONLY = "alert_only"


@dataclass
class BreakerEvent:
    """Circuit breaker trip event."""
    breaker_type: BreakerType
    timestamp: datetime
    reason: str
    action_taken: BreakerAction
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CircuitBreaker:
    """Base circuit breaker class."""

    def __init__(
        self,
        name: str,
        breaker_type: BreakerType,
        action: BreakerAction,
        enabled: bool = True
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Breaker name
            breaker_type: Type of breaker
            action: Action to take when tripped
            enabled: Whether breaker is enabled
        """
        self.name = name
        self.breaker_type = breaker_type
        self.action = action
        self.enabled = enabled

        self.is_tripped = False
        self.trip_count = 0
        self.last_trip_time: Optional[datetime] = None
        self.logger = get_logger(f"circuit_breaker.{name}")

    def check(self, *args, **kwargs) -> bool:
        """
        Check if breaker should trip.

        Returns:
            True if breaker trips
        """
        raise NotImplementedError

    def trip(self, reason: str, metadata: Optional[Dict] = None) -> BreakerEvent:
        """
        Trip the circuit breaker.

        Args:
            reason: Reason for trip
            metadata: Additional metadata

        Returns:
            Breaker event
        """
        self.is_tripped = True
        self.trip_count += 1
        self.last_trip_time = datetime.now(timezone.utc)

        event = BreakerEvent(
            breaker_type=self.breaker_type,
            timestamp=self.last_trip_time,
            reason=reason,
            action_taken=self.action,
            metadata=metadata or {}
        )

        self.logger.critical(
            f"CIRCUIT BREAKER TRIPPED: {self.name} - {reason}",
            category=LogCategory.RISK,
            breaker=self.name,
            reason=reason,
            action=self.action.value
        )

        return event

    def reset(self):
        """Reset the breaker."""
        self.is_tripped = False

        self.logger.info(
            f"Circuit breaker reset: {self.name}",
            category=LogCategory.RISK,
            breaker=self.name
        )


class DailyLossBreaker(CircuitBreaker):
    """Circuit breaker for daily loss limit."""

    def __init__(
        self,
        max_daily_loss: float,
        action: BreakerAction = BreakerAction.PAUSE_TRADING,
        enabled: bool = True
    ):
        super().__init__(
            name="DailyLoss",
            breaker_type=BreakerType.DAILY_LOSS,
            action=action,
            enabled=enabled
        )
        self.max_daily_loss = max_daily_loss

    def check(self, daily_pnl: float) -> bool:
        """
        Check daily loss.

        Args:
            daily_pnl: Current daily P&L

        Returns:
            True if breaker trips
        """
        if not self.enabled or self.is_tripped:
            return False

        if daily_pnl <= -self.max_daily_loss:
            self.trip(
                f"Daily loss ${abs(daily_pnl):.2f} exceeds limit ${self.max_daily_loss:.2f}",
                metadata={"daily_pnl": daily_pnl, "limit": self.max_daily_loss}
            )
            return True

        return False


class DrawdownBreaker(CircuitBreaker):
    """Circuit breaker for maximum drawdown."""

    def __init__(
        self,
        max_drawdown: float,
        action: BreakerAction = BreakerAction.PAUSE_TRADING,
        enabled: bool = True
    ):
        super().__init__(
            name="Drawdown",
            breaker_type=BreakerType.DRAWDOWN,
            action=action,
            enabled=enabled
        )
        self.max_drawdown = max_drawdown

    def check(self, current_drawdown: float) -> bool:
        """
        Check drawdown.

        Args:
            current_drawdown: Current drawdown amount

        Returns:
            True if breaker trips
        """
        if not self.enabled or self.is_tripped:
            return False

        if current_drawdown >= self.max_drawdown:
            self.trip(
                f"Drawdown ${current_drawdown:.2f} exceeds maximum ${self.max_drawdown:.2f}",
                metadata={"drawdown": current_drawdown, "max": self.max_drawdown}
            )
            return True

        return False


class APIErrorBreaker(CircuitBreaker):
    """Circuit breaker for consecutive API errors."""

    def __init__(
        self,
        max_consecutive_errors: int = 10,
        action: BreakerAction = BreakerAction.PAUSE_TRADING,
        enabled: bool = True
    ):
        super().__init__(
            name="APIError",
            breaker_type=BreakerType.API_ERROR,
            action=action,
            enabled=enabled
        )
        self.max_consecutive_errors = max_consecutive_errors
        self.consecutive_errors = 0

    def record_error(self):
        """Record an API error."""
        self.consecutive_errors += 1

        if self.consecutive_errors >= self.max_consecutive_errors:
            self.trip(
                f"{self.consecutive_errors} consecutive API errors",
                metadata={"error_count": self.consecutive_errors}
            )

    def record_success(self):
        """Record a successful API call."""
        self.consecutive_errors = 0

    def check(self) -> bool:
        """Check if error threshold exceeded."""
        return self.is_tripped


class VolatilityBreaker(CircuitBreaker):
    """Circuit breaker for extreme volatility."""

    def __init__(
        self,
        max_move_percent: float = 50,
        time_window_minutes: int = 5,
        action: BreakerAction = BreakerAction.ALERT_ONLY,
        enabled: bool = True
    ):
        super().__init__(
            name="Volatility",
            breaker_type=BreakerType.VOLATILITY,
            action=action,
            enabled=enabled
        )
        self.max_move_percent = max_move_percent
        self.time_window_minutes = time_window_minutes

        # Price history
        self.price_history: Dict[str, List[tuple]] = {}  # symbol -> [(timestamp, price)]

    def update_price(self, symbol: str, price: float):
        """
        Update price and check for volatility spike.

        Args:
            symbol: Trading pair symbol
            price: Current price
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        timestamp = datetime.now(timezone.utc)
        self.price_history[symbol].append((timestamp, price))

        # Clean old data
        cutoff = timestamp - timedelta(minutes=self.time_window_minutes)
        self.price_history[symbol] = [
            (ts, p) for ts, p in self.price_history[symbol]
            if ts >= cutoff
        ]

        # Check volatility
        self.check(symbol)

    def check(self, symbol: str) -> bool:
        """
        Check for volatility spike.

        Args:
            symbol: Trading pair symbol

        Returns:
            True if breaker trips
        """
        if not self.enabled or self.is_tripped:
            return False

        prices = self.price_history.get(symbol, [])
        if len(prices) < 2:
            return False

        # Get price range
        price_values = [p for _, p in prices]
        min_price = min(price_values)
        max_price = max(price_values)

        # Calculate move percentage
        move_percent = ((max_price - min_price) / min_price) * 100

        if move_percent >= self.max_move_percent:
            self.trip(
                f"{symbol} moved {move_percent:.1f}% in {self.time_window_minutes} minutes",
                metadata={
                    "symbol": symbol,
                    "move_percent": move_percent,
                    "min_price": min_price,
                    "max_price": max_price
                }
            )
            return True

        return False


class ConsecutiveLossesBreaker(CircuitBreaker):
    """Circuit breaker for consecutive losing trades."""

    def __init__(
        self,
        max_consecutive_losses: int = 5,
        action: BreakerAction = BreakerAction.PAUSE_TRADING,
        enabled: bool = True
    ):
        super().__init__(
            name="ConsecutiveLosses",
            breaker_type=BreakerType.CONSECUTIVE_LOSSES,
            action=action,
            enabled=enabled
        )
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0

    def record_trade(self, pnl: float):
        """
        Record trade result.

        Args:
            pnl: Trade P&L
        """
        if pnl < 0:
            self.consecutive_losses += 1

            if self.consecutive_losses >= self.max_consecutive_losses:
                self.trip(
                    f"{self.consecutive_losses} consecutive losing trades",
                    metadata={"consecutive_losses": self.consecutive_losses}
                )
        else:
            self.consecutive_losses = 0

    def check(self) -> bool:
        """Check if consecutive loss limit exceeded."""
        return self.is_tripped


class CircuitBreakerManager:
    """
    Manages all circuit breakers and coordinates emergency actions.
    """

    def __init__(
        self,
        max_daily_loss: float,
        max_drawdown: float,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize circuit breaker manager.

        Args:
            max_daily_loss: Maximum daily loss
            max_drawdown: Maximum drawdown
            alert_callback: Callback for alerts
        """
        self.logger = get_logger("circuit_breakers")
        self.alert_callback = alert_callback

        # Initialize breakers
        self.breakers: Dict[str, CircuitBreaker] = {
            "daily_loss": DailyLossBreaker(
                max_daily_loss=max_daily_loss,
                action=BreakerAction.PAUSE_TRADING
            ),
            "drawdown": DrawdownBreaker(
                max_drawdown=max_drawdown,
                action=BreakerAction.PAUSE_TRADING
            ),
            "api_error": APIErrorBreaker(
                max_consecutive_errors=10,
                action=BreakerAction.PAUSE_TRADING
            ),
            "volatility": VolatilityBreaker(
                max_move_percent=50,
                time_window_minutes=5,
                action=BreakerAction.ALERT_ONLY
            ),
            "consecutive_losses": ConsecutiveLossesBreaker(
                max_consecutive_losses=5,
                action=BreakerAction.PAUSE_TRADING
            )
        }

        # Event history
        self.events: List[BreakerEvent] = []

        # Kill switch
        self.kill_switch_active = False

    def check_all(
        self,
        daily_pnl: float,
        current_drawdown: float,
        symbol_prices: Optional[Dict[str, float]] = None
    ) -> List[BreakerEvent]:
        """
        Check all circuit breakers.

        Args:
            daily_pnl: Current daily P&L
            current_drawdown: Current drawdown
            symbol_prices: Current prices for volatility check

        Returns:
            List of breaker events
        """
        events = []

        # Daily loss
        if self.breakers["daily_loss"].check(daily_pnl):
            events.append(self.breakers["daily_loss"].last_trip_time)

        # Drawdown
        if self.breakers["drawdown"].check(current_drawdown):
            events.append(self.breakers["drawdown"].last_trip_time)

        # API errors
        if self.breakers["api_error"].check():
            events.append(self.breakers["api_error"].last_trip_time)

        # Volatility (if prices provided)
        if symbol_prices:
            for symbol, price in symbol_prices.items():
                self.breakers["volatility"].update_price(symbol, price)

        # Consecutive losses
        if self.breakers["consecutive_losses"].check():
            events.append(self.breakers["consecutive_losses"].last_trip_time)

        # Send alerts
        if events and self.alert_callback:
            asyncio.create_task(self.alert_callback(events))

        # Add to history
        self.events.extend(events)

        return events

    def record_api_error(self):
        """Record an API error."""
        self.breakers["api_error"].record_error()

    def record_api_success(self):
        """Record successful API call."""
        self.breakers["api_error"].record_success()

    def record_trade(self, pnl: float):
        """
        Record trade result.

        Args:
            pnl: Trade P&L
        """
        self.breakers["consecutive_losses"].record_trade(pnl)

    def activate_kill_switch(self, reason: str):
        """
        Activate emergency kill switch.

        Args:
            reason: Reason for activation
        """
        self.kill_switch_active = True

        event = BreakerEvent(
            breaker_type=BreakerType.MANUAL,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            action_taken=BreakerAction.CLOSE_ALL_POSITIONS
        )

        self.events.append(event)

        self.logger.critical(
            f"KILL SWITCH ACTIVATED: {reason}",
            category=LogCategory.RISK,
            reason=reason
        )

        if self.alert_callback:
            asyncio.create_task(self.alert_callback([event]))

    def deactivate_kill_switch(self):
        """Deactivate kill switch."""
        self.kill_switch_active = False

        self.logger.info(
            "Kill switch deactivated",
            category=LogCategory.RISK
        )

    def is_trading_allowed(self) -> bool:
        """
        Check if trading is allowed.

        Returns:
            True if trading allowed
        """
        if self.kill_switch_active:
            return False

        # Check if any critical breakers are tripped
        for breaker in self.breakers.values():
            if breaker.is_tripped and breaker.action == BreakerAction.PAUSE_TRADING:
                return False

        return True

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()

        self.logger.info(
            "All circuit breakers reset",
            category=LogCategory.RISK
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all breakers.

        Returns:
            Status dict
        """
        return {
            "kill_switch_active": self.kill_switch_active,
            "trading_allowed": self.is_trading_allowed(),
            "breakers": {
                name: {
                    "tripped": breaker.is_tripped,
                    "trip_count": breaker.trip_count,
                    "last_trip": breaker.last_trip_time.isoformat() if breaker.last_trip_time else None
                }
                for name, breaker in self.breakers.items()
            },
            "total_events": len(self.events)
        }
