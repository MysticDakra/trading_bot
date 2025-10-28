"""
Configuration management with type-safe settings and validation.
Combines YAML config files with environment variables.
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import yaml
import os
from enum import Enum


class Environment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTNET = "testnet"


class HyperliquidConfig(BaseSettings):
    """Hyperliquid API configuration."""

    api_key: str = Field(..., env="HYPERLIQUID_API_KEY")
    private_key: str = Field(..., env="HYPERLIQUID_PRIVATE_KEY")
    testnet: bool = Field(False, env="HYPERLIQUID_TESTNET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    host: str = Field("localhost", env="POSTGRES_HOST")
    port: int = Field(5432, env="POSTGRES_PORT")
    database: str = Field("hyperliquid_trader", env="POSTGRES_DB")
    user: str = Field(..., env="POSTGRES_USER")
    password: str = Field(..., env="POSTGRES_PASSWORD")

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    class Config:
        env_file = ".env"


class RedisConfig(BaseSettings):
    """Redis configuration."""

    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")

    class Config:
        env_file = ".env"


class NansenConfig(BaseSettings):
    """Nansen MCP configuration."""

    api_key: str = Field(..., env="NANSEN_API_KEY")
    mcp_server_url: str = Field("http://localhost:3000", env="NANSEN_MCP_SERVER_URL")

    class Config:
        env_file = ".env"


class RiskConfig(BaseSettings):
    """Risk management configuration."""

    active_capital: float = Field(..., env="ACTIVE_CAPITAL")
    max_daily_loss: float = Field(..., env="MAX_DAILY_LOSS")
    max_drawdown: float = Field(..., env="MAX_DRAWDOWN")
    default_leverage: int = Field(4, env="DEFAULT_LEVERAGE")
    max_leverage: int = Field(8, env="MAX_LEVERAGE")

    @validator("max_daily_loss")
    def validate_daily_loss(cls, v, values):
        """Ensure daily loss is reasonable."""
        if "active_capital" in values and v > values["active_capital"] * 0.1:
            raise ValueError("Daily loss limit should be <= 10% of active capital")
        return v

    @validator("max_drawdown")
    def validate_drawdown(cls, v, values):
        """Ensure drawdown is reasonable."""
        if "active_capital" in values and v > values["active_capital"] * 0.3:
            raise ValueError("Max drawdown should be <= 30% of active capital")
        return v

    class Config:
        env_file = ".env"


class TradingPairConfig:
    """Configuration for a single trading pair."""

    def __init__(
        self,
        symbol: str,
        enabled: bool = True,
        max_position_size: float = 5000,
        min_order_size: float = 10
    ):
        self.symbol = symbol
        self.enabled = enabled
        self.max_position_size = max_position_size
        self.min_order_size = min_order_size


class StrategyConfig:
    """Base configuration for trading strategies."""

    def __init__(self, enabled: bool = True, **kwargs):
        self.enabled = enabled
        self.__dict__.update(kwargs)


class TradingConfig:
    """Main trading system configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize trading configuration.

        Args:
            config_path: Path to YAML config file. Defaults to config/trading_config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "trading_config.yaml"

        # Load YAML configuration
        with open(config_path, 'r') as f:
            self._yaml_config = yaml.safe_load(f)

        # Load environment-based configs
        self.hyperliquid = HyperliquidConfig()
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.nansen = NansenConfig()
        self.risk = RiskConfig()

        # Parse YAML sections
        self._parse_trading_config()
        self._parse_execution_config()
        self._parse_strategy_configs()
        self._parse_monitoring_config()

        # Deployment phase
        self.deployment_week = int(os.getenv("DEPLOYMENT_WEEK", "1"))
        self._apply_deployment_phase()

    def _parse_trading_config(self):
        """Parse trading section from YAML."""
        trading = self._yaml_config.get("trading", {})

        # Trading pairs
        self.pairs: List[TradingPairConfig] = []
        for pair_data in trading.get("pairs", []):
            self.pairs.append(TradingPairConfig(**pair_data))

        self.max_concurrent_positions = trading.get("max_concurrent_positions", 4)
        self.default_position_size_percent = trading.get("default_position_size_percent", 18)
        self.max_correlation = trading.get("max_correlation", 0.7)

    def _parse_execution_config(self):
        """Parse execution section from YAML."""
        execution = self._yaml_config.get("execution", {})

        self.max_slippage_bps = execution.get("max_slippage_bps", 20)
        self.order_timeout_seconds = execution.get("order_timeout_seconds", 30)
        self.max_retry_attempts = execution.get("max_retry_attempts", 3)
        self.retry_backoff_base = execution.get("retry_backoff_base", 2)
        self.rate_limit_weight_per_minute = execution.get("rate_limit_weight_per_minute", 1200)
        self.rate_limit_buffer = execution.get("rate_limit_buffer", 0.8)

    def _parse_strategy_configs(self):
        """Parse strategy configurations from YAML."""
        strategies = self._yaml_config.get("strategies", {})

        self.orderbook_imbalance = StrategyConfig(**strategies.get("orderbook_imbalance", {}))
        self.volume_profile = StrategyConfig(**strategies.get("volume_profile", {}))
        self.smart_momentum = StrategyConfig(**strategies.get("smart_momentum", {}))

    def _parse_monitoring_config(self):
        """Parse monitoring section from YAML."""
        monitoring = self._yaml_config.get("monitoring", {})

        self.dashboard_port = monitoring.get("dashboard_port", 8080)
        self.log_level = monitoring.get("log_level", "INFO")
        self.alert_on_loss_percent = monitoring.get("alert_on_loss_percent", 3)
        self.alert_on_win_percent = monitoring.get("alert_on_win_percent", 10)

    def _apply_deployment_phase(self):
        """Apply progressive deployment phase restrictions."""
        deployment = self._yaml_config.get("deployment", {})
        week_key = f"week_{self.deployment_week}"

        if week_key in deployment:
            phase = deployment[week_key]

            # Override capital and leverage based on deployment phase
            self.risk.active_capital = phase.get("capital", self.risk.active_capital)
            self.risk.default_leverage = phase.get("leverage", self.risk.default_leverage)

            # Enable only approved strategies for this phase
            approved_strategies = phase.get("strategies", [])
            if approved_strategies != ["all"]:
                # Disable strategies not in approved list
                if "orderbook_imbalance" not in approved_strategies:
                    self.orderbook_imbalance.enabled = False
                if "volume_profile" not in approved_strategies:
                    self.volume_profile.enabled = False
                if "smart_momentum" not in approved_strategies:
                    self.smart_momentum.enabled = False

            # AI learning control
            self.ai_enabled = phase.get("ai_enabled", False)

    def get_enabled_pairs(self) -> List[str]:
        """Get list of enabled trading pair symbols."""
        return [pair.symbol for pair in self.pairs if pair.enabled]

    def get_pair_config(self, symbol: str) -> Optional[TradingPairConfig]:
        """Get configuration for specific trading pair."""
        for pair in self.pairs:
            if pair.symbol == symbol:
                return pair
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            "enabled_pairs": self.get_enabled_pairs(),
            "max_concurrent_positions": self.max_concurrent_positions,
            "active_capital": self.risk.active_capital,
            "max_daily_loss": self.risk.max_daily_loss,
            "default_leverage": self.risk.default_leverage,
            "deployment_week": self.deployment_week,
            "strategies": {
                "orderbook_imbalance": self.orderbook_imbalance.enabled,
                "volume_profile": self.volume_profile.enabled,
                "smart_momentum": self.smart_momentum.enabled,
            }
        }


# Singleton instance
_config_instance: Optional[TradingConfig] = None


def get_config() -> TradingConfig:
    """
    Get singleton configuration instance.

    Returns:
        TradingConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TradingConfig()
    return _config_instance


def reload_config(config_path: Optional[Path] = None) -> TradingConfig:
    """
    Reload configuration from file.

    Args:
        config_path: Path to config file

    Returns:
        New TradingConfig instance
    """
    global _config_instance
    _config_instance = TradingConfig(config_path)
    return _config_instance
