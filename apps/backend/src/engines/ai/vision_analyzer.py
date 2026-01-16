"""
Vision Analyzer - Multi-AI visual chart analysis.

Uses vision-capable models (GPT-4V, Claude Vision, Gemini Vision) to analyze
candlestick charts and identify patterns, trends, and trading opportunities.
"""

import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import httpx

from src.core.config import settings


class VisionModel(str, Enum):
    """Available vision-capable AI models."""
    GPT4_VISION = "gpt-4o"
    CLAUDE_VISION = "claude-sonnet-4-20250514"
    GEMINI_VISION = "gemini-1.5-flash"


@dataclass
class VisionAnalysisResult:
    """Result from a single vision AI analysis."""
    model: str
    direction: str  # LONG, SHORT, HOLD
    confidence: float  # 0-100
    entry_zone: Optional[Dict[str, float]] = None  # {"min": x, "max": y}
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    risk_reward: Optional[float] = None
    patterns_detected: Optional[List[str]] = None
    trend_analysis: Optional[Dict[str, str]] = None  # per timeframe
    reasoning: Optional[str] = None
    raw_response: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class VisionAnalyzer:
    """
    Analyzes chart images using multiple vision-capable AI models.
    """

    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY
        self.anthropic_key = settings.ANTHROPIC_API_KEY
        self.google_key = settings.GOOGLE_API_KEY
        self.timeout = 60.0

    async def analyze_with_gpt4_vision(
        self,
        images_base64: Dict[str, str],
        prompt: str,
    ) -> VisionAnalysisResult:
        """Analyze charts using GPT-4 Vision."""
        if not self.openai_key:
            return VisionAnalysisResult(
                model=VisionModel.GPT4_VISION,
                direction="HOLD",
                confidence=0,
                error="OpenAI API key not configured"
            )

        start_time = datetime.now()

        try:
            # Build content with images
            content = []
            for timeframe, image_b64 in images_base64.items():
                content.append({
                    "type": "text",
                    "text": f"Chart for {timeframe} timeframe:"
                })
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "high"
                    }
                })

            content.append({"type": "text", "text": prompt})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": VisionModel.GPT4_VISION,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert technical analyst specializing in forex and CFD trading. Analyze charts precisely and provide actionable trading recommendations."
                            },
                            {
                                "role": "user",
                                "content": content
                            }
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.3
                    }
                )
                response.raise_for_status()
                data = response.json()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            raw_text = data["choices"][0]["message"]["content"]

            return self._parse_analysis_response(
                raw_text=raw_text,
                model=VisionModel.GPT4_VISION,
                latency_ms=latency
            )

        except Exception as e:
            return VisionAnalysisResult(
                model=VisionModel.GPT4_VISION,
                direction="HOLD",
                confidence=0,
                error=str(e)
            )

    async def analyze_with_claude_vision(
        self,
        images_base64: Dict[str, str],
        prompt: str,
    ) -> VisionAnalysisResult:
        """Analyze charts using Claude Vision."""
        if not self.anthropic_key:
            return VisionAnalysisResult(
                model=VisionModel.CLAUDE_VISION,
                direction="HOLD",
                confidence=0,
                error="Anthropic API key not configured"
            )

        start_time = datetime.now()

        try:
            # Build content with images
            content = []
            for timeframe, image_b64 in images_base64.items():
                content.append({
                    "type": "text",
                    "text": f"Chart for {timeframe} timeframe:"
                })
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64
                    }
                })

            content.append({"type": "text", "text": prompt})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": VisionModel.CLAUDE_VISION,
                        "max_tokens": 2000,
                        "system": "You are an expert technical analyst specializing in forex and CFD trading. Analyze charts precisely and provide actionable trading recommendations.",
                        "messages": [
                            {
                                "role": "user",
                                "content": content
                            }
                        ]
                    }
                )
                response.raise_for_status()
                data = response.json()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            raw_text = data["content"][0]["text"]

            return self._parse_analysis_response(
                raw_text=raw_text,
                model=VisionModel.CLAUDE_VISION,
                latency_ms=latency
            )

        except Exception as e:
            return VisionAnalysisResult(
                model=VisionModel.CLAUDE_VISION,
                direction="HOLD",
                confidence=0,
                error=str(e)
            )

    async def analyze_with_gemini_vision(
        self,
        images_base64: Dict[str, str],
        prompt: str,
    ) -> VisionAnalysisResult:
        """Analyze charts using Gemini Vision."""
        if not self.google_key:
            return VisionAnalysisResult(
                model=VisionModel.GEMINI_VISION,
                direction="HOLD",
                confidence=0,
                error="Google API key not configured"
            )

        start_time = datetime.now()

        try:
            # Build parts with images
            parts = []
            for timeframe, image_b64 in images_base64.items():
                parts.append({"text": f"Chart for {timeframe} timeframe:"})
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": image_b64
                    }
                })

            parts.append({"text": prompt})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1/models/{VisionModel.GEMINI_VISION}:generateContent?key={self.google_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": parts}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 2000
                        },
                        "systemInstruction": {
                            "parts": [{
                                "text": "You are an expert technical analyst specializing in forex and CFD trading. Analyze charts precisely and provide actionable trading recommendations."
                            }]
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

            return self._parse_analysis_response(
                raw_text=raw_text,
                model=VisionModel.GEMINI_VISION,
                latency_ms=latency
            )

        except Exception as e:
            return VisionAnalysisResult(
                model=VisionModel.GEMINI_VISION,
                direction="HOLD",
                confidence=0,
                error=str(e)
            )

    async def analyze_all_models(
        self,
        images_base64: Dict[str, str],
        prompt: str,
        models: Optional[List[VisionModel]] = None,
    ) -> List[VisionAnalysisResult]:
        """
        Run analysis on all specified vision models in parallel.

        Args:
            images_base64: Dict mapping timeframe to base64 chart image
            prompt: Analysis prompt
            models: List of models to use. Defaults to all available.

        Returns:
            List of analysis results from each model
        """
        if models is None:
            models = list(VisionModel)

        tasks = []
        for model in models:
            if model == VisionModel.GPT4_VISION:
                tasks.append(self.analyze_with_gpt4_vision(images_base64, prompt))
            elif model == VisionModel.CLAUDE_VISION:
                tasks.append(self.analyze_with_claude_vision(images_base64, prompt))
            elif model == VisionModel.GEMINI_VISION:
                tasks.append(self.analyze_with_gemini_vision(images_base64, prompt))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(VisionAnalysisResult(
                    model=models[i].value,
                    direction="HOLD",
                    confidence=0,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def _parse_analysis_response(
        self,
        raw_text: str,
        model: str,
        latency_ms: int
    ) -> VisionAnalysisResult:
        """Parse the AI response to extract structured data."""
        result = VisionAnalysisResult(
            model=model,
            direction="HOLD",
            confidence=50,
            raw_response=raw_text,
            latency_ms=latency_ms
        )

        text_upper = raw_text.upper()

        # Extract direction
        if "**DIRECTION**:" in text_upper or "DIRECTION:" in text_upper:
            if "LONG" in text_upper.split("DIRECTION")[1][:50]:
                result.direction = "LONG"
            elif "SHORT" in text_upper.split("DIRECTION")[1][:50]:
                result.direction = "SHORT"
            else:
                result.direction = "HOLD"
        elif "RECOMMENDATION" in text_upper:
            section = text_upper.split("RECOMMENDATION")[1][:200]
            if "LONG" in section or "BUY" in section:
                result.direction = "LONG"
            elif "SHORT" in section or "SELL" in section:
                result.direction = "SHORT"

        # Extract confidence
        confidence_patterns = [
            r'\*\*CONFIDENCE\*\*:\s*(\d+)',
            r'CONFIDENCE:\s*(\d+)',
            r'CONFIDENCE\s*[:\-]\s*(\d+)',
            r'(\d+)\s*%\s*CONFIDENCE',
        ]
        for pattern in confidence_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result.confidence = min(100, max(0, int(match.group(1))))
                break

        # Extract stop loss
        sl_patterns = [
            r'STOP\s*LOSS[:\s]*[\$]?([\d.]+)',
            r'SL[:\s]*[\$]?([\d.]+)',
        ]
        for pattern in sl_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    result.stop_loss = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract take profit
        tp_patterns = [
            r'TAKE\s*PROFIT[:\s]*[\$]?([\d.]+)',
            r'TP[:\s]*[\$]?([\d.]+)',
            r'TARGET[:\s]*[\$]?([\d.]+)',
        ]
        take_profits = []
        for pattern in tp_patterns:
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for m in matches:
                try:
                    take_profits.append(float(m))
                except ValueError:
                    pass
        if take_profits:
            result.take_profit = take_profits[:3]  # Max 3 targets

        # Extract risk/reward
        rr_patterns = [
            r'RISK[/\s]*REWARD[:\s]*([\d.]+)[:\s]*([\d.]+)',
            r'R[:\s]*R[:\s]*([\d.]+)',
            r'(\d+)[:\s]*(\d+)\s*R',
        ]
        for pattern in rr_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        result.risk_reward = float(match.group(2)) / float(match.group(1))
                    else:
                        result.risk_reward = float(match.group(1))
                    break
                except (ValueError, ZeroDivisionError):
                    pass

        # Extract patterns detected
        pattern_keywords = [
            "head and shoulders", "double top", "double bottom",
            "triangle", "flag", "pennant", "wedge", "channel",
            "engulfing", "doji", "hammer", "shooting star",
            "morning star", "evening star", "three white soldiers",
            "support", "resistance", "breakout", "breakdown"
        ]
        detected = []
        for p in pattern_keywords:
            if p.lower() in raw_text.lower():
                detected.append(p.title())
        result.patterns_detected = detected if detected else None

        # Extract reasoning (first 500 chars of the response)
        result.reasoning = raw_text[:500] + "..." if len(raw_text) > 500 else raw_text

        return result


# Singleton instance
_vision_analyzer: Optional[VisionAnalyzer] = None


def get_vision_analyzer() -> VisionAnalyzer:
    """Get or create the vision analyzer singleton."""
    global _vision_analyzer
    if _vision_analyzer is None:
        _vision_analyzer = VisionAnalyzer()
    return _vision_analyzer
