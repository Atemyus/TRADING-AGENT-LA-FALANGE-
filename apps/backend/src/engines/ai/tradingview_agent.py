"""
TradingView AI Agent - Autonomous chart interaction and analysis.

This agent:
1. Controls a real TradingView chart via browser automation
2. Each AI can add its own indicators
3. Draw trendlines, support/resistance, zones
4. Take screenshots at each step
5. Reason about what it sees and make trading decisions

Requires: playwright
"""

import asyncio
import base64
import json
import io
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    BrowserContext = None

from src.core.config import settings


class DrawingTool(str, Enum):
    """Available drawing tools on TradingView."""
    TRENDLINE = "trendline"
    HORIZONTAL_LINE = "horizontal_line"
    HORIZONTAL_RAY = "horizontal_ray"
    RECTANGLE = "rectangle"
    FIBONACCI = "fibonacci"
    PITCHFORK = "pitchfork"
    TEXT = "text"


class Indicator(str, Enum):
    """Common TradingView indicators."""
    RSI = "RSI"
    MACD = "MACD"
    EMA = "EMA"
    SMA = "SMA"
    BOLLINGER = "Bollinger Bands"
    STOCHASTIC = "Stochastic"
    ADX = "ADX"
    ATR = "ATR"
    ICHIMOKU = "Ichimoku Cloud"
    VWAP = "VWAP"
    VOLUME = "Volume"
    OBV = "OBV"
    SUPERTREND = "Supertrend"
    PIVOT_POINTS = "Pivot Points"


@dataclass
class ChartAction:
    """Represents an action taken on the chart."""
    action_type: str  # "add_indicator", "draw", "screenshot", "change_timeframe", etc.
    details: Dict[str, Any]
    screenshot_before: Optional[str] = None  # base64
    screenshot_after: Optional[str] = None   # base64
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradingViewAnalysisResult:
    """Result from TradingView AI agent analysis."""
    model: str
    model_display_name: str

    # Analysis output
    analysis_style: str  # "smc", "price_action", "indicator_based", etc.
    indicators_used: List[str]
    drawings_made: List[Dict[str, Any]]  # trendlines, zones, etc.

    # Trading decision
    direction: str  # LONG, SHORT, HOLD
    confidence: float  # 0-100

    # Fields with defaults must come after fields without defaults
    timeframe: str = "15"  # Timeframe analyzed
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: List[float] = field(default_factory=list)

    # Advanced management
    break_even_trigger: Optional[float] = None
    trailing_stop_pips: Optional[float] = None

    # Detailed reasoning
    reasoning: str = ""
    key_observations: List[str] = field(default_factory=list)

    # Screenshots taken during analysis
    screenshots: List[str] = field(default_factory=list)  # base64 images
    actions_taken: List[ChartAction] = field(default_factory=list)

    # Metadata
    latency_ms: int = 0
    error: Optional[str] = None


