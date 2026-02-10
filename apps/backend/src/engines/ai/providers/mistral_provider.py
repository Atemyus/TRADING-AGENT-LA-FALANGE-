"""
Mistral Provider

Supports Mistral Large, Mistral Medium, Mistral Small, Codestral models.
"""

import json
import time
from decimal import Decimal

from src.core.config import settings
from src.engines.ai.base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from src.engines.ai.prompts.templates import build_analysis_prompt, get_system_prompt


class MistralProvider(BaseAIProvider):
    """
    Mistral AI provider.

    Supported models:
    - mistral-large-latest: Best quality, 128k context
    - mistral-medium-latest: Good balance
    - mistral-small-latest: Fast and efficient
    - codestral-latest: Optimized for code/structured output
    """

    PRICING = {
        "mistral-large-latest": {"input": 0.002, "output": 0.006},
        "mistral-medium-latest": {"input": 0.0027, "output": 0.0081},
        "mistral-small-latest": {"input": 0.0002, "output": 0.0006},
        "codestral-latest": {"input": 0.0003, "output": 0.0009},
        "mistral-large": {"input": 0.002, "output": 0.006},  # Alias
        "mistral-small": {"input": 0.0002, "output": 0.0006},  # Alias
    }

    MODEL_ALIASES = {
        "mistral-large": "mistral-large-latest",
        "mistral-medium": "mistral-medium-latest",
        "mistral-small": "mistral-small-latest",
        "codestral": "codestral-latest",
    }

    def __init__(
        self,
        model_name: str = "mistral-large",
        api_key: str | None = None,
    ):
        resolved_model = self.MODEL_ALIASES.get(model_name, model_name)
        super().__init__(resolved_model, api_key)
        self._display_name = model_name

    @property
    def provider_name(self) -> str:
        return "mistral"

    @property
    def supported_models(self) -> list[str]:
        return [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "codestral-latest",
            "mistral-large",
            "mistral-medium",
            "mistral-small",
            "codestral",
        ]

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("input", 0.002)

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("output", 0.006)

    async def initialize(self) -> None:
        """Initialize Mistral client."""
        try:
            from mistralai import Mistral
            api_key = self.api_key or getattr(settings, 'MISTRAL_API_KEY', None)
            if api_key:
                self._client = Mistral(api_key=api_key)
        except ImportError:
            pass

    async def health_check(self) -> bool:
        """Check if Mistral API is accessible."""
        try:
            await self.initialize()
            if self._client is None:
                return False
            response = await self._client.chat.complete_async(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response is not None
        except Exception:
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """Analyze market context using Mistral."""
        await self.initialize()

        if self._client is None:
            return self._create_error_response("Mistral client not initialized. Check API key.")

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            response = await self._client.chat.complete_async(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            processing_time = int((time.time() - start_time) * 1000)
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(input_tokens, output_tokens)

            return AIAnalysis(
                provider_name=self.provider_name,
                model_name=self._display_name,
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
            return self._create_error_response(f"Failed to parse JSON: {e}")
        except Exception as e:
            return self._create_error_response(str(e))
