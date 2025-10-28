"""
Tests for order book functionality.
"""

import pytest
from src.data.market_data import OrderBook, OrderBookLevel


class TestOrderBook:
    """Test suite for OrderBook."""

    def test_mid_price_calculation(self, sample_order_book):
        """Test mid price calculation."""
        mid_price = sample_order_book.get_mid_price()

        # Mid price should be average of best bid and ask
        # (100.0 + 100.5) / 2 = 100.25
        assert mid_price == 100.25

    def test_spread_calculation(self, sample_order_book):
        """Test spread calculation."""
        spread = sample_order_book.get_spread()

        # Spread = best ask - best bid = 100.5 - 100.0 = 0.5
        assert spread == 0.5

    def test_spread_bps_calculation(self, sample_order_book):
        """Test spread in basis points."""
        spread_bps = sample_order_book.get_spread_bps()

        # Spread BPS = (spread / mid) * 10000
        # = (0.5 / 100.25) * 10000 ≈ 49.88
        assert spread_bps == pytest.approx(49.88, rel=0.01)

    def test_imbalance_calculation_balanced(self, sample_order_book):
        """Test imbalance calculation for balanced book."""
        imbalance = sample_order_book.get_imbalance(depth=5)

        # Total bids = 10 + 15 + 20 + 12 + 8 = 65
        # Total asks = 8 + 12 + 18 + 14 + 10 = 62
        # Imbalance = (65 - 62) / (65 + 62) = 3 / 127 ≈ 0.024
        assert imbalance == pytest.approx(0.024, rel=0.01)

    def test_imbalance_calculation_bullish(self, imbalanced_order_book_bullish):
        """Test imbalance calculation for bullish book."""
        imbalance = imbalanced_order_book_bullish.get_imbalance(depth=5)

        # Total bids = 50 + 45 + 40 + 35 + 30 = 200
        # Total asks = 5 + 6 + 7 + 8 + 9 = 35
        # Imbalance = (200 - 35) / (200 + 35) = 165 / 235 ≈ 0.702
        assert imbalance == pytest.approx(0.702, rel=0.01)

        # Should be strongly bullish
        assert imbalance > 0.6

    def test_liquidity_calculation(self, sample_order_book):
        """Test liquidity metrics."""
        liquidity = sample_order_book.get_liquidity(depth=5)

        # Bid liquidity = sum(price * size) for bids
        # = 100*10 + 99.5*15 + 99*20 + 98.5*12 + 98*8
        # = 1000 + 1492.5 + 1980 + 1182 + 784 = 6438.5
        expected_bid_liq = 6438.5

        # Ask liquidity = sum(price * size) for asks
        # = 100.5*8 + 101*12 + 101.5*18 + 102*14 + 102.5*10
        # = 804 + 1212 + 1827 + 1428 + 1025 = 6296
        expected_ask_liq = 6296.0

        assert liquidity["bid_liquidity"] == pytest.approx(expected_bid_liq, rel=0.01)
        assert liquidity["ask_liquidity"] == pytest.approx(expected_ask_liq, rel=0.01)
        assert liquidity["total_liquidity"] == pytest.approx(
            expected_bid_liq + expected_ask_liq, rel=0.01
        )
