"""
OpenAI Provider

Supports GPT-4o, GPT-4o-mini, GPT-4-turbo models.
"""

import json
import time
from decimal import Decimal

from openai import AsyncOpenAI

from src.core.config import settings
from src.engines.ai.base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from src.engines.ai.prompts.templates import build_analysis_prompt, get_system_prompt


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI GPT provider.

    Supported models:
    - gpt-4o: Best quality, moderate speed
    - gpt-4o-mini: Fast, cost-effective
    - gpt-4-turbo: Previous generation, still good
    """

    # Model pricing (per 1K tokens) as of Dec 2024
    PRICING = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
    }

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: str | None = None,
    ):
        super().__init__(model_name, api_key or settings.OPENAI_API_KEY)
        self._client: AsyncOpenAI | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4"]

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("input", 0.0025)

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("output", 0.01)

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            await self.initialize()
            # Simple test call
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response is not None
        except Exception:
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """
        Analyze market context using OpenAI GPT.

        Args:
            context: Market context with all relevant data

        Returns:
            AIAnalysis with trading recommendation
        """
        await self.initialize()

        start_time = time.time()

        try:
            # Build prompt
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            # Call OpenAI
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1000,
            )

            # Parse response
            content = response.choices[0].message.content
            data = json.loads(content)

            # Calculate metrics
            processing_time = int((time.time() - start_time) * 1000)
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(input_tokens, output_tokens)

            return AIAnalysis(
                provider_name=self.provider_name,
                model_name=self.model_name,
                direction=TradeDirection(data.get("direction", "HOLD")),
                confidence=float(data.get("confidence", 0)),
                entry_price=Decimal(str(data["entry_price"])) if data.get("entry_price") else None,
                stop_loss=Decimal(str(data["stop_loss"])) if data.get("stop_loss") else None,
                take_profit=Decimal(str(data["take_profit"])) if data.get("take_profit") else None,
                risk_reward_ratio=float(data.get("risk_reward_ratio", 0)) if data.get("risk_reward_ratio") else None,
                reasoning=data.get("reasoning", ""),
                key_factors=data.get("key_factors", []),
                risks=data.get("risks", []),
                suggested_timeframe=data.get("suggested_timeframe", ""),
                urgency=data.get("urgency", "normal"),
                processing_time_ms=processing_time,
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                raw_response=content,
            )

        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse JSON response: {e}")
        except Exception as e:
            return self._create_error_response(str(e))