class TradingViewBrowser:
    """
    Controls a TradingView chart via Playwright browser automation.
    """

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self._initialized = False

        # TradingView selectors (may need updates as TV changes)
        self.selectors = {
            # Chart container
            "chart": "div.chart-container",
            "canvas": "canvas.chart-markup-table",

            # Top toolbar
            "symbol_input": "input[data-role='search']",
            "timeframe_button": "button[data-name='date-ranges-menu']",
            "indicators_button": "button[data-name='open-indicators-dialog']",

            # Drawing toolbar
            "drawing_toolbar": "div[data-name='drawings-toolbar']",
            "trendline_tool": "div[data-name='Trend Line']",
            "horizontal_line_tool": "div[data-name='Horizontal Line']",
            "rectangle_tool": "div[data-name='Rectangle']",
            "fib_tool": "div[data-name='Fib Retracement']",

            # Indicators dialog
            "indicators_search": "input[placeholder='Search']",
            "indicator_item": "div[data-name='indicator-item']",

            # Context menu
            "delete_drawing": "div[data-name='remove']",
        }

    async def initialize(self, headless: bool = True):
        """Initialize the browser."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        if self._initialized:
            return

        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        self.page = await self.context.new_page()
        self._initialized = True

    async def close(self):
        """Close the browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False

    async def open_chart(self, symbol: str = "EURUSD", timeframe: str = "15") -> bool:
        """Open TradingView chart for a symbol."""
        try:
            # Navigate to TradingView chart
            url = f"https://www.tradingview.com/chart/?symbol={symbol}&interval={timeframe}"
            await self.page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for chart to load
            await self.page.wait_for_selector(self.selectors["chart"], timeout=15000)
            await asyncio.sleep(2)  # Extra time for chart to render

            return True
        except Exception as e:
            print(f"Failed to open chart: {e}")
            return False

    async def take_screenshot(self) -> str:
        """Take a screenshot of the chart and return base64."""
        try:
            # Try to screenshot just the chart area
            chart_element = await self.page.query_selector(self.selectors["chart"])
            if chart_element:
                screenshot = await chart_element.screenshot()
            else:
                screenshot = await self.page.screenshot()

            return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return ""

    async def change_timeframe(self, timeframe: str) -> bool:
        """Change the chart timeframe."""
        try:
            # Click timeframe button
            await self.page.click(self.selectors["timeframe_button"])
            await asyncio.sleep(0.5)

            # Select timeframe from dropdown
            await self.page.click(f"div[data-value='{timeframe}']")
            await asyncio.sleep(1)

            return True
        except Exception as e:
            print(f"Failed to change timeframe: {e}")
            return False

    async def add_indicator(self, indicator_name: str, params: Dict[str, Any] = None) -> bool:
        """Add an indicator to the chart."""
        try:
            # Open indicators dialog
            await self.page.click(self.selectors["indicators_button"])
            await asyncio.sleep(0.5)

            # Search for indicator
            search_input = await self.page.wait_for_selector(self.selectors["indicators_search"])
            await search_input.fill(indicator_name)
            await asyncio.sleep(0.5)

            # Click first result
            first_result = await self.page.wait_for_selector(f"div[data-title*='{indicator_name}']")
            if first_result:
                await first_result.click()
                await asyncio.sleep(0.5)

            # Close dialog by pressing Escape
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            return True
        except Exception as e:
            print(f"Failed to add indicator {indicator_name}: {e}")
            return False

    async def remove_all_indicators(self) -> bool:
        """Remove all indicators from the chart."""
        try:
            # Use keyboard shortcut to remove all indicators
            # This varies by TradingView version
            await self.page.keyboard.press("Control+A")
            await asyncio.sleep(0.2)
            await self.page.keyboard.press("Delete")
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print(f"Failed to remove indicators: {e}")
            return False

    async def draw_trendline(self, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        """Draw a trendline on the chart."""
        try:
            # Select trendline tool
            await self.page.click(self.selectors["trendline_tool"])
            await asyncio.sleep(0.3)

            # Draw the line
            await self.page.mouse.move(start_x, start_y)
            await self.page.mouse.down()
            await self.page.mouse.move(end_x, end_y)
            await self.page.mouse.up()
            await asyncio.sleep(0.3)

            return True
        except Exception as e:
            print(f"Failed to draw trendline: {e}")
            return False

    async def draw_horizontal_line(self, y: int) -> bool:
        """Draw a horizontal line at a specific Y position."""
        try:
            # Select horizontal line tool
            await self.page.click(self.selectors["horizontal_line_tool"])
            await asyncio.sleep(0.3)

            # Click to place the line
            await self.page.mouse.click(960, y)  # Center of 1920 width
            await asyncio.sleep(0.3)

            return True
        except Exception as e:
            print(f"Failed to draw horizontal line: {e}")
            return False

    async def draw_rectangle(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Draw a rectangle zone on the chart."""
        try:
            # Select rectangle tool
            await self.page.click(self.selectors["rectangle_tool"])
            await asyncio.sleep(0.3)

            # Draw the rectangle
            await self.page.mouse.move(x1, y1)
            await self.page.mouse.down()
            await self.page.mouse.move(x2, y2)
            await self.page.mouse.up()
            await asyncio.sleep(0.3)

            return True
        except Exception as e:
            print(f"Failed to draw rectangle: {e}")
            return False

    async def zoom(self, direction: str = "in", steps: int = 1) -> bool:
        """Zoom in or out on the chart."""
        try:
            for _ in range(steps):
                if direction == "in":
                    await self.page.keyboard.press("Control+=")
                else:
                    await self.page.keyboard.press("Control+-")
                await asyncio.sleep(0.2)
            return True
        except Exception as e:
            print(f"Failed to zoom: {e}")
            return False

    async def scroll_chart(self, direction: str = "left", pixels: int = 200) -> bool:
        """Scroll the chart left or right."""
        try:
            chart = await self.page.query_selector(self.selectors["chart"])
            if chart:
                box = await chart.bounding_box()
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                await self.page.mouse.move(center_x, center_y)
                delta = -pixels if direction == "left" else pixels
                await self.page.mouse.wheel(delta, 0)
                await asyncio.sleep(0.3)
            return True
        except Exception as e:
            print(f"Failed to scroll: {e}")
            return False

    async def get_price_at_position(self, x: int, y: int) -> Optional[float]:
        """Get the price level at a specific Y position."""
        # This would require parsing the price scale which is complex
        # For now, return None and let AI estimate from visual
        return None


class TradingViewAIAgent:
    """
    AI Agent that autonomously interacts with TradingView.

    Each AI model can:
    1. Decide which indicators to add
    2. Draw on the chart (trendlines, zones, S/R)
    3. Take screenshots at each step
    4. Reason about observations
    5. Make a final trading decision
    """

    # AI Models that support vision
    VISION_MODELS = {
        "chatgpt": "openai/gpt-5-2-chat-latest",
        "gemini": "google/gemini-3-pro-preview",
        "deepseek": "deepseek/deepseek-non-thinking-v3.2-exp",
        "glm": "zhipu/glm-4.5-air",
        "grok": "x-ai/grok-4-1-fast-reasoning",
        "qwen": "qwen-max",
    }

    MODEL_DISPLAY_NAMES = {
        "chatgpt": "ChatGPT 5.2",
        "gemini": "Gemini 3 Pro",
        "deepseek": "DeepSeek V3.2",
        "glm": "GLM 4.5",
        "grok": "Grok 4.1",
        "qwen": "Qwen Max",
    }

    # Each AI model gets a different analysis style preference
    MODEL_PREFERENCES = {
        "chatgpt": {
            "style": "smc",
            "indicators": ["EMA", "Volume"],
            "focus": "Order Blocks, FVG, Liquidity"
        },
        "gemini": {
            "style": "trend",
            "indicators": ["EMA", "ADX", "MACD"],
            "focus": "Trend direction and strength"
        },
        "deepseek": {
            "style": "price_action",
            "indicators": ["Volume"],
            "focus": "Candlestick patterns and structure"
        },
        "glm": {
            "style": "indicator_based",
            "indicators": ["RSI", "MACD", "Bollinger Bands"],
            "focus": "Indicator divergences and signals"
        },
        "grok": {
            "style": "volatility",
            "indicators": ["ATR", "Bollinger Bands", "VWAP"],
            "focus": "Volatility breakouts and mean reversion"
        },
        "qwen": {
            "style": "hybrid",
            "indicators": ["Ichimoku Cloud", "RSI"],
            "focus": "Cloud analysis with momentum"
        },
    }

    # TradingView indicator limits by plan
    TRADINGVIEW_PLANS = {
        "basic": 3,      # Free plan
        "essential": 5,
        "plus": 10,
        "premium": 25,
    }

    # Analysis mode configuration - timeframes and models per mode
    MODE_CONFIG = {
        "quick": {
            "timeframes": ["15"],  # 15 minutes
            "num_models": 1,
            "description": "Fast single-timeframe analysis"
        },
        "standard": {
            "timeframes": ["15", "60"],  # 15m, 1h
            "num_models": 2,
            "description": "Balanced multi-timeframe analysis"
        },
        "premium": {
            "timeframes": ["15", "60", "240"],  # 15m, 1h, 4h
            "num_models": 4,
            "description": "Deep multi-timeframe analysis"
        },
        "ultra": {
            "timeframes": ["5", "15", "60", "240", "D"],  # 5m, 15m, 1h, 4h, Daily
            "num_models": 6,
            "description": "Complete multi-timeframe analysis with all AI models"
        },
    }

    def __init__(self, max_indicators: int = 3):
        """
        Initialize TradingView AI Agent.

        Args:
            max_indicators: Maximum indicators allowed by TradingView plan.
                           Default 3 (Basic/Free plan).
        """
        self.browser: Optional[TradingViewBrowser] = None
        self.api_key = settings.AIML_API_KEY
        self.base_url = settings.AIML_BASE_URL
        self.timeout = 120.0
        self.max_indicators = max_indicators

    async def initialize(self, headless: bool = True):
        """Initialize the browser for TradingView interaction."""
        self.browser = TradingViewBrowser()
        await self.browser.initialize(headless=headless)

    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()

    async def analyze_with_model(
        self,
        model_key: str,
        symbol: str,
        timeframe: str = "15",
    ) -> TradingViewAnalysisResult:
        """
        Run autonomous analysis with a specific AI model.

        The AI will:
        1. See the initial chart
        2. Decide what indicators to add
        3. Draw on the chart
        4. Take multiple screenshots
        5. Provide final analysis
        """
        model_id = self.VISION_MODELS.get(model_key)
        display_name = self.MODEL_DISPLAY_NAMES.get(model_key, model_key)
        preferences = self.MODEL_PREFERENCES.get(model_key, {})

        result = TradingViewAnalysisResult(
            model=model_id,
            model_display_name=display_name,
            analysis_style=preferences.get("style", "mixed"),
            indicators_used=[],
            drawings_made=[],
            direction="HOLD",
            confidence=0,
        )

        if not self.browser or not self.browser._initialized:
            result.error = "Browser not initialized"
            return result

        start_time = datetime.now()

        try:
            # Step 1: Open the chart
            success = await self.browser.open_chart(symbol, timeframe)
            if not success:
                result.error = "Failed to open chart"
                return result

            # Step 2: Take initial screenshot
            initial_screenshot = await self.browser.take_screenshot()
            result.screenshots.append(initial_screenshot)
            result.actions_taken.append(ChartAction(
                action_type="open_chart",
                details={"symbol": symbol, "timeframe": timeframe},
                screenshot_after=initial_screenshot
            ))

            # Step 3: Ask AI what indicators to add
            indicators_to_add = await self._ask_ai_for_indicators(
                model_id, initial_screenshot, symbol, preferences
            )

            # Step 4: Add the indicators
            for indicator in indicators_to_add:
                success = await self.browser.add_indicator(indicator)
                if success:
                    result.indicators_used.append(indicator)
                    screenshot = await self.browser.take_screenshot()
                    result.screenshots.append(screenshot)
                    result.actions_taken.append(ChartAction(
                        action_type="add_indicator",
                        details={"indicator": indicator},
                        screenshot_after=screenshot
                    ))

            # Step 5: Take screenshot with indicators
            chart_with_indicators = await self.browser.take_screenshot()

            # Step 6: Ask AI for drawings (trendlines, zones, S/R)
            drawings = await self._ask_ai_for_drawings(
                model_id, chart_with_indicators, symbol, preferences
            )

            # Step 7: Execute the drawings
            for drawing in drawings:
                if drawing["type"] == "trendline":
                    success = await self.browser.draw_trendline(
                        drawing["start_x"], drawing["start_y"],
                        drawing["end_x"], drawing["end_y"]
                    )
                elif drawing["type"] == "horizontal_line":
                    success = await self.browser.draw_horizontal_line(drawing["y"])
                elif drawing["type"] == "rectangle":
                    success = await self.browser.draw_rectangle(
                        drawing["x1"], drawing["y1"],
                        drawing["x2"], drawing["y2"]
                    )

                if success:
                    result.drawings_made.append(drawing)
                    screenshot = await self.browser.take_screenshot()
                    result.screenshots.append(screenshot)
                    result.actions_taken.append(ChartAction(
                        action_type="draw",
                        details=drawing,
                        screenshot_after=screenshot
                    ))

            # Step 8: Take final screenshot with everything
            final_screenshot = await self.browser.take_screenshot()
            result.screenshots.append(final_screenshot)

            # Step 9: Ask AI for final analysis
            analysis = await self._ask_ai_for_analysis(
                model_id,
                result.screenshots,  # Send all screenshots
                symbol,
                timeframe,
                result.indicators_used,
                result.drawings_made,
                preferences
            )

            # Update result with analysis
            result.direction = analysis.get("direction", "HOLD")
            result.confidence = analysis.get("confidence", 0)
            result.entry_price = analysis.get("entry_price")
            result.stop_loss = analysis.get("stop_loss")
            result.take_profit = analysis.get("take_profit", [])
            result.break_even_trigger = analysis.get("break_even_trigger")
            result.trailing_stop_pips = analysis.get("trailing_stop_pips")
            result.reasoning = analysis.get("reasoning", "")
            result.key_observations = analysis.get("key_observations", [])

            result.latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        except Exception as e:
            result.error = str(e)
            result.latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    async def _ask_ai_for_indicators(
        self,
        model_id: str,
        screenshot: str,
        symbol: str,
        preferences: Dict[str, Any]
    ) -> List[str]:
        """Ask AI which indicators to add based on initial chart."""

        # Respect TradingView indicator limit
        max_ind = min(self.max_indicators, 4)  # Cap at 4 for performance

        prompt = f"""You are analyzing a {symbol} chart on TradingView.

Your preferred analysis style: {preferences.get('style', 'mixed')}
Your preferred focus: {preferences.get('focus', 'general analysis')}

Look at this chart and decide which indicators you want to add.
You can choose from: RSI, MACD, EMA, SMA, Bollinger Bands, Stochastic, ADX, ATR, Ichimoku, VWAP, Volume, Supertrend

IMPORTANT: You can add a MAXIMUM of {max_ind} indicators (TradingView plan limit).
Choose the {max_ind} most useful indicators for your analysis style.

Respond with ONLY a JSON array of indicator names (max {max_ind}), e.g.:
["RSI", "EMA"]
"""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                                {"type": "text", "text": prompt}
                            ]
                        }],
                        "max_tokens": 200,
                        "temperature": 0.3
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]

                # Parse JSON array and enforce limit
                import re
                match = re.search(r'\[.*?\]', text, re.DOTALL)
                if match:
                    indicators = json.loads(match.group())
                    # Enforce the max_indicators limit
                    return indicators[:self.max_indicators]
                # Fallback: use preferences but respect limit
                fallback = preferences.get("indicators", ["EMA", "RSI"])
                return fallback[:self.max_indicators]

        except Exception as e:
            print(f"Error asking AI for indicators: {e}")
            return preferences.get("indicators", ["EMA", "RSI"])

    async def _ask_ai_for_drawings(
        self,
        model_id: str,
        screenshot: str,
        symbol: str,
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Ask AI what to draw on the chart (trendlines, S/R, zones)."""

        prompt = f"""You are analyzing a {symbol} chart with indicators.

Your analysis style: {preferences.get('style', 'mixed')}
Your focus: {preferences.get('focus', 'general analysis')}

The chart is 1920x1080 pixels. Look at the chart and identify:
1. Key trendlines (connect swing highs or swing lows)
2. Important support/resistance levels (horizontal lines)
3. Significant zones (rectangles for order blocks, supply/demand)

Respond with ONLY a JSON array of drawings. Each drawing should have:
- type: "trendline" | "horizontal_line" | "rectangle"
- For trendline: start_x, start_y, end_x, end_y (in pixels)
- For horizontal_line: y (in pixels, where 0 is top, 540 is middle, 1080 is bottom)
- For rectangle: x1, y1, x2, y2 (in pixels)
- label: description of what this drawing represents

Example:
[
  {{"type": "trendline", "start_x": 200, "start_y": 400, "end_x": 800, "end_y": 300, "label": "Uptrend line"}},
  {{"type": "horizontal_line", "y": 350, "label": "Resistance at high"}},
  {{"type": "rectangle", "x1": 600, "y1": 400, "x2": 700, "y2": 450, "label": "Bullish Order Block"}}
]

Identify 2-5 key drawings. Only respond with JSON, no other text.
"""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                                {"type": "text", "text": prompt}
                            ]
                        }],
                        "max_tokens": 500,
                        "temperature": 0.3
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]

                # Parse JSON array
                import re
                match = re.search(r'\[.*?\]', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                return []

        except Exception as e:
            print(f"Error asking AI for drawings: {e}")
            return []

    async def _ask_ai_for_analysis(
        self,
        model_id: str,
        screenshots: List[str],
        symbol: str,
        timeframe: str,
        indicators_used: List[str],
        drawings_made: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ask AI for final trading analysis."""

        drawings_desc = "\n".join([f"- {d.get('label', d.get('type'))}" for d in drawings_made])

        prompt = f"""You have been analyzing {symbol} on the {timeframe} minute timeframe.

Your analysis style: {preferences.get('style', 'mixed')}
Indicators you added: {', '.join(indicators_used)}
Drawings you made:
{drawings_desc}

Now provide your complete trading analysis based on EVERYTHING you've observed.

Respond with ONLY a JSON object:
{{
  "direction": "LONG" or "SHORT" or "HOLD",
  "confidence": 0-100,
  "entry_price": exact price or null,
  "stop_loss": exact price or null,
  "take_profit": [price1, price2, price3] or [],
  "break_even_trigger": price to move SL to entry or null,
  "trailing_stop_pips": trailing stop distance or null,
  "key_observations": ["observation1", "observation2", ...],
  "reasoning": "Complete explanation of your analysis and why you recommend this trade or why you say HOLD"
}}

Be specific with price levels based on what you see on the chart.
"""

        try:
            # Send all screenshots for context
            content = []
            for i, screenshot in enumerate(screenshots[-3:]):  # Last 3 screenshots
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot}"}
                })
            content.append({"type": "text", "text": prompt})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": content}],
                        "max_tokens": 1500,
                        "temperature": 0.2
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]

                # Parse JSON
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                return {"direction": "HOLD", "confidence": 0, "reasoning": text}

        except Exception as e:
            print(f"Error asking AI for analysis: {e}")
            return {"direction": "HOLD", "confidence": 0, "reasoning": str(e)}

    async def analyze_all_models(
        self,
        symbol: str,
        timeframe: str = "15",
    ) -> List[TradingViewAnalysisResult]:
        """
        Run analysis with all AI models sequentially.
        Each model gets a fresh chart and adds its own indicators/drawings.
        """
        results = []

        for model_key in self.VISION_MODELS.keys():
            print(f"Analyzing with {self.MODEL_DISPLAY_NAMES[model_key]}...")

            # Clean up chart for next AI (remove drawings/indicators)
            if self.browser and self.browser._initialized:
                await self.browser.remove_all_indicators()

            result = await self.analyze_with_model(model_key, symbol, timeframe)
            results.append(result)

            # Small delay between models
            await asyncio.sleep(1)

        return results

    async def analyze_with_mode(
        self,
        symbol: str,
        mode: str = "standard",
    ) -> Dict[str, Any]:
        """
        Run multi-timeframe analysis based on the selected mode.

        Each mode uses different timeframes and number of AI models:
        - quick: 1 timeframe (15m), 1 model
        - standard: 2 timeframes (15m, 1h), 2 models
        - premium: 3 timeframes (15m, 1h, 4h), 4 models
        - ultra: 5 timeframes (5m, 15m, 1h, 4h, D), 6 models

        Each AI analyzes ALL timeframes for the mode, changing TF on TradingView.
        """
        mode_config = self.MODE_CONFIG.get(mode, self.MODE_CONFIG["standard"])
        timeframes = mode_config["timeframes"]
        num_models = mode_config["num_models"]

        # Select which models to use based on mode
        model_keys = list(self.VISION_MODELS.keys())[:num_models]

        all_results: List[TradingViewAnalysisResult] = []
        timeframe_analyses: Dict[str, List[TradingViewAnalysisResult]] = {tf: [] for tf in timeframes}

        print(f"\n{'='*60}")
        print(f"TradingView AI Agent - Mode: {mode.upper()}")
        print(f"Timeframes: {', '.join(timeframes)}")
        print(f"AI Models: {', '.join([self.MODEL_DISPLAY_NAMES[k] for k in model_keys])}")
        print(f"{'='*60}\n")

        for model_key in model_keys:
            model_name = self.MODEL_DISPLAY_NAMES[model_key]
            print(f"\n--- {model_name} starting multi-timeframe analysis ---")

            for tf in timeframes:
                print(f"  [{model_name}] Analyzing {symbol} on {tf} timeframe...")

                # Clean chart for fresh analysis
                if self.browser and self.browser._initialized:
                    await self.browser.remove_all_indicators()
                    # Change timeframe on TradingView
                    await self.browser.change_timeframe(tf)
                    await asyncio.sleep(1)

                # Run analysis on this timeframe
                result = await self.analyze_with_model(model_key, symbol, tf)
                result.timeframe = tf
                all_results.append(result)
                timeframe_analyses[tf].append(result)

                print(f"  [{model_name}] {tf}: {result.direction} ({result.confidence}% confidence)")
                await asyncio.sleep(0.5)

        # Calculate consensus per timeframe
        tf_consensus = {}
        for tf, results in timeframe_analyses.items():
            tf_consensus[tf] = self._calculate_timeframe_consensus(results)

        # Calculate overall consensus
        overall_consensus = self.calculate_consensus(all_results)

        # Add multi-timeframe specific data
        overall_consensus["mode"] = mode
        overall_consensus["timeframes_analyzed"] = timeframes
        overall_consensus["models_used"] = [self.MODEL_DISPLAY_NAMES[k] for k in model_keys]
        overall_consensus["timeframe_consensus"] = tf_consensus
        overall_consensus["all_results"] = all_results

        # Multi-timeframe alignment score
        tf_directions = [tc["direction"] for tc in tf_consensus.values() if tc["direction"] != "HOLD"]
        if tf_directions:
            alignment = tf_directions.count(tf_directions[0]) / len(tf_directions) * 100
            overall_consensus["timeframe_alignment"] = round(alignment, 1)
            overall_consensus["is_aligned"] = alignment >= 80  # 80%+ agreement across TFs
        else:
            overall_consensus["timeframe_alignment"] = 0
            overall_consensus["is_aligned"] = False

        print(f"\n{'='*60}")
        print(f"Analysis Complete - {mode.upper()} Mode")
        print(f"Direction: {overall_consensus['direction']}")
        print(f"Confidence: {overall_consensus['confidence']}%")
        print(f"Models Agree: {overall_consensus['models_agree']}/{overall_consensus['total_models']}")
        print(f"Timeframe Alignment: {overall_consensus.get('timeframe_alignment', 0)}%")
        print(f"Strong Signal: {overall_consensus['is_strong_signal']}")
        print(f"{'='*60}\n")

        return overall_consensus

    def _calculate_timeframe_consensus(
        self,
        results: List[TradingViewAnalysisResult]
    ) -> Dict[str, Any]:
        """Calculate consensus for a single timeframe."""
        valid = [r for r in results if not r.error and r.direction != "HOLD"]

        if not valid:
            return {"direction": "HOLD", "confidence": 0, "models_agree": 0}

        long_votes = [r for r in valid if r.direction == "LONG"]
        short_votes = [r for r in valid if r.direction == "SHORT"]

        if len(long_votes) > len(short_votes):
            direction = "LONG"
            agreeing = long_votes
        elif len(short_votes) > len(long_votes):
            direction = "SHORT"
            agreeing = short_votes
        else:
            # Tie - check confidence
            long_conf = sum(r.confidence for r in long_votes) / len(long_votes) if long_votes else 0
            short_conf = sum(r.confidence for r in short_votes) / len(short_votes) if short_votes else 0
            direction = "LONG" if long_conf >= short_conf else "SHORT"
            agreeing = long_votes if direction == "LONG" else short_votes

        avg_confidence = sum(r.confidence for r in agreeing) / len(agreeing) if agreeing else 0

        return {
            "direction": direction,
            "confidence": round(avg_confidence, 1),
            "models_agree": len(agreeing),
            "total_models": len(results),
        }

    def calculate_consensus(
        self,
        results: List[TradingViewAnalysisResult]
    ) -> Dict[str, Any]:
        """Calculate consensus from all AI analyses."""
        valid = [r for r in results if not r.error and r.direction != "HOLD"]
        total = len([r for r in results if not r.error])

        if not valid:
            return {
                "direction": "HOLD",
                "confidence": 0,
                "models_agree": 0,
                "total_models": total,
                "is_strong_signal": False,
            }

        # Count votes
        long_votes = [r for r in valid if r.direction == "LONG"]
        short_votes = [r for r in valid if r.direction == "SHORT"]

        if len(long_votes) > len(short_votes):
            direction = "LONG"
            agreeing = long_votes
        elif len(short_votes) > len(long_votes):
            direction = "SHORT"
            agreeing = short_votes
        else:
            # Tie - use confidence
            long_conf = sum(r.confidence for r in long_votes) / len(long_votes) if long_votes else 0
            short_conf = sum(r.confidence for r in short_votes) / len(short_votes) if short_votes else 0
            if long_conf >= short_conf:
                direction = "LONG"
                agreeing = long_votes
            else:
                direction = "SHORT"
                agreeing = short_votes

        models_agree = len(agreeing)
        avg_confidence = sum(r.confidence for r in agreeing) / models_agree

        # Collect trade parameters
        entries = [r.entry_price for r in agreeing if r.entry_price]
        stop_losses = [r.stop_loss for r in agreeing if r.stop_loss]
        take_profits = [r.take_profit[0] for r in agreeing if r.take_profit]
        break_evens = [r.break_even_trigger for r in agreeing if r.break_even_trigger]
        trailing_stops = [r.trailing_stop_pips for r in agreeing if r.trailing_stop_pips]

        # Collect all observations and reasoning
        all_observations = []
        all_reasoning = []
        for r in agreeing:
            all_observations.extend(r.key_observations)
            if r.reasoning:
                all_reasoning.append(f"**{r.model_display_name}**: {r.reasoning[:300]}")

        # Collect analysis styles and indicators
        styles = list(set(r.analysis_style for r in agreeing))
        indicators = list(set(ind for r in agreeing for ind in r.indicators_used))

        return {
            "direction": direction,
            "confidence": round(avg_confidence, 1),
            "models_agree": models_agree,
            "total_models": total,
            "is_strong_signal": models_agree >= 4 and avg_confidence >= 70,

            # Trade parameters
            "entry_price": round(sum(entries) / len(entries), 5) if entries else None,
            "stop_loss": round(sum(stop_losses) / len(stop_losses), 5) if stop_losses else None,
            "take_profit": round(sum(take_profits) / len(take_profits), 5) if take_profits else None,
            "break_even_trigger": round(sum(break_evens) / len(break_evens), 5) if break_evens else None,
            "trailing_stop_pips": round(sum(trailing_stops) / len(trailing_stops), 1) if trailing_stops else None,

            # Analysis details
            "analysis_styles_used": styles,
            "indicators_used": indicators,
            "key_observations": list(set(all_observations))[:10],
            "combined_reasoning": "\n\n".join(all_reasoning),

            # Individual results
            "individual_analyses": results,

            # Vote breakdown
            "vote_breakdown": {
                "LONG": len(long_votes),
                "SHORT": len(short_votes),
                "HOLD": total - len(long_votes) - len(short_votes),
            }
        }


# Singleton instance
_tv_agent: Optional[TradingViewAIAgent] = None


async def get_tradingview_agent(
    headless: bool = True,
    max_indicators: int = 3
) -> TradingViewAIAgent:
    """
    Get or create the TradingView AI agent singleton.

    Args:
        headless: Run browser in headless mode
        max_indicators: Max indicators allowed by TradingView plan (default 3 for free)
    """
    global _tv_agent
    if _tv_agent is None:
        _tv_agent = TradingViewAIAgent(max_indicators=max_indicators)
        await _tv_agent.initialize(headless=headless)
    return _tv_agent
