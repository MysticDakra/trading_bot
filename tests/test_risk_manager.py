"""
Tests for risk management system.
"""

import pytest
from src.risk.risk_manager import RiskManager


class TestRiskManager:
    """Test suite for RiskManager."""

    def test_initialization(self):
        """Test risk manager initialization."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000,
            default_leverage=4,
            max_leverage=8
        )

        assert risk_manager.active_capital == 15000
        assert risk_manager.max_daily_loss == 750
        assert risk_manager.max_drawdown == 3000
        assert risk_manager.default_leverage == 4
        assert risk_manager.max_leverage == 8

    def test_kelly_position_sizing(self):
        """Test Kelly Criterion position sizing."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000
        )

        # Good strategy: 60% win rate, avg win $200, avg loss $100
        position_fraction = risk_manager.calculate_kelly_position_size(
            win_rate=0.60,
            avg_win=200,
            avg_loss=100
        )

        # Should get positive sizing
        assert position_fraction > 0
        # Should be less than 25% (capped for safety)
        assert position_fraction <= 0.25

    def test_liquidation_price_calculation(self):
        """Test liquidation price calculation."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000
        )

        # Long position at $100 with 4x leverage
        liq_price_long = risk_manager.calculate_liquidation_price(
            entry_price=100,
            leverage=4,
            side="long"
        )

        # Liquidation should be below entry for longs
        assert liq_price_long < 100

        # Short position at $100 with 4x leverage
        liq_price_short = risk_manager.calculate_liquidation_price(
            entry_price=100,
            leverage=4,
            side="short"
        )

        # Liquidation should be above entry for shorts
        assert liq_price_short > 100

    def test_position_allowed_check(self):
        """Test position allowed validation."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000,
            max_concurrent_positions=4
        )

        # First position should be allowed
        allowed, reason = risk_manager.check_position_allowed(
            symbol="SOL",
            position_size=2000,
            leverage=4
        )
        assert allowed is True
        assert reason is None

    def test_position_tracking(self):
        """Test position addition and tracking."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000
        )

        # Add position
        success = risk_manager.add_position(
            symbol="SOL",
            side="long",
            entry_price=100.0,
            quantity=10.0,
            leverage=4
        )

        assert success is True
        assert "SOL" in risk_manager.positions
        assert risk_manager.positions["SOL"].side == "long"
        assert risk_manager.positions["SOL"].entry_price == 100.0

    def test_daily_loss_limit_enforcement(self):
        """Test daily loss limit enforcement."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000
        )

        # Simulate large loss
        risk_manager.daily_pnl = -800

        # Should not allow new position
        allowed, reason = risk_manager.check_position_allowed(
            symbol="SOL",
            position_size=1000,
            leverage=4
        )

        assert allowed is False
        assert "Daily loss limit exceeded" in reason

    def test_max_concurrent_positions(self):
        """Test maximum concurrent positions limit."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000,
            max_concurrent_positions=2
        )

        # Add two positions
        risk_manager.add_position("SOL", "long", 100.0, 10.0, 4)
        risk_manager.add_position("HYPE", "long", 50.0, 20.0, 4)

        # Third position should be rejected
        allowed, reason = risk_manager.check_position_allowed(
            symbol="DOGE",
            position_size=1000,
            leverage=4
        )

        assert allowed is False
        assert "Maximum concurrent positions" in reason

    def test_pnl_calculation(self):
        """Test P&L calculation."""
        risk_manager = RiskManager(
            active_capital=15000,
            max_daily_loss=750,
            max_drawdown=3000
        )

        # Add position
        risk_manager.add_position("SOL", "long", 100.0, 10.0, 4)

        # Close position with profit
        pnl = risk_manager.close_position("SOL", 105.0)

        # P&L = (exit - entry) * quantity * leverage
        # = (105 - 100) * 10 * 4 = 200
        assert pnl == 200.0
        assert risk_manager.daily_pnl == 200.0
        assert risk_manager.total_pnl == 200.0
