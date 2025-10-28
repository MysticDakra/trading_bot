"""
Real-time market data management via Hyperliquid WebSocket.
Handles automatic reconnection, order book reconstruction, and data distribution.
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from src.core.logger import get_logger, LogCategory


@dataclass
class OrderBookLevel:
    """Single order book price level."""
    price: float
    size: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderBook:
    """L2 order book for a trading pair."""
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_mid_price(self) -> Optional[float]:
        """Get mid-market price."""
        if not self.bids or not self.asks:
            return None
        return (self.bids[0].price + self.asks[0].price) / 2

    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        if not self.bids or not self.asks:
            return None
        return self.asks[0].price - self.bids[0].price

    def get_spread_bps(self) -> Optional[float]:
        """Get spread in basis points."""
        if not self.bids or not self.asks:
            return None
        mid = self.get_mid_price()
        if mid is None or mid == 0:
            return None
        return (self.get_spread() / mid) * 10000

    def get_imbalance(self, depth: int = 5) -> Optional[float]:
        """
        Calculate order book imbalance ratio.

        ρ = (V^bid - V^ask) / (V^bid + V^ask)

        Args:
            depth: Number of levels to consider

        Returns:
            Imbalance ratio between -1 and 1
        """
        if len(self.bids) < depth or len(self.asks) < depth:
            return None

        bid_volume = sum(level.size for level in self.bids[:depth])
        ask_volume = sum(level.size for level in self.asks[:depth])

        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0

        return (bid_volume - ask_volume) / total_volume

    def get_liquidity(self, depth: int = 5) -> Dict[str, float]:
        """
        Get liquidity metrics.

        Args:
            depth: Number of levels to consider

        Returns:
            Dict with bid_liquidity, ask_liquidity, total_liquidity
        """
        if len(self.bids) < depth or len(self.asks) < depth:
            return {"bid_liquidity": 0, "ask_liquidity": 0, "total_liquidity": 0}

        bid_liquidity = sum(level.price * level.size for level in self.bids[:depth])
        ask_liquidity = sum(level.price * level.size for level in self.asks[:depth])

        return {
            "bid_liquidity": bid_liquidity,
            "ask_liquidity": ask_liquidity,
            "total_liquidity": bid_liquidity + ask_liquidity
        }


class OrderBookManager:
    """
    Manages order books for multiple trading pairs.
    Reconstructs L2 order book from WebSocket updates.
    """

    def __init__(self, max_depth: int = 20):
        """
        Initialize order book manager.

        Args:
            max_depth: Maximum order book depth to maintain
        """
        self.max_depth = max_depth
        self.order_books: Dict[str, OrderBook] = {}
        self.logger = get_logger("market_data")

    def update_order_book(self, symbol: str, bids: List[List[float]], asks: List[List[float]]):
        """
        Update order book with new data.

        Args:
            symbol: Trading pair symbol
            bids: List of [price, size] bid levels
            asks: List of [price, size] ask levels
        """
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol=symbol)

        book = self.order_books[symbol]

        # Update bids (sorted descending by price)
        book.bids = [
            OrderBookLevel(price=price, size=size)
            for price, size in sorted(bids, key=lambda x: x[0], reverse=True)[:self.max_depth]
        ]

        # Update asks (sorted ascending by price)
        book.asks = [
            OrderBookLevel(price=price, size=size)
            for price, size in sorted(asks, key=lambda x: x[0])[:self.max_depth]
        ]

        book.last_update = datetime.now(timezone.utc)

    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Get order book for symbol."""
        return self.order_books.get(symbol)

    def get_all_order_books(self) -> Dict[str, OrderBook]:
        """Get all order books."""
        return self.order_books.copy()


