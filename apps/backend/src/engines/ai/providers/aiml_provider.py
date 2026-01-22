"""
AIML API Provider

Multi-model gateway at api.aimlapi.com/v1
Uses a single API key to access multiple AI models.

Supported models (real AIML API model IDs):
- GPT-4o (OpenAI)
- GPT-4o-mini (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- Gemini 1.5 Pro (Google)
- DeepSeek Chat (DeepSeek)
- Llama 3.1 70B (Meta via AIML)
"""

import json
import os
import time
from decimal import Decimal
from typing import List, Optional

from openai import AsyncOpenAI

from src.core.config import settings
from src.engines.ai.base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from src.engines.ai.prompts.templates import build_analysis_prompt, get_system_prompt


# AIML API model mappings - REAL model IDs
AIML_MODELS = {
    "gpt-4o": {
        "id": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "OpenAI",
    },
    "gpt-4o-mini": {
        "id": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "OpenAI",
    },
    "claude-3-5-sonnet": {
        "id": "anthropic/claude-3.5-sonnet",
        "display_name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
    },
    "gemini-1.5-pro": {
        "id": "google/gemini-pro-1.5",
        "display_name": "Gemini 1.5 Pro",
        "provider": "Google",
    },
    "deepseek-chat": {
        "id": "deepseek/deepseek-chat",
        "display_name": "DeepSeek Chat",
        "provider": "DeepSeek",
    },
    "llama-3.1-70b": {
        "id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "display_name": "Llama 3.1 70B",
        "provider": "Meta",
    },
}


class AIMLProvider(BaseAIProvider):
    """
    AIML API Provider - Multi-model gateway.

    Uses api.aimlapi.com/v1 with OpenAI-compatible API format.
    Single API key provides access to multiple AI models.
    """

    # Flat rate pricing for AIML API (approximate)
    PRICING = {
        "input": 0.001,   # $0.001 per 1K input tokens
        "output": 0.002,  # $0.002 per 1K output tokens
    }

    def __init__(
        self,
        model_name: str = "chatgpt-5.2",
        api_key: Optional[str] = None,
    ):
        # Get API key: explicit > environment > settings
        key = api_key or os.environ.get('AIML_API_KEY') or getattr(settings, 'AIML_API_KEY', None)
        super().__init__(model_name, key)
        self._client: Optional[AsyncOpenAI] = None

        # Get model info
        self._model_info = AIML_MODELS.get(model_name, {
            "id": model_name,
            "display_name": model_name,
            "provider": "AIML",
        })

    @property
    def provider_name(self) -> str:
        return f"aiml_{self._model_info['provider'].lower()}"

    @property
    def supported_models(self) -> List[str]:
        return list(AIML_MODELS.keys())

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING["input"]

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING["output"]

    async def initialize(self) -> None:
        """Initialize AIML API client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.aimlapi.com/v1",
            )

    async def health_check(self) -> bool:
        """Check if AIML API is accessible."""
        try:
            await self.initialize()
            response = await self._client.chat.completions.create(
                model=self._model_info["id"],
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return response is not None
        except Exception as e:
            print(f"AIML health check failed for {self.model_name}: {e}")
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """
        Analyze market context using AIML API.

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

            # Call AIML API
            response = await self._client.chat.completions.create(
                model=self._model_info["id"],
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000,
            )

            # Parse response
            content = response.choices[0].message.content
            data = json.loads(content)

            # Calculate metrics
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
