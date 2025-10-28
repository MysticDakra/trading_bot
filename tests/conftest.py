"""
Pytest configuration and shared fixtures.
"""

import pytest
from datetime import datetime, timezone
from src.data.market_data import OrderBook, OrderBookLevel


@pytest.fixture
def sample_order_book():
    """Create sample order book for testing."""
    order_book = OrderBook(symbol="SOL")

    # Add bids (descending by price)
    order_book.bids = [
        OrderBookLevel(price=100.0, size=10.0),
        OrderBookLevel(price=99.5, size=15.0),
        OrderBookLevel(price=99.0, size=20.0),
        OrderBookLevel(price=98.5, size=12.0),
        OrderBookLevel(price=98.0, size=8.0),
    ]

    # Add asks (ascending by price)
    order_book.asks = [
        OrderBookLevel(price=100.5, size=8.0),
        OrderBookLevel(price=101.0, size=12.0),
        OrderBookLevel(price=101.5, size=18.0),
        OrderBookLevel(price=102.0, size=14.0),
        OrderBookLevel(price=102.5, size=10.0),
    ]

    return order_book


@pytest.fixture
def imbalanced_order_book_bullish():
    """Create bullish imbalanced order book."""
    order_book = OrderBook(symbol="SOL")

    # Heavy bids
    order_book.bids = [
        OrderBookLevel(price=100.0, size=50.0),
        OrderBookLevel(price=99.5, size=45.0),
        OrderBookLevel(price=99.0, size=40.0),
        OrderBookLevel(price=98.5, size=35.0),
        OrderBookLevel(price=98.0, size=30.0),
    ]

    # Light asks
    order_book.asks = [
        OrderBookLevel(price=100.5, size=5.0),
        OrderBookLevel(price=101.0, size=6.0),
        OrderBookLevel(price=101.5, size=7.0),
        OrderBookLevel(price=102.0, size=8.0),
        OrderBookLevel(price=102.5, size=9.0),
    ]

    return order_book