class HyperliquidWebSocket:
    """
    WebSocket client for Hyperliquid real-time market data.

    Features:
    - Automatic reconnection with exponential backoff
    - Order book subscription
    - Trade subscription
    - Observer pattern for data distribution
    """

    def __init__(
        self,
        ws_url: str = "wss://api.hyperliquid.xyz/ws",
        reconnect_delay: int = 5,
        max_reconnect_attempts: int = 10,
        ping_interval: int = 30
    ):
        """
        Initialize WebSocket client.

        Args:
            ws_url: WebSocket endpoint URL
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_attempts: Maximum reconnection attempts
            ping_interval: Ping interval in seconds
        """
        self.ws_url = ws_url
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.order_book_manager = OrderBookManager()
        self.logger = get_logger("websocket")

        # Subscriptions
        self.subscribed_symbols: List[str] = []

        # Observer pattern callbacks
        self.orderbook_callbacks: List[Callable[[str, OrderBook], None]] = []
        self.trade_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Connection state
        self.is_connected = False
        self.reconnect_attempts = 0
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def subscribe_orderbook(self, callback: Callable[[str, OrderBook], None]):
        """
        Subscribe to order book updates.

        Args:
            callback: Callback function(symbol, order_book)
        """
        self.orderbook_callbacks.append(callback)

    def subscribe_trades(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Subscribe to trade updates.

        Args:
            callback: Callback function(trade_data)
        """
        self.trade_callbacks.append(callback)

    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.logger.info(
                f"Connecting to Hyperliquid WebSocket: {self.ws_url}",
                category=LogCategory.MARKET_DATA
            )

            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=self.ping_interval,
                ping_timeout=10,
                close_timeout=10
            )

            self.is_connected = True
            self.reconnect_attempts = 0

            self.logger.info(
                "WebSocket connected successfully",
                category=LogCategory.MARKET_DATA
            )

            # Resubscribe to symbols after reconnection
            if self.subscribed_symbols:
                await self._resubscribe()

        except Exception as e:
            self.logger.error(
                f"WebSocket connection failed: {e}",
                category=LogCategory.MARKET_DATA
            )
            raise

    async def disconnect(self):
        """Disconnect WebSocket."""
        self._running = False
        self.is_connected = False

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        self.logger.info(
            "WebSocket disconnected",
            category=LogCategory.MARKET_DATA
        )

    async def subscribe_symbols(self, symbols: List[str]):
        """
        Subscribe to market data for symbols.

        Args:
            symbols: List of trading pair symbols
        """
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                self.subscribed_symbols.append(symbol)

        if self.is_connected:
            await self._resubscribe()

    async def _resubscribe(self):
        """Resubscribe to all symbols after reconnection."""
        for symbol in self.subscribed_symbols:
            # Subscribe to L2 order book
            subscribe_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "l2Book",
                    "coin": symbol
                }
            }
            await self.websocket.send(json.dumps(subscribe_msg))

            # Subscribe to trades
            trade_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "trades",
                    "coin": symbol
                }
            }
            await self.websocket.send(json.dumps(trade_msg))

            self.logger.info(
                f"Subscribed to {symbol}",
                category=LogCategory.MARKET_DATA,
                symbol=symbol
            )

    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket message.

        Args:
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)

            # Handle order book updates
            if data.get("channel") == "l2Book":
                await self._handle_orderbook_update(data)

            # Handle trade updates
            elif data.get("channel") == "trades":
                await self._handle_trade_update(data)

        except Exception as e:
            self.logger.error(
                f"Error handling WebSocket message: {e}",
                category=LogCategory.MARKET_DATA,
                error=str(e)
            )

    async def _handle_orderbook_update(self, data: Dict[str, Any]):
        """Handle order book update."""
        try:
            symbol = data["data"]["coin"]
            levels = data["data"]["levels"]

            bids = [[float(level[0]["px"]), float(level[0]["sz"])] for level in levels if level[0]["side"] == "B"]
            asks = [[float(level[0]["px"]), float(level[0]["sz"])] for level in levels if level[0]["side"] == "A"]

            # Update order book manager
            self.order_book_manager.update_order_book(symbol, bids, asks)

            # Notify subscribers
            order_book = self.order_book_manager.get_order_book(symbol)
            if order_book:
                for callback in self.orderbook_callbacks:
                    try:
                        callback(symbol, order_book)
                    except Exception as e:
                        self.logger.error(
                            f"Error in orderbook callback: {e}",
                            category=LogCategory.MARKET_DATA
                        )

        except Exception as e:
            self.logger.error(
                f"Error processing orderbook update: {e}",
                category=LogCategory.MARKET_DATA
            )

    async def _handle_trade_update(self, data: Dict[str, Any]):
        """Handle trade update."""
        try:
            for callback in self.trade_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(
                        f"Error in trade callback: {e}",
                        category=LogCategory.MARKET_DATA
                    )

        except Exception as e:
            self.logger.error(
                f"Error processing trade update: {e}",
                category=LogCategory.MARKET_DATA
            )

    async def _message_handler(self):
        """Main message handling loop."""
        while self._running and self.websocket:
            try:
                message = await self.websocket.recv()
                await self._handle_message(message)

            except ConnectionClosed:
                self.logger.warning(
                    "WebSocket connection closed",
                    category=LogCategory.MARKET_DATA
                )
                await self._reconnect()

            except Exception as e:
                self.logger.error(
                    f"Error in message handler: {e}",
                    category=LogCategory.MARKET_DATA
                )
                await self._reconnect()

    async def _reconnect(self):
        """Reconnect with exponential backoff."""
        self.is_connected = False

        while self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))

            self.logger.info(
                f"Reconnecting in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})",
                category=LogCategory.MARKET_DATA
            )

            await asyncio.sleep(delay)

            try:
                await self.connect()
                return
            except Exception as e:
                self.logger.error(
                    f"Reconnection attempt {self.reconnect_attempts} failed: {e}",
                    category=LogCategory.MARKET_DATA
                )

        self.logger.critical(
            "Max reconnection attempts reached, stopping WebSocket",
            category=LogCategory.MARKET_DATA
        )
        self._running = False

    async def start(self):
        """Start WebSocket client."""
        self._running = True
        await self.connect()

        # Start message handler task
        handler_task = asyncio.create_task(self._message_handler())
        self._tasks.append(handler_task)

        self.logger.info(
            "WebSocket client started",
            category=LogCategory.MARKET_DATA
        )

    async def run(self):
        """Run WebSocket client (blocking)."""
        await self.start()

        # Wait for tasks
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            self.logger.info(
                "WebSocket tasks cancelled",
                category=LogCategory.MARKET_DATA
            )
        finally:
            await self.disconnect()
