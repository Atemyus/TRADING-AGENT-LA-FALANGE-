"""
OpenRouter Provider

Routes selected models through OpenRouter's OpenAI-compatible API.
"""

import json
import os
import re
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
from src.engines.ai.prompts.templates import (
    build_analysis_prompt,
    get_system_prompt,
)

OPENROUTER_MODELS = {
    "chatgpt-5.4": {
        "id": "openai/gpt-5.4",
        "display_name": "GPT-5.4",
        "provider": "OpenAI",
        "supports_vision": True,
    },
    "gemini-3.1-flash-lite": {
        "id": "google/gemini-3.1-flash-lite-preview",
        "display_name": "Gemini 3.1 Flash Lite",
        "provider": "Google",
        "supports_vision": True,
    },
}


class OpenRouterProvider(BaseAIProvider):
    """OpenRouter-backed provider for selected premium models."""

    def __init__(
        self,
        model_name: str = "chatgpt-5.4",
        api_key: str | None = None,
    ):
        key = api_key or os.environ.get("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", None)
        super().__init__(model_name, key)
        self._client: AsyncOpenAI | None = None
        self._model_info = OPENROUTER_MODELS.get(model_name, {
            "id": model_name,
            "display_name": model_name,
            "provider": "OpenRouter",
        })

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def supported_models(self) -> list[str]:
        return list(OPENROUTER_MODELS.keys())

    async def initialize(self) -> None:
        """Initialize OpenRouter client."""
        if self._client is None:
            base_url = os.environ.get("OPENROUTER_BASE_URL") or settings.OPENROUTER_BASE_URL
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base_url,
            )

    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        try:
            await self.initialize()
            response = await self._client.chat.completions.create(
                model=self._model_info["id"],
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response is not None
        except Exception:
            return False

    async def analyze(
        self,
        context: MarketContext,
        mode: str = "standard",
        trading_style: str = "intraday",
    ) -> AIAnalysis:
        """Analyze market context using OpenRouter."""
        await self.initialize()

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                mode=mode,
                trading_style=trading_style,
                session=context.market_session or "unknown",
            )

            max_tokens = 1000 if mode == "quick" else 2000 if mode == "standard" else 3000

            response = await self._client.chat.completions.create(
                model=self._model_info["id"],
                messages=[
                    {"role": "system", "content": get_system_prompt(mode)},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3 if mode == "quick" else 0.4,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            if not content:
                return self._create_error_response("Empty response from model")

            data = self._extract_json(content)
            if data is None:
                return self._create_error_response(f"Failed to parse JSON response: {content[:200]}")

            processing_time = int((time.time() - start_time) * 1000)
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost = self.calculate_cost(input_tokens, output_tokens)

            return AIAnalysis(
                provider_name=self._model_info["provider"],
                model_name=self._model_info["display_name"],
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

    def _extract_json(self, content: str) -> dict | None:
        """Extract JSON from an OpenRouter response."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{[^{}]*\"direction\"[^{}]*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{[\s\S]*?\"direction\"[\s\S]*?\}", content)
        if json_match:
            try:
                potential_json = json_match.group(0)
                brace_count = 0
                end_idx = 0
                for i, char in enumerate(potential_json):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                if end_idx > 0:
                    return json.loads(potential_json[:end_idx])
            except json.JSONDecodeError:
                pass

        return None
