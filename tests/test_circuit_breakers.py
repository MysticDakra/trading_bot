"""
Tests for circuit breakers.
"""

import pytest
from src.risk.circuit_breakers import (
    DailyLossBreaker,
    DrawdownBreaker,
    APIErrorBreaker,
    ConsecutiveLossesBreaker,
    BreakerAction
)


class TestDailyLossBreaker:
    """Test daily loss circuit breaker."""

    def test_no_trip_under_limit(self):
        """Test breaker doesn't trip under limit."""
        breaker = DailyLossBreaker(max_daily_loss=750)

        # Loss of $500 should not trip
        tripped = breaker.check(daily_pnl=-500)
        assert tripped is False
        assert breaker.is_tripped is False

    def test_trip_at_limit(self):
        """Test breaker trips at limit."""
        breaker = DailyLossBreaker(max_daily_loss=750)

        # Loss of $750 should trip
        tripped = breaker.check(daily_pnl=-750)
        assert tripped is True
        assert breaker.is_tripped is True

    def test_trip_over_limit(self):
        """Test breaker trips over limit."""
        breaker = DailyLossBreaker(max_daily_loss=750)

        # Loss of $800 should trip
        tripped = breaker.check(daily_pnl=-800)
        assert tripped is True
        assert breaker.is_tripped is True


class TestDrawdownBreaker:
    """Test drawdown circuit breaker."""

    def test_no_trip_under_limit(self):
        """Test breaker doesn't trip under limit."""
        breaker = DrawdownBreaker(max_drawdown=3000)

        tripped = breaker.check(current_drawdown=2000)
        assert tripped is False

    def test_trip_at_limit(self):
        """Test breaker trips at limit."""
        breaker = DrawdownBreaker(max_drawdown=3000)

        tripped = breaker.check(current_drawdown=3000)
        assert tripped is True


class TestAPIErrorBreaker:
    """Test API error circuit breaker."""

    def test_consecutive_errors(self):
        """Test consecutive error tracking."""
        breaker = APIErrorBreaker(max_consecutive_errors=5)

        # Record 4 errors - should not trip
        for _ in range(4):
            breaker.record_error()

        assert breaker.is_tripped is False

        # 5th error should trip
        breaker.record_error()
        assert breaker.is_tripped is True

    def test_error_reset_on_success(self):
        """Test errors reset on success."""
        breaker = APIErrorBreaker(max_consecutive_errors=5)

        # Record some errors
        for _ in range(3):
            breaker.record_error()

        # Record success - should reset
        breaker.record_success()
        assert breaker.consecutive_errors == 0


class TestConsecutiveLossesBreaker:
    """Test consecutive losses circuit breaker."""

    def test_consecutive_losses(self):
        """Test consecutive loss tracking."""
        breaker = ConsecutiveLossesBreaker(max_consecutive_losses=5)

        # Record 4 losses
        for _ in range(4):
            breaker.record_trade(pnl=-100)

        assert breaker.is_tripped is False

        # 5th loss should trip
        breaker.record_trade(pnl=-100)
        assert breaker.is_tripped is True

    def test_loss_reset_on_win(self):
        """Test losses reset on winning trade."""
        breaker = ConsecutiveLossesBreaker(max_consecutive_losses=5)

        # Record some losses
        for _ in range(3):
            breaker.record_trade(pnl=-100)

        # Record win - should reset
        breaker.record_trade(pnl=200)
        assert breaker.consecutive_losses == 0
