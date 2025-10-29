"""
TAAPI.io client for technical indicators.

Based on Gajesh2007/ai-trading-agent proven implementation.
TAAPI provides 100+ technical indicators with RESTful API.
"""

import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from src.core.logger import get_logger, LogCategory


@dataclass
class TechnicalIndicators:
    """Technical indicators from TAAPI."""
    symbol: str
    timestamp: datetime

    # Trend Indicators
    rsi: Optional[float] = None  # Relative Strength Index
    macd: Optional[float] = None  # MACD
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

    # Moving Averages
    sma_20: Optional[float] = None  # Simple Moving Average 20
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None  # Exponential Moving Average
    ema_26: Optional[float] = None

    # Momentum
    stoch_k: Optional[float] = None  # Stochastic
    stoch_d: Optional[float] = None
    cci: Optional[float] = None  # Commodity Channel Index

    # Volatility
    atr: Optional[float] = None  # Average True Range
    bbands_upper: Optional[float] = None  # Bollinger Bands
    bbands_middle: Optional[float] = None
    bbands_lower: Optional[float] = None

    # Volume
    obv: Optional[float] = None  # On Balance Volume
    adx: Optional[float] = None  # Average Directional Index

    # Additional
    vwap: Optional[float] = None  # Volume Weighted Average Price


