"""
Structured logging system with PostgreSQL persistence and audit trails.
Provides microsecond-precision timestamps and JSON formatting.
"""

import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import structlog
from pythonjsonlogger import jsonlogger
import asyncpg
from enum import Enum


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for filtering and analysis."""
    SYSTEM = "system"
    MARKET_DATA = "market_data"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    RISK = "risk"
    NANSEN = "nansen"
    AI = "ai"
    TRADE = "trade"
    PERFORMANCE = "performance"


class TradingLogger:
    """
    Structured logger with PostgreSQL persistence.

    Features:
    - Microsecond timestamp precision
    - JSON structured logging
    - PostgreSQL audit trail
    - Category-based filtering
    - Trade-specific logging
    """

    def __init__(
        self,
        name: str,
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_to_database: bool = True,
        log_dir: Optional[Path] = None
    ):
        """
        Initialize trading logger.

        Args:
            name: Logger name
            log_level: Logging level
            log_to_file: Enable file logging
            log_to_database: Enable database logging
            log_dir: Directory for log files
        """
        self.name = name
        self.log_level = getattr(logging, log_level.upper())
        self.log_to_database = log_to_database
        self.db_pool: Optional[asyncpg.Pool] = None

        # Set up log directory
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir

        # Configure structlog
        self._configure_structlog()

        # Set up file logging if enabled
        if log_to_file:
            self._setup_file_logging()

        self.logger = structlog.get_logger(name)

    def _configure_structlog(self):
        """Configure structlog with processors."""
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(self.log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _setup_file_logging(self):
        """Set up JSON file logging with rotation."""
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.jsonl"

        # Create custom JSON formatter
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.log_level)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    async def init_database(self, connection_string: str):
        """
        Initialize database connection pool for log persistence.

        Args:
            connection_string: PostgreSQL connection string
        """
        if not self.log_to_database:
            return

        self.db_pool = await asyncpg.create_pool(
            connection_string,
            min_size=2,
            max_size=10
        )

        # Create logs table if not exists
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    logger_name VARCHAR(100) NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    category VARCHAR(50),
                    message TEXT NOT NULL,
                    context JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_logs_category ON system_logs(category);
                CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    trade_id VARCHAR(100) UNIQUE NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    quantity DECIMAL(18, 8) NOT NULL,
                    price DECIMAL(18, 8) NOT NULL,
                    strategy VARCHAR(100),
                    nansen_signal JSONB,
                    execution_details JSONB,
                    pnl DECIMAL(18, 8),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_trade_logs_timestamp ON trade_logs(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_trade_logs_symbol ON trade_logs(symbol);
                CREATE INDEX IF NOT EXISTS idx_trade_logs_strategy ON trade_logs(strategy);
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    cycle_id VARCHAR(100) NOT NULL,
                    decision_type VARCHAR(50) NOT NULL,
                    asset VARCHAR(20),
                    action VARCHAR(20),
                    confidence DECIMAL(5, 4),
                    reasoning TEXT,
                    nansen_data JSONB,
                    technical_data JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_decision_logs_timestamp ON decision_logs(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_decision_logs_asset ON decision_logs(asset);
            """)

    async def log_to_db(
        self,
        level: str,
        message: str,
        category: Optional[LogCategory] = None,
        **context
    ):
        """
        Log message to PostgreSQL database.

        Args:
            level: Log level
            message: Log message
            category: Log category
            **context: Additional context
        """
        if not self.log_to_database or not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO system_logs (timestamp, logger_name, level, category, message, context)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    datetime.now(timezone.utc),
                    self.name,
                    level,
                    category.value if category else None,
                    message,
                    context if context else None
                )
        except Exception as e:
            # Don't let logging failures crash the app
            print(f"Failed to log to database: {e}")

    def debug(self, message: str, category: Optional[LogCategory] = None, **context):
        """Log debug message."""
        self.logger.debug(message, category=category.value if category else None, **context)

    def info(self, message: str, category: Optional[LogCategory] = None, **context):
        """Log info message."""
        self.logger.info(message, category=category.value if category else None, **context)

    def warning(self, message: str, category: Optional[LogCategory] = None, **context):
        """Log warning message."""
        self.logger.warning(message, category=category.value if category else None, **context)

    def error(self, message: str, category: Optional[LogCategory] = None, **context):
        """Log error message."""
        self.logger.error(message, category=category.value if category else None, **context)

    def critical(self, message: str, category: Optional[LogCategory] = None, **context):
        """Log critical message."""
        self.logger.critical(message, category=category.value if category else None, **context)

    async def log_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy: Optional[str] = None,
        nansen_signal: Optional[Dict[str, Any]] = None,
        execution_details: Optional[Dict[str, Any]] = None,
        pnl: Optional[float] = None
    ):
        """
        Log trade execution to database.

        Args:
            trade_id: Unique trade identifier
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Trade quantity
            price: Execution price
            strategy: Strategy name
            nansen_signal: Nansen signal data
            execution_details: Execution details
            pnl: Realized P&L
        """
        if not self.log_to_database or not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO trade_logs
                    (timestamp, trade_id, symbol, side, quantity, price, strategy, nansen_signal, execution_details, pnl)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (trade_id) DO UPDATE SET
                        pnl = EXCLUDED.pnl,
                        execution_details = EXCLUDED.execution_details
                    """,
                    datetime.now(timezone.utc),
                    trade_id,
                    symbol,
                    side,
                    quantity,
                    price,
                    strategy,
                    nansen_signal,
                    execution_details,
                    pnl
                )

            self.info(
                f"Trade executed: {side} {quantity} {symbol} @ {price}",
                category=LogCategory.TRADE,
                trade_id=trade_id,
                strategy=strategy,
                pnl=pnl
            )

        except Exception as e:
            self.error(f"Failed to log trade: {e}", category=LogCategory.SYSTEM)

    async def log_decision(
        self,
        cycle_id: str,
        decision_type: str,
        asset: Optional[str] = None,
        action: Optional[str] = None,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
        nansen_data: Optional[Dict[str, Any]] = None,
        technical_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log AI reasoning decision to database.

        Args:
            cycle_id: Reasoning cycle identifier
            decision_type: Type of decision
            asset: Asset symbol
            action: Proposed action
            confidence: Confidence score
            reasoning: Decision reasoning
            nansen_data: Nansen input data
            technical_data: Technical analysis data
        """
        if not self.log_to_database or not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO decision_logs
                    (timestamp, cycle_id, decision_type, asset, action, confidence, reasoning, nansen_data, technical_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    datetime.now(timezone.utc),
                    cycle_id,
                    decision_type,
                    asset,
                    action,
                    confidence,
                    reasoning,
                    nansen_data,
                    technical_data
                )

            self.info(
                f"Decision logged: {decision_type} for {asset}",
                category=LogCategory.AI,
                cycle_id=cycle_id,
                action=action,
                confidence=confidence
            )

        except Exception as e:
            self.error(f"Failed to log decision: {e}", category=LogCategory.SYSTEM)

    async def close(self):
        """Close database connections."""
        if self.db_pool:
            await self.db_pool.close()


# Global logger instance
_logger_instance: Optional[TradingLogger] = None


def get_logger(name: str = "trading_system") -> TradingLogger:
    """
    Get global logger instance.

    Args:
        name: Logger name

    Returns:
        TradingLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        from src.core.config import get_config
        config = get_config()
        _logger_instance = TradingLogger(
            name=name,
            log_level=config.log_level,
            log_to_file=True,
            log_to_database=True
        )
    return _logger_instance
