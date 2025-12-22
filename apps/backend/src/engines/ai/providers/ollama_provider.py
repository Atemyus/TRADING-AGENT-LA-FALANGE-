"""
Ollama Provider

Local, FREE inference using Ollama.
Supports any model available in Ollama: Llama, Mistral, Qwen, DeepSeek, etc.
"""

import json
import time
from decimal import Decimal
from typing import List, Optional

import httpx

from src.core.config import settings
from src.engines.ai.base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from src.engines.ai.prompts.templates import build_analysis_prompt, get_system_prompt


class OllamaProvider(BaseAIProvider):
    """
    Ollama provider - LOCAL & FREE!

    Run any open-source model locally without API costs.

    Recommended models for trading analysis:
    - llama3.2:3b: Fast, good for quick analysis
    - llama3.1:8b: Better quality, still fast
    - llama3.1:70b: Best quality (needs powerful GPU)
    - qwen2.5:14b: Excellent reasoning
    - deepseek-r1:14b: Great for analysis tasks
    - mistral:7b: Good balance
    - mixtral:8x7b: MoE architecture, quality output
    """

    # No pricing - it's FREE!
    PRICING = {}

    # Default recommended models
    RECOMMENDED_MODELS = [
        "llama3.2:3b",
        "llama3.1:8b",
        "llama3.1:70b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "deepseek-r1:7b",
        "deepseek-r1:14b",
        "mistral:7b",
        "mixtral:8x7b",
        "gemma2:9b",
        "phi3:14b",
    ]

    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,  # Not used for Ollama
    ):
        super().__init__(model_name, api_key)
        self._base_url = base_url or getattr(settings, 'OLLAMA_BASE_URL', None) or "http://localhost:11434"
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supported_models(self) -> List[str]:
        return self.RECOMMENDED_MODELS

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.0  # FREE!

    @property
    def cost_per_1k_output_tokens(self) -> float:
        return 0.0  # FREE!

    async def initialize(self) -> None:
        """Initialize Ollama HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=120.0,  # Longer timeout for local inference
            )
            self._client = self._http_client  # For compatibility with base class

    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            await self.initialize()

            # Check if Ollama is running
            response = await self._http_client.get("/api/tags")
            if response.status_code != 200:
                return False

            # Check if model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if our model (or a close variant) is available
            if self.model_name in model_names:
                return True

            # Check without tag
            base_model = self.model_name.split(":")[0]
            for name in model_names:
                if name.startswith(base_model):
                    return True

            return False
        except Exception:
            return False

    async def list_available_models(self) -> List[str]:
        """List all models available in local Ollama installation."""
        try:
            await self.initialize()
            response = await self._http_client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]
            return []
        except Exception:
            return []

    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """Analyze market context using local Ollama model."""
        await self.initialize()

        if self._http_client is None:
            return self._create_error_response("Ollama client not initialized.")

        start_time = time.time()

        try:
            user_prompt = build_analysis_prompt(
                context_str=context.to_prompt_string(),
                trading_style="intraday",
                risk_tolerance="moderate",
                session=context.market_session or "unknown",
            )

            # Combine system and user prompt for Ollama
            full_prompt = f"""<|system|>
{get_system_prompt()}
<|user|>
{user_prompt}
<|assistant|>"""

            # Use chat API for better results
            response = await self._http_client.post(
                "/api/chat",
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 1000,
                    },
                },
            )

            if response.status_code != 200:
                return self._create_error_response(f"Ollama API error: {response.status_code}")

            result = response.json()
            content = result.get("message", {}).get("content", "")

            # Parse JSON from response
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            processing_time = int((time.time() - start_time) * 1000)

            # Ollama provides token counts in response
            eval_count = result.get("eval_count", 0)
            prompt_eval_count = result.get("prompt_eval_count", 0)

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
                tokens_used=prompt_eval_count + eval_count,
                cost_usd=0.0,  # FREE!
                raw_response=content,
            )

        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse JSON: {e}")
        except httpx.ConnectError:
            return self._create_error_response("Cannot connect to Ollama. Make sure it's running: `ollama serve`")
        except Exception as e:
            return self._create_error_response(str(e))

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
