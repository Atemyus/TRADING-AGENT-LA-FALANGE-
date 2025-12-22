"""
Anthropic Provider

Supports Claude Sonnet, Claude Haiku, Claude Opus models.
"""

import json
import time
from decimal import Decimal
from typing import List, Optional

from src.core.config import settings
from src.engines.ai.base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from src.engines.ai.prompts.templates import build_analysis_prompt, get_system_prompt


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude provider.

    Supported models:
    - claude-3-5-sonnet-20241022: Best balance of quality/speed
    - claude-3-5-haiku-20241022: Fastest, most cost-effective
    - claude-3-opus-20240229: Highest quality, slower
    """

    # Model pricing (per 1K tokens)
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-sonnet": {"input": 0.003, "output": 0.015},  # Alias
        "claude-haiku": {"input": 0.0008, "output": 0.004},  # Alias
    }

    # Model aliases
    MODEL_ALIASES = {
        "claude-sonnet": "claude-3-5-sonnet-20241022",
        "claude-haiku": "claude-3-5-haiku-20241022",
        "claude-opus": "claude-3-opus-20240229",
    }

    def __init__(
        self,
        model_name: str = "claude-sonnet",
        api_key: Optional[str] = None,
    ):
        # Resolve alias
        resolved_model = self.MODEL_ALIASES.get(model_name, model_name)
        super().__init__(resolved_model, api_key)
        self._display_name = model_name

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> List[str]:
        return list(self.MODEL_ALIASES.keys()) + list(self.MODEL_ALIASES.values())

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING.get(self.model_name, self.PRICING.get(self._display_name, {})).get("input", 0.003)

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING.get(self.model_name, self.PRICING.get(self._display_name, {})).get("output", 0.015)

    async def initialize(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic
            if self._client is None:
                api_key = self.api_key or getattr(settings, 'ANTHROPIC_API_KEY', None)
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            pass  # anthropic package not installed

    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        try:
            await self.initialize()
            if self._client is None:
                return False
            response = await self._client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return response is not None
        except Exception:
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """Analyze market context using Claude."""
        await self.initialize()

        if self._client is None:
            return self._create_error_response("Anthropic client not initialized. Check API key.")

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            response = await self._client.messages.create(
                model=self.model_name,
                max_tokens=1000,
                system=get_system_prompt(),
                messages=[{"role": "user", "content": user_prompt}],
            )

            content = response.content[0].text

            # Extract JSON from response
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            processing_time = int((time.time() - start_time) * 1000)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
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
