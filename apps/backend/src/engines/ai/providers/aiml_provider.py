"""
AIML API Provider

Multi-model gateway at api.aimlapi.com/v1
Uses a single API key to access multiple AI models.

Supported models (exact AIML API model IDs):
- ChatGPT 5.2 → openai/gpt-5-2-chat-latest
- Gemini 3 Pro → google/gemini-3-pro-preview
- DeepSeek V3.2 → deepseek/deepseek-non-thinking-v3.2-exp
- Grok 4.1 Fast → x-ai/grok-4-1-fast-reasoning
- Qwen Max → qwen-max
- GLM 4.7 → zhipu/glm-4.7
"""

import json
import os
import re
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


# AIML API model mappings - EXACT model IDs from AIML API documentation
AIML_MODELS = {
    "chatgpt-5.2": {
        "id": "openai/gpt-5-2-chat-latest",
        "display_name": "ChatGPT 5.2",
        "provider": "OpenAI",
    },
    "gemini-3-pro": {
        "id": "google/gemini-3-pro-preview",
        "display_name": "Gemini 3 Pro",
        "provider": "Google",
    },
    "deepseek-v3.2": {
        "id": "deepseek/deepseek-non-thinking-v3.2-exp",
        "display_name": "DeepSeek V3.2",
        "provider": "DeepSeek",
    },
    "grok-4.1-fast": {
        "id": "x-ai/grok-4-1-fast-reasoning",
        "display_name": "Grok 4.1 Fast",
        "provider": "xAI",
    },
    "qwen-max": {
        "id": "qwen-max",
        "display_name": "Qwen Max",
        "provider": "Alibaba",
    },
    "glm-4.7": {
        "id": "zhipu/glm-4.7",
        "display_name": "GLM 4.7",
        "provider": "Zhipu",
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

            # Call AIML API - don't use response_format as not all models support it
            response = await self._client.chat.completions.create(
                model=self._model_info["id"],
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=2000,  # Increased for detailed reasoning
            )

            # Parse response - handle potential non-JSON content
            content = response.choices[0].message.content
            if not content:
                return self._create_error_response("Empty response from model")

            # Try to extract JSON from response
            data = self._extract_json(content)
            if data is None:
                return self._create_error_response(f"Failed to parse JSON response: {content[:200]}")

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

    def _extract_json(self, content: str) -> Optional[dict]:
        """
        Extract JSON from response content.
        Handles cases where model returns JSON wrapped in markdown or extra text.
        """
        # First try direct parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r'\{[^{}]*"direction"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try to find JSON that spans multiple lines
        json_match = re.search(r'\{[\s\S]*?"direction"[\s\S]*?\}', content)
        if json_match:
            try:
                # Clean up the match
                potential_json = json_match.group(0)
                # Find matching closing brace
                brace_count = 0
                end_idx = 0
                for i, char in enumerate(potential_json):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                if end_idx > 0:
                    return json.loads(potential_json[:end_idx])
            except json.JSONDecodeError:
                pass

        return None
