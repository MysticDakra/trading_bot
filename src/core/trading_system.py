"""
Main trading system coordinator.

Orchestrates:
- Market data collection
- Nansen intelligence gathering
- AI reasoning engine
- Strategy execution
- Risk management
- Circuit breakers
- Monitoring
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from src.core.config import get_config
from src.core.logger import get_logger, LogCategory
from src.data.market_data import HyperliquidWebSocket, OrderBook
from src.data.nansen_client import NansenMCPClient
from src.ai.reasoning_engine import ContinuousReasoningEngine, TradingAction
from src.strategies.imbalance_strategy import OrderBookImbalanceStrategy
from src.strategies.smart_momentum_strategy import SmartMoneyMomentumStrategy
from src.execution.executor import HyperliquidExecutor, OrderSide
from src.risk.risk_manager import RiskManager
from src.risk.circuit_breakers import CircuitBreakerManager


class TradingSystem:
    """
    Main trading system coordinator.

    Manages entire trading lifecycle from data collection to execution.
    """

    def __init__(self):
        """Initialize trading system."""
        self.config = get_config()
        self.logger = get_logger("trading_system")

        # Initialize components
        self.websocket: Optional[HyperliquidWebSocket] = None
        self.nansen_client: Optional[NansenMCPClient] = None
        self.reasoning_engine: Optional[ContinuousReasoningEngine] = None
        self.executor: Optional[HyperliquidExecutor] = None
        self.risk_manager: Optional[RiskManager] = None
        self.circuit_breakers: Optional[CircuitBreakerManager] = None

        # Strategies
        self.strategies: Dict = {}

        # State
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def initialize(self):
        """Initialize all components."""
        self.logger.info(
            "Initializing trading system",
            category=LogCategory.SYSTEM,
            config=self.config.to_dict()
        )

        # Initialize WebSocket
        self.websocket = HyperliquidWebSocket(
            ws_url="wss://api.hyperliquid.xyz/ws",
            reconnect_delay=5,
            max_reconnect_attempts=10,
            ping_interval=30
        )

        # Subscribe to market data updates
        self.websocket.subscribe_orderbook(self._on_orderbook_update)

        # Initialize Nansen client
        self.nansen_client = NansenMCPClient(
            api_key=self.config.nansen.api_key,
            mcp_server_url=self.config.nansen.mcp_server_url,
            query_interval=150  # 2.5 minutes
        )
        await self.nansen_client.init()

        # Initialize AI reasoning engine
        self.reasoning_engine = ContinuousReasoningEngine(
            nansen_client=self.nansen_client,
            symbols=self.config.get_enabled_pairs(),
            query_interval=150
        )

        # Initialize executor
        self.executor = HyperliquidExecutor(
            api_key=self.config.hyperliquid.api_key,
            private_key=self.config.hyperliquid.private_key,
            testnet=self.config.hyperliquid.testnet,
            max_slippage_bps=self.config.max_slippage_bps,
            order_timeout=self.config.order_timeout_seconds,
            max_retries=self.config.max_retry_attempts
        )
        await self.executor.init()

        # Initialize risk manager
        self.risk_manager = RiskManager(
            active_capital=self.config.risk.active_capital,
            max_daily_loss=self.config.risk.max_daily_loss,
            max_drawdown=self.config.risk.max_drawdown,
            default_leverage=self.config.risk.default_leverage,
            max_leverage=self.config.risk.max_leverage,
            max_concurrent_positions=self.config.max_concurrent_positions
        )

        # Initialize circuit breakers
        self.circuit_breakers = CircuitBreakerManager(
            max_daily_loss=self.config.risk.max_daily_loss,
            max_drawdown=self.config.risk.max_drawdown,
            alert_callback=self._send_alert
        )

        # Initialize strategies
        if self.config.orderbook_imbalance.enabled:
            self.strategies["orderbook_imbalance"] = OrderBookImbalanceStrategy(
                imbalance_threshold=self.config.orderbook_imbalance.imbalance_threshold,
                holding_period_seconds=self.config.orderbook_imbalance.holding_period_seconds,
                stop_loss_bps=self.config.orderbook_imbalance.stop_loss_bps,
                take_profit_bps=self.config.orderbook_imbalance.take_profit_bps,
                nansen_confirmation_required=self.config.orderbook_imbalance.nansen_confirmation_required
            )

        if self.config.smart_momentum.enabled:
            self.strategies["smart_momentum"] = SmartMoneyMomentumStrategy(
                nansen_weight=self.config.smart_momentum.nansen_weight,
                technical_weight=self.config.smart_momentum.technical_weight,
                smart_money_threshold=self.config.smart_momentum.smart_money_threshold,
                scale_in_stages=self.config.smart_momentum.scale_in_stages,
                never_average_down=self.config.smart_momentum.never_average_down
            )

        # Initialize database logging
        await self.logger.init_database(self.config.database.connection_string)

        self.logger.info(
            f"Trading system initialized with {len(self.strategies)} strategies",
            category=LogCategory.SYSTEM,
            strategies=list(self.strategies.keys())
        )

    def _on_orderbook_update(self, symbol: str, order_book: OrderBook):
        """
        Handle order book update.

        Args:
            symbol: Trading pair symbol
            order_book: Updated order book
        """
        # Update reasoning engine
        if self.reasoning_engine:
            mid_price = order_book.get_mid_price()
            if mid_price:
                self.reasoning_engine.update_market_data(symbol, order_book, mid_price)

        # Update strategies
        for strategy in self.strategies.values():
            strategy.update_order_book(symbol, order_book)
            if mid_price:
                strategy.update_price(symbol, mid_price)

        # Update circuit breakers for volatility check
        if mid_price and self.circuit_breakers:
            self.circuit_breakers.check_all(
                daily_pnl=self.risk_manager.daily_pnl if self.risk_manager else 0,
                current_drawdown=self.risk_manager.current_drawdown if self.risk_manager else 0,
                symbol_prices={symbol: mid_price}
            )

    async def _send_alert(self, events):
        """
        Send alerts for circuit breaker events.

        Args:
            events: List of breaker events
        """
        for event in events:
            self.logger.critical(
                f"ALERT: {event.breaker_type.value} - {event.reason}",
                category=LogCategory.RISK,
                event=event.__dict__
            )

            # In production, send to Discord/Telegram
            # await self._send_discord_alert(event)
            # await self._send_telegram_alert(event)

    async def _trading_loop(self):
        """Main trading loop."""
        while self._running:
            try:
                # Check if trading is allowed
                if not self.circuit_breakers.is_trading_allowed():
                    self.logger.warning(
                        "Trading paused by circuit breakers",
                        category=LogCategory.SYSTEM
                    )
                    await asyncio.sleep(60)
                    continue

                # Reset daily metrics if new day
                self.risk_manager.reset_daily_metrics()

                # Check risk metrics
                risk_metrics = self.risk_manager.get_risk_metrics()

                # Check circuit breakers
                self.circuit_breakers.check_all(
                    daily_pnl=self.risk_manager.daily_pnl,
                    current_drawdown=self.risk_manager.current_drawdown
                )

                # Get latest AI decisions
                for symbol in self.config.get_enabled_pairs():
                    decision = self.reasoning_engine.get_latest_decision(symbol)

                    if decision and decision.action != TradingAction.HOLD:
                        # Execute trading decision
                        await self._execute_decision(decision)

                # Check strategy signals
                for symbol in self.config.get_enabled_pairs():
                    for strategy_name, strategy in self.strategies.items():
                        if not strategy.enabled:
                            continue

                        signal = await strategy.analyze(symbol)

                        if signal and signal.confidence > 0.6:
                            # Execute strategy signal
                            await self._execute_signal(signal, strategy_name)

                await asyncio.sleep(5)  # Main loop interval

            except Exception as e:
                self.logger.error(
                    f"Error in trading loop: {e}",
                    category=LogCategory.SYSTEM,
                    error=str(e)
                )
                await asyncio.sleep(10)

    async def _execute_decision(self, decision):
        """
        Execute AI reasoning decision.

        Args:
            decision: Trading decision from reasoning engine
        """
        if decision.action == TradingAction.BUY:
            await self._execute_buy(
                symbol=decision.asset,
                size_percent=decision.size_percent,
                leverage=decision.leverage,
                strategy_name="AI_Reasoning",
                metadata={"decision": decision.__dict__}
            )
        elif decision.action == TradingAction.SELL:
            await self._execute_sell(
                symbol=decision.asset,
                size_percent=decision.size_percent,
                leverage=decision.leverage,
                strategy_name="AI_Reasoning",
                metadata={"decision": decision.__dict__}
            )

    async def _execute_signal(self, signal, strategy_name):
        """
        Execute strategy signal.

        Args:
            signal: Trading signal
            strategy_name: Name of strategy
        """
        # Calculate position size
        position_sizing = self.risk_manager.calculate_position_size(
            symbol=signal.symbol,
            risk_percent=5.0,  # 5% risk per trade
            win_rate=self.strategies[strategy_name].performance.win_rate or 0.55,
            avg_win=self.strategies[strategy_name].performance.avg_win or 200,
            avg_loss=self.strategies[strategy_name].performance.avg_loss or 100
        )

        if signal.signal_type.value == "BUY":
            await self._execute_buy(
                symbol=signal.symbol,
                size_percent=18,  # Default 18% of capital
                leverage=signal.leverage or 4,
                strategy_name=strategy_name,
                metadata={"signal": signal.__dict__}
            )
        elif signal.signal_type.value == "SELL":
            await self._execute_sell(
                symbol=signal.symbol,
                size_percent=18,
                leverage=signal.leverage or 4,
                strategy_name=strategy_name,
                metadata={"signal": signal.__dict__}
            )

    async def _execute_buy(
        self,
        symbol: str,
        size_percent: float,
        leverage: int,
        strategy_name: str,
        metadata: dict
    ):
        """Execute buy order."""
        # Calculate position size
        capital_to_deploy = self.risk_manager.active_capital * (size_percent / 100)

        # Check if position allowed
        allowed, reason = self.risk_manager.check_position_allowed(
            symbol=symbol,
            position_size=capital_to_deploy,
            leverage=leverage
        )

        if not allowed:
            self.logger.warning(
                f"Position not allowed: {reason}",
                category=LogCategory.EXECUTION,
                symbol=symbol,
                reason=reason
            )
            return

        # Place order
        order = await self.executor.place_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=capital_to_deploy,  # Simplified
            leverage=leverage,
            metadata=metadata
        )

        if order:
            # Record position
            self.risk_manager.add_position(
                symbol=symbol,
                side="long",
                entry_price=order.average_fill_price,
                quantity=order.filled_quantity,
                leverage=leverage
            )

            # Log trade
            await self.logger.log_trade(
                trade_id=order.order_id,
                symbol=symbol,
                side="BUY",
                quantity=order.filled_quantity,
                price=order.average_fill_price,
                strategy=strategy_name,
                nansen_signal=metadata.get("nansen_data")
            )

    async def _execute_sell(
        self,
        symbol: str,
        size_percent: float,
        leverage: int,
        strategy_name: str,
        metadata: dict
    ):
        """Execute sell order."""
        # Similar to _execute_buy but for short positions
        capital_to_deploy = self.risk_manager.active_capital * (size_percent / 100)

        allowed, reason = self.risk_manager.check_position_allowed(
            symbol=symbol,
            position_size=capital_to_deploy,
            leverage=leverage
        )

        if not allowed:
            self.logger.warning(
                f"Position not allowed: {reason}",
                category=LogCategory.EXECUTION,
                symbol=symbol,
                reason=reason
            )
            return

        order = await self.executor.place_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=capital_to_deploy,
            leverage=leverage,
            metadata=metadata
        )

        if order:
            self.risk_manager.add_position(
                symbol=symbol,
                side="short",
                entry_price=order.average_fill_price,
                quantity=order.filled_quantity,
                leverage=leverage
            )

            await self.logger.log_trade(
                trade_id=order.order_id,
                symbol=symbol,
                side="SELL",
                quantity=order.filled_quantity,
                price=order.average_fill_price,
                strategy=strategy_name,
                nansen_signal=metadata.get("nansen_data")
            )

    async def start(self):
        """Start trading system."""
        if self._running:
            self.logger.warning(
                "Trading system already running",
                category=LogCategory.SYSTEM
            )
            return

        self._running = True

        self.logger.info(
            "Starting trading system",
            category=LogCategory.SYSTEM
        )

        # Start WebSocket
        await self.websocket.start()
        await self.websocket.subscribe_symbols(self.config.get_enabled_pairs())

        # Start reasoning engine
        await self.reasoning_engine.start()

        # Start trading loop
        trading_task = asyncio.create_task(self._trading_loop())
        self._tasks.append(trading_task)

        self.logger.info(
            "Trading system started successfully",
            category=LogCategory.SYSTEM,
            pairs=self.config.get_enabled_pairs()
        )

    async def stop(self):
        """Stop trading system."""
        self._running = False

        self.logger.info(
            "Stopping trading system",
            category=LogCategory.SYSTEM
        )

        # Stop reasoning engine
        if self.reasoning_engine:
            await self.reasoning_engine.stop()

        # Stop WebSocket
        if self.websocket:
            await self.websocket.disconnect()

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Close connections
        if self.executor:
            await self.executor.close()

        if self.nansen_client:
            await self.nansen_client.close()

        if self.logger:
            await self.logger.close()

        self.logger.info(
            "Trading system stopped",
            category=LogCategory.SYSTEM
        )

    async def emergency_shutdown(self):
        """Emergency shutdown - close all positions and stop."""
        self.logger.critical(
            "EMERGENCY SHUTDOWN INITIATED",
            category=LogCategory.SYSTEM
        )

        # Activate kill switch
        self.circuit_breakers.activate_kill_switch("Emergency shutdown")

        # Cancel all orders
        await self.executor.cancel_all_orders()

        # Close all positions
        # (Implementation depends on Hyperliquid API)

        # Stop system
        await self.stop()


async def main():
    """Main entry point."""
    system = TradingSystem()

    try:
        await system.initialize()
        await system.start()

        # Run until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
        await system.stop()

    except Exception as e:
        print(f"Fatal error: {e}")
        await system.emergency_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
