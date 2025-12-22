"""
Google Gemini Provider

Supports Gemini Pro, Gemini Flash models.
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


class GoogleProvider(BaseAIProvider):
    """
    Google Gemini provider.

    Supported models:
    - gemini-pro: Best quality
    - gemini-1.5-flash: Fast and efficient
    - gemini-1.5-pro: Latest pro model
    """

    PRICING = {
        "gemini-pro": {"input": 0.00025, "output": 0.0005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-flash": {"input": 0.000075, "output": 0.0003},  # Alias
    }

    MODEL_ALIASES = {
        "gemini-flash": "gemini-1.5-flash",
        "gemini-pro": "gemini-1.5-pro",
    }

    def __init__(
        self,
        model_name: str = "gemini-flash",
        api_key: Optional[str] = None,
    ):
        resolved_model = self.MODEL_ALIASES.get(model_name, model_name)
        super().__init__(resolved_model, api_key)
        self._display_name = model_name

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def supported_models(self) -> List[str]:
        return ["gemini-pro", "gemini-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("input", 0.00025)

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return self.PRICING.get(self.model_name, {}).get("output", 0.0005)

    async def initialize(self) -> None:
        """Initialize Google Generative AI client."""
        try:
            import google.generativeai as genai
            api_key = self.api_key or getattr(settings, 'GOOGLE_API_KEY', None)
            if api_key:
                genai.configure(api_key=api_key)
                self._client = genai.GenerativeModel(self.model_name)
        except ImportError:
            pass

    async def health_check(self) -> bool:
        """Check if Google API is accessible."""
        try:
            await self.initialize()
            if self._client is None:
                return False
            response = await self._client.generate_content_async("test")
            return response is not None
        except Exception:
            return False

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """Analyze market context using Gemini."""
        await self.initialize()

        if self._client is None:
            return self._create_error_response("Google client not initialized. Check API key.")

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            full_prompt = f"{get_system_prompt()}\n\n{user_prompt}"

            response = await self._client.generate_content_async(
                full_prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 1000,
                    "response_mime_type": "application/json",
                },
            )

            content = response.text

            # Parse JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            processing_time = int((time.time() - start_time) * 1000)

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
                raw_response=content,
            )

        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse JSON: {e}")
        except Exception as e:
            return self._create_error_response(str(e))
