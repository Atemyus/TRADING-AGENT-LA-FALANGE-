"""
Groq Provider

Ultra-fast inference using Groq's LPU technology.
Supports Llama 3.3, Mixtral models.
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


class GroqProvider(BaseAIProvider):
    """
    Groq provider - ULTRA FAST inference!

    Groq's LPU (Language Processing Unit) provides 10x faster inference
    than traditional GPU-based solutions.

    Supported models:
    - llama-3.3-70b-versatile: Best quality, still very fast
    - llama-3.1-8b-instant: Fastest, good for simple tasks
    - mixtral-8x7b-32768: Good balance
    """

    PRICING = {
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
        "llama3-70b": {"input": 0.00059, "output": 0.00079},  # Alias
    }

    MODEL_ALIASES = {
        "llama3-70b": "llama-3.3-70b-versatile",
        "llama3-8b": "llama-3.1-8b-instant",
    }

    def __init__(
        self,
        model_name: str = "llama3-70b",
        api_key: str | None = None,
    ):
        resolved_model = self.MODEL_ALIASES.get(model_name, model_name)
        super().__init__(resolved_model, api_key)
        self._display_name = model_name

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def supported_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "llama3-70b",
            "llama3-8b",
        ]

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("input", 0.00059)

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("output", 0.00079)

    async def initialize(self) -> None:
        """Initialize Groq client."""
        try:
            from groq import AsyncGroq
            api_key = self.api_key or getattr(settings, 'GROQ_API_KEY', None)
            if api_key:
                self._client = AsyncGroq(api_key=api_key)
        except ImportError:
            pass

    async def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            await self.initialize()
            if self._client is None:
                return False
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response is not None
        except Exception:
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """Analyze market context using Groq (ultra-fast!)."""
        await self.initialize()

        if self._client is None:
            return self._create_error_response("Groq client not initialized. Check API key.")

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            response = await self._client.chat.completions.create(
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
