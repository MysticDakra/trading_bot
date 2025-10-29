"""
OpenRouter client for multi-LLM support.

Based on Gajesh2007/ai-trading-agent implementation.
Supports: GPT-5, DeepSeek, Grok, Claude, and more.
"""

import aiohttp
from typing import Dict, List, Optional, Any
from enum import Enum
from src.core.logger import get_logger, LogCategory


class LLMModel(str, Enum):
    """Supported LLM models via OpenRouter."""
    # OpenAI
    GPT_5_PRO = "openai/gpt-5-pro"
    GPT_4O = "openai/gpt-4o"
    O1_PREVIEW = "openai/o1-preview"

    # DeepSeek
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"
    DEEPSEEK_R1 = "deepseek/deepseek-r1"
    DEEPSEEK_CODER = "deepseek/deepseek-coder"

    # Anthropic Claude
    CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4.5"
    CLAUDE_OPUS_4 = "anthropic/claude-opus-4"

    # xAI Grok
    GROK_4 = "x-ai/grok-4"
    GROK_BETA = "x-ai/grok-beta"

    # Google Gemini
    GEMINI_2_5_PRO = "google/gemini-2.5-pro"

    # Qwen
    QWEN_3_MAX = "qwen/qwen-3-max"


class OpenRouterClient:
    """
    Client for OpenRouter API - access multiple LLMs with single API.

    Based on Gajesh2007/ai-trading-agent proven implementation.
    """

    def __init__(
        self,
        api_key: str,
        default_model: LLMModel = LLMModel.DEEPSEEK_CHAT,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            default_model: Default LLM model to use
            base_url: OpenRouter API base URL
        """
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = base_url

        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger("openrouter_client")

    async def init(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/hyperliquid-trader",
                "X-Title": "Hyperliquid Trading System"
            },
            timeout=aiohttp.ClientTimeout(total=120)  # 2 min for deep thinking models
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[LLMModel] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Create chat completion via OpenRouter.

        Args:
            messages: List of message dicts with role and content
            model: LLM model to use (defaults to default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional function calling tools

        Returns:
            Response dict with content and metadata
        """
        if not self.session:
            await self.init()

        model_str = (model or self.default_model).value

        payload = {
            "model": model_str,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            payload["tools"] = tools

        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Extract response
                content = data["choices"][0]["message"]["content"]
                tool_calls = data["choices"][0]["message"].get("tool_calls", [])

                # Log usage
                usage = data.get("usage", {})
                self.logger.debug(
                    f"OpenRouter API call: {model_str}",
                    category=LogCategory.AI,
                    model=model_str,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0)
                )

                return {
                    "content": content,
                    "tool_calls": tool_calls,
                    "model": data.get("model"),
                    "usage": usage
                }

        except aiohttp.ClientError as e:
            self.logger.error(
                f"OpenRouter API error: {e}",
                category=LogCategory.AI,
                model=model_str,
                error=str(e)
            )
            raise

    async def analyze_trade(
        self,
        symbol: str,
        current_price: float,
        technical_data: Dict[str, Any],
        nansen_data: Optional[Dict[str, Any]] = None,
        order_book_data: Optional[Dict[str, Any]] = None,
        model: Optional[LLMModel] = None
    ) -> Dict[str, Any]:
        """
        Analyze trade opportunity using specified LLM.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            technical_data: Technical indicators from TAAPI
            nansen_data: Nansen smart money data
            order_book_data: Order book imbalance data
            model: LLM model to use

        Returns:
            Trading decision dict
        """
        # Build comprehensive analysis prompt
        prompt = self._build_analysis_prompt(
            symbol=symbol,
            current_price=current_price,
            technical_data=technical_data,
            nansen_data=nansen_data,
            order_book_data=order_book_data
        )

        messages = [
            {
                "role": "system",
                "content": """You are an elite quantitative trading analyst.

Analyze the provided market data and provide a trading recommendation in JSON format:

{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation",
    "entry_price": number,
    "stop_loss": number,
    "take_profit": number,
    "risk_reward_ratio": number
}

Only recommend BUY/SELL if confidence > 0.7 and risk/reward > 3.0"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = await self.chat_completion(
                messages=messages,
                model=model,
                temperature=0.3  # Low for consistency
            )

            # Parse JSON response
            import json
            content = response["content"]

            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]

            decision = json.loads(json_str)
            decision['model_used'] = response.get('model')

            return decision

        except Exception as e:
            self.logger.error(
                f"Error in trade analysis: {e}",
                category=LogCategory.AI,
                error=str(e)
            )

            return {
                "action": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error in analysis: {e}"
            }

    def _build_analysis_prompt(
        self,
        symbol: str,
        current_price: float,
        technical_data: Dict[str, Any],
        nansen_data: Optional[Dict[str, Any]],
        order_book_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build comprehensive analysis prompt."""
        prompt_parts = [
            f"# Trading Analysis for {symbol}",
            f"Current Price: ${current_price:.4f}",
            "",
            "## Technical Indicators (TAAPI)"
        ]

        # Add technical indicators
        if technical_data:
            for key, value in technical_data.items():
                if value is not None:
                    prompt_parts.append(f"- {key}: {value}")

        # Add Nansen data
        if nansen_data:
            prompt_parts.extend([
                "",
                "## Nansen Smart Money Analysis",
                f"- Action: {nansen_data.get('action', 'UNKNOWN')}",
                f"- Confidence: {nansen_data.get('confidence', 0):.2f}",
                f"- Score: {nansen_data.get('score', 0):.2f}"
            ])

        # Add order book data
        if order_book_data:
            prompt_parts.extend([
                "",
                "## Order Book Analysis",
                f"- Imbalance: {order_book_data.get('imbalance', 0):.2f}",
                f"- Spread (bps): {order_book_data.get('spread_bps', 0):.1f}"
            ])

        prompt_parts.extend([
            "",
            "## Your Task",
            "Analyze all data and provide a trading recommendation.",
            "Focus on high-probability setups with excellent risk/reward ratios.",
            "Provide your analysis in the JSON format specified."
        ])

        return "\n".join(prompt_parts)

    async def compare_models(
        self,
        symbol: str,
        current_price: float,
        technical_data: Dict[str, Any],
        models: List[LLMModel]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get recommendations from multiple models for comparison.

        Args:
            symbol: Trading pair
            current_price: Current price
            technical_data: Technical indicators
            models: List of models to compare

        Returns:
            Dict mapping model name to decision
        """
        results = {}

        for model in models:
            try:
                decision = await self.analyze_trade(
                    symbol=symbol,
                    current_price=current_price,
                    technical_data=technical_data,
                    model=model
                )

                results[model.value] = decision

                self.logger.info(
                    f"{model.value}: {decision['action']} (confidence: {decision['confidence']:.2f})",
                    category=LogCategory.AI
                )

            except Exception as e:
                self.logger.error(
                    f"Error with {model.value}: {e}",
                    category=LogCategory.AI
                )

        return results

    def get_consensus(self, model_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get consensus recommendation from multiple models.

        Args:
            model_results: Results from multiple models

        Returns:
            Consensus decision
        """
        if not model_results:
            return {"action": "HOLD", "confidence": 0.0, "reasoning": "No model results"}

        # Count votes
        buy_votes = sum(1 for r in model_results.values() if r.get('action') == 'BUY')
        sell_votes = sum(1 for r in model_results.values() if r.get('action') == 'SELL')
        hold_votes = sum(1 for r in model_results.values() if r.get('action') == 'HOLD')

        total_votes = len(model_results)

        # Calculate average confidence
        confidences = [r.get('confidence', 0) for r in model_results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Determine consensus
        if buy_votes > sell_votes and buy_votes > hold_votes:
            action = "BUY"
            consensus_strength = buy_votes / total_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            action = "SELL"
            consensus_strength = sell_votes / total_votes
        else:
            action = "HOLD"
            consensus_strength = hold_votes / total_votes

        return {
            "action": action,
            "confidence": avg_confidence * consensus_strength,
            "consensus_strength": consensus_strength,
            "votes": {
                "BUY": buy_votes,
                "SELL": sell_votes,
                "HOLD": hold_votes
            },
            "model_count": total_votes,
            "reasoning": f"{action} consensus from {total_votes} models"
        }