class TaapiClient:
    """
    Client for TAAPI.io technical indicators API.

    Based on proven Gajesh2007/ai-trading-agent implementation.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.taapi.io"):
        """
        Initialize TAAPI client.

        Args:
            api_key: TAAPI.io API key
            base_url: TAAPI API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger("taapi_client")

    async def init(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        indicator: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make request to TAAPI API.

        Args:
            indicator: Indicator name (rsi, macd, etc.)
            params: Request parameters

        Returns:
            Response data
        """
        if not self.session:
            await self.init()

        # Add API key to params
        params['secret'] = self.api_key

        url = f"{self.base_url}/{indicator}"

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            self.logger.error(
                f"TAAPI API error for {indicator}: {e}",
                category=LogCategory.MARKET_DATA,
                indicator=indicator,
                error=str(e)
            )
            return {}

    async def get_indicators(
        self,
        symbol: str,
        exchange: str = "binance",
        interval: str = "1h"
    ) -> TechnicalIndicators:
        """
        Get comprehensive technical indicators for symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            exchange: Exchange name
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)

        Returns:
            TechnicalIndicators object
        """
        # Convert Hyperliquid symbols to TAAPI format
        taapi_symbol = self._convert_symbol(symbol)

        base_params = {
            'exchange': exchange,
            'symbol': taapi_symbol,
            'interval': interval
        }

        indicators = TechnicalIndicators(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc)
        )

        # Fetch all indicators in parallel
        tasks = {
            'rsi': self._make_request('rsi', base_params),
            'macd': self._make_request('macd', base_params),
            'sma': self._make_request('sma', {**base_params, 'period': 20}),
            'ema': self._make_request('ema', {**base_params, 'period': 12}),
            'stoch': self._make_request('stoch', base_params),
            'atr': self._make_request('atr', base_params),
            'bbands': self._make_request('bbands', base_params),
            'adx': self._make_request('adx', base_params),
            'vwap': self._make_request('vwap', base_params),
        }

        try:
            results = {}
            import asyncio
            for name, task in tasks.items():
                results[name] = await task

            # Parse results
            if 'value' in results.get('rsi', {}):
                indicators.rsi = float(results['rsi']['value'])

            if 'valueMACDSignal' in results.get('macd', {}):
                indicators.macd = float(results['macd']['valueMACD'])
                indicators.macd_signal = float(results['macd']['valueMACDSignal'])
                indicators.macd_histogram = float(results['macd']['valueMACDHist'])

            if 'value' in results.get('sma', {}):
                indicators.sma_20 = float(results['sma']['value'])

            if 'value' in results.get('ema', {}):
                indicators.ema_12 = float(results['ema']['value'])

            if 'valueK' in results.get('stoch', {}):
                indicators.stoch_k = float(results['stoch']['valueK'])
                indicators.stoch_d = float(results['stoch']['valueD'])

            if 'value' in results.get('atr', {}):
                indicators.atr = float(results['atr']['value'])

            if 'valueLowerBand' in results.get('bbands', {}):
                indicators.bbands_upper = float(results['bbands']['valueUpperBand'])
                indicators.bbands_middle = float(results['bbands']['valueMiddleBand'])
                indicators.bbands_lower = float(results['bbands']['valueLowerBand'])

            if 'value' in results.get('adx', {}):
                indicators.adx = float(results['adx']['value'])

            if 'value' in results.get('vwap', {}):
                indicators.vwap = float(results['vwap']['value'])

            self.logger.debug(
                f"Fetched technical indicators for {symbol}",
                category=LogCategory.MARKET_DATA,
                symbol=symbol,
                rsi=indicators.rsi,
                macd=indicators.macd
            )

        except Exception as e:
            self.logger.error(
                f"Error parsing TAAPI indicators: {e}",
                category=LogCategory.MARKET_DATA,
                error=str(e)
            )

        return indicators

    def _convert_symbol(self, symbol: str) -> str:
        """
        Convert Hyperliquid symbol to TAAPI format.

        Args:
            symbol: Hyperliquid symbol (e.g., "SOL")

        Returns:
            TAAPI symbol (e.g., "SOL/USDT")
        """
        # Map common symbols
        if symbol == "SOL":
            return "SOL/USDT"
        elif symbol == "HYPE":
            return "HYPE/USDT"
        elif symbol == "DOGE":
            return "DOGE/USDT"
        elif symbol == "BTC":
            return "BTC/USDT"
        elif symbol == "ETH":
            return "ETH/USDT"
        else:
            return f"{symbol}/USDT"

    def analyze_indicators(self, indicators: TechnicalIndicators) -> Dict[str, Any]:
        """
        Analyze indicators and provide trading signals.

        Args:
            indicators: Technical indicators

        Returns:
            Dict with analysis results
        """
        signals = {
            'bullish': 0,
            'bearish': 0,
            'neutral': 0,
            'strength': 0.0,
            'reasons': []
        }

        # RSI Analysis
        if indicators.rsi:
            if indicators.rsi < 30:
                signals['bullish'] += 1
                signals['reasons'].append(f"RSI oversold: {indicators.rsi:.1f}")
            elif indicators.rsi > 70:
                signals['bearish'] += 1
                signals['reasons'].append(f"RSI overbought: {indicators.rsi:.1f}")
            else:
                signals['neutral'] += 1

        # MACD Analysis
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                signals['bullish'] += 1
                signals['reasons'].append("MACD bullish crossover")
            else:
                signals['bearish'] += 1
                signals['reasons'].append("MACD bearish crossover")

        # Stochastic Analysis
        if indicators.stoch_k and indicators.stoch_d:
            if indicators.stoch_k < 20 and indicators.stoch_k > indicators.stoch_d:
                signals['bullish'] += 1
                signals['reasons'].append("Stoch bullish (oversold + crossing up)")
            elif indicators.stoch_k > 80 and indicators.stoch_k < indicators.stoch_d:
                signals['bearish'] += 1
                signals['reasons'].append("Stoch bearish (overbought + crossing down)")

        # Bollinger Bands Analysis
        if all([indicators.bbands_upper, indicators.bbands_middle, indicators.bbands_lower]):
            # Need current price to compare
            # Will be added when integrated with market data
            pass

        # ADX Trend Strength
        if indicators.adx:
            if indicators.adx > 25:
                signals['reasons'].append(f"Strong trend (ADX: {indicators.adx:.1f})")
            elif indicators.adx < 20:
                signals['reasons'].append(f"Weak trend (ADX: {indicators.adx:.1f})")

        # Calculate overall strength
        total_signals = signals['bullish'] + signals['bearish'] + signals['neutral']
        if total_signals > 0:
            if signals['bullish'] > signals['bearish']:
                signals['strength'] = signals['bullish'] / total_signals
                signals['direction'] = 'BULLISH'
            elif signals['bearish'] > signals['bullish']:
                signals['strength'] = signals['bearish'] / total_signals
                signals['direction'] = 'BEARISH'
            else:
                signals['strength'] = 0.0
                signals['direction'] = 'NEUTRAL'
        else:
            signals['direction'] = 'NEUTRAL'

        return signals
