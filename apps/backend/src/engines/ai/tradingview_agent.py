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
    VERTICAL_LINE = "vertical_line"
    RECTANGLE = "rectangle"
    FIBONACCI = "fibonacci"
    PITCHFORK = "pitchfork"
    SUPPLY_ZONE = "supply_zone"
    DEMAND_ZONE = "demand_zone"
    ORDER_BLOCK = "order_block"
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
    # Advanced indicators
    PIVOT_FIBONACCI = "Pivot Points Fibonacci"
    PIVOT_CAMARILLA = "Pivot Points Camarilla"
    PIVOT_WOODIE = "Pivot Points Woodie"
    AUTO_FIB = "Auto Fib Retracement"
    AUTO_FIB_EXT = "Auto Fib Extension"
    LIQUIDITY_LEVELS = "Liquidity Levels"
    ORDER_BLOCKS = "Order Blocks"
    FAIR_VALUE_GAP = "Fair Value Gap"
    MARKET_STRUCTURE = "Market Structure"
    SUPPLY_DEMAND = "Supply and Demand"
    SMART_MONEY = "Smart Money Concepts"


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

    Uses keyboard shortcuts primarily (more reliable than clicking UI elements).
    TradingView Keyboard Shortcuts:
    - "/" or "." : Open symbol search
    - "," : Change timeframe (opens timeframe menu)
    - "Alt+I" : Open indicators dialog
    - "Alt+T" : Trendline tool
    - "Alt+H" : Horizontal line tool
    - "Alt+V" : Vertical line tool
    - "Alt+C" : Crossline tool
    - "Alt+F" : Fibonacci retracement
    - "Alt+P" : Pitchfork tool
    - Numbers 1-9 : Quick timeframe change
    """

    # Timeframe keyboard mappings (TradingView shortcuts)
    TIMEFRAME_KEYS = {
        "1": "1",      # 1 minute
        "3": "2",      # 3 minutes
        "5": "3",      # 5 minutes
        "15": "4",     # 15 minutes
        "30": "5",     # 30 minutes
        "60": "6",     # 1 hour
        "240": "7",    # 4 hours
        "D": "8",      # Daily
        "W": "9",      # Weekly
    }

    # TradingView URL timeframe format
    TIMEFRAME_URL = {
        "1": "1",
        "3": "3",
        "5": "5",
        "15": "15",
        "30": "30",
        "60": "60",
        "240": "240",
        "D": "1D",
        "W": "1W",
        "M": "1M",
    }

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self._initialized = False
        self._current_symbol = None
        self._current_timeframe = None

        # Modern TradingView selectors (2024/2025)
        self.selectors = {
            # Chart container - multiple fallback selectors
            "chart": [
                "div.chart-container",
                "div[class*='chart-container']",
                "div.layout__area--center",
                "#chart-area",
                "div[data-name='chart-container']",
            ],

            # Canvas for drawing
            "canvas": [
                "canvas",
                "canvas.chart-markup-table",
            ],

            # Symbol search
            "symbol_search": [
                "input[data-role='search']",
                "input[placeholder*='Search']",
                "input[placeholder*='Symbol']",
            ],

            # Indicators dialog
            "indicators_dialog": [
                "div[data-name='indicators-dialog']",
                "div[class*='dialog-']",
            ],
            "indicators_search": [
                "input[placeholder*='Search']",
                "input[data-role='search']",
                "div[data-name='indicators-dialog'] input",
            ],
            "indicator_item": [
                "div[data-title]",
                "div[class*='listItem']",
            ],

            # Timeframe menu
            "timeframe_menu": [
                "button[data-name='date-ranges-menu']",
                "div[id*='time-interval']",
                "button[class*='timeframe']",
            ],
        }

    async def _find_element(self, selector_list: List[str], timeout: int = 5000):
        """Try multiple selectors and return the first matching element."""
        if isinstance(selector_list, str):
            selector_list = [selector_list]

        for selector in selector_list:
            try:
                element = await self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except:
                continue
        return None

    async def _safe_click(self, selector_list: List[str], timeout: int = 5000) -> bool:
        """Safely click an element using multiple selector fallbacks."""
        element = await self._find_element(selector_list, timeout)
        if element:
            try:
                await element.click()
                return True
            except:
                pass
        return False

    async def initialize(self, headless: bool = True):
        """Initialize the browser with optimized settings."""
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
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Block only ads and analytics - DO NOT block images as TradingView charts use them!
        # NOTE: Removed image blocking that was causing empty/tiny screenshots
        await self.context.route("**/ads/**", lambda route: route.abort())
        await self.context.route("**/analytics/**", lambda route: route.abort())
        await self.context.route("**/tracking/**", lambda route: route.abort())
        await self.context.route("**/*google-analytics*", lambda route: route.abort())
        await self.context.route("**/*facebook*", lambda route: route.abort())

        self.page = await self.context.new_page()
        self._initialized = True
        print("[TradingViewBrowser] Initialized successfully")

    async def close(self):
        """Close the browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            print(f"[TradingViewBrowser] Error closing: {e}")
        finally:
            self._initialized = False
            self._current_symbol = None
            self._current_timeframe = None

    async def open_chart(self, symbol: str = "EURUSD", timeframe: str = "15") -> bool:
        """
        Open TradingView chart for a symbol.
        Uses URL parameters for reliable symbol/timeframe setting.
        """
        try:
            # Format symbol for TradingView URL
            formatted_symbol = symbol.replace("_", "").replace("/", "")
            if not formatted_symbol.startswith("FX:") and len(formatted_symbol) == 6:
                formatted_symbol = f"FX:{formatted_symbol}"

            # Get URL timeframe format
            tf_url = self.TIMEFRAME_URL.get(timeframe, timeframe)

            # Build TradingView chart URL
            url = f"https://www.tradingview.com/chart/?symbol={formatted_symbol}&interval={tf_url}"
            print(f"[TradingViewBrowser] Opening: {url}")

            # Navigate with extended timeout
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"[TradingViewBrowser] Page loaded with status: {response.status if response else 'unknown'}")

            # Wait for chart to be ready - try multiple selectors
            chart_ready = False
            for selector in self.selectors["chart"]:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    chart_ready = True
                    print(f"[TradingViewBrowser] Chart found with selector: {selector}")
                    break
                except Exception as e:
                    print(f"[TradingViewBrowser] Selector '{selector}' not found: {type(e).__name__}")
                    continue

            if not chart_ready:
                # Fallback: wait for any canvas element
                try:
                    await self.page.wait_for_selector("canvas", timeout=10000)
                    chart_ready = True
                    print("[TradingViewBrowser] Chart found via canvas fallback")
                except:
                    print("[TradingViewBrowser] WARNING: No chart canvas found!")

            # Extra wait for chart rendering (candlesticks, indicators)
            print("[TradingViewBrowser] Waiting 4 seconds for chart to fully render...")
            await asyncio.sleep(4)

            # Dismiss any popups/modals
            await self._dismiss_popups()

            # Verify page content
            title = await self.page.title()
            print(f"[TradingViewBrowser] Page title: {title}")

            self._current_symbol = symbol
            self._current_timeframe = timeframe

            return chart_ready

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to open chart: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _dismiss_popups(self):
        """Dismiss any popups, cookie banners, or modals."""
        try:
            # Press Escape multiple times to close any open dialogs
            for _ in range(3):
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.2)

            # Try to click common close/accept buttons
            close_selectors = [
                "button[aria-label='Close']",
                "button[data-name='close']",
                "div[data-name='close']",
                "button:has-text('Accept')",
                "button:has-text('OK')",
                "button:has-text('Got it')",
            ]
            for selector in close_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.2)
                except:
                    continue
        except:
            pass

    async def take_screenshot(self) -> str:
        """Take a screenshot of the chart and return base64."""
        try:
            # Dismiss any popups first
            await self._dismiss_popups()
            await asyncio.sleep(0.5)

            print(f"[TradingViewBrowser] Attempting to take screenshot...")
            print(f"[TradingViewBrowser] Current URL: {self.page.url}")

            # Try to screenshot the chart container
            for selector in self.selectors["chart"]:
                try:
                    chart_element = await self.page.query_selector(selector)
                    if chart_element:
                        # Check if element is visible
                        box = await chart_element.bounding_box()
                        print(f"[TradingViewBrowser] Found chart element with selector '{selector}', box: {box}")
                        if box and box['width'] > 100 and box['height'] > 100:
                            screenshot = await chart_element.screenshot()
                            size_kb = len(screenshot) / 1024
                            print(f"[TradingViewBrowser] Chart screenshot: {len(screenshot)} bytes ({size_kb:.1f} KB) - {box['width']}x{box['height']} px")
                            if size_kb < 10:
                                print(f"[TradingViewBrowser] WARNING: Screenshot is very small, chart may not have loaded properly")
                            return base64.b64encode(screenshot).decode('utf-8')
                except Exception as e:
                    print(f"[TradingViewBrowser] Selector '{selector}' failed: {e}")
                    continue

            # Fallback: full page screenshot
            print(f"[TradingViewBrowser] No chart element found, taking full page screenshot")
            screenshot = await self.page.screenshot(full_page=True)
            size_kb = len(screenshot) / 1024
            print(f"[TradingViewBrowser] Full page screenshot: {len(screenshot)} bytes ({size_kb:.1f} KB)")
            if size_kb < 50:
                print(f"[TradingViewBrowser] WARNING: Full page screenshot is very small, page may not have loaded")
            return base64.b64encode(screenshot).decode('utf-8')

        except Exception as e:
            print(f"[TradingViewBrowser] Screenshot failed: {e}")
            import traceback
            traceback.print_exc()
            return ""

    async def change_timeframe(self, timeframe: str) -> bool:
        """
        Change the chart timeframe.
        Uses keyboard shortcuts (faster than URL navigation).
        """
        try:
            print(f"[TradingViewBrowser] Changing timeframe to {timeframe}...")

            # Method 1: Try keyboard shortcut first (faster)
            tf_key = self.TIMEFRAME_KEYS.get(timeframe)
            if tf_key:
                await self.page.keyboard.press(tf_key)
                await asyncio.sleep(2)  # Wait for chart to update
                await self._dismiss_popups()
                self._current_timeframe = timeframe
                print(f"[TradingViewBrowser] Timeframe changed to {timeframe} via keyboard (key: {tf_key})")
                return True

            # Method 2: Fallback to URL navigation
            if self._current_symbol:
                symbol = self._current_symbol.replace("_", "").replace("/", "")
                if not symbol.startswith("FX:") and len(symbol) == 6:
                    symbol = f"FX:{symbol}"

                tf_url = self.TIMEFRAME_URL.get(timeframe, timeframe)
                url = f"https://www.tradingview.com/chart/?symbol={symbol}&interval={tf_url}"

                print(f"[TradingViewBrowser] Using URL fallback: {url}")
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                await self._dismiss_popups()

                self._current_timeframe = timeframe
                print(f"[TradingViewBrowser] Timeframe changed to {timeframe} via URL")
                return True

            print(f"[TradingViewBrowser] ERROR: Cannot change timeframe - no keyboard key and no current symbol")
            return False

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to change timeframe: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def add_indicator(self, indicator_name: str, params: Dict[str, Any] = None) -> bool:
        """
        Add an indicator to the chart.
        Uses "/" search shortcut (most reliable).
        """
        try:
            print(f"[TradingViewBrowser] Adding indicator: {indicator_name}")

            # Method 1: Use "/" shortcut to open search, then type indicator name
            await self.page.keyboard.press("/")
            await asyncio.sleep(0.8)

            # Type the indicator name
            await self.page.keyboard.type(indicator_name, delay=50)
            await asyncio.sleep(1)

            # Press Enter to select first result
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            # Press Escape to close dialog
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            print(f"[TradingViewBrowser] Indicator {indicator_name} added")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to add indicator {indicator_name}: {e}")
            # Try to recover by pressing Escape
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass
            return False

    async def remove_all_indicators(self) -> bool:
        """Remove all indicators from the chart."""
        try:
            # TradingView doesn't have a "remove all" shortcut
            # Best approach: reload the chart without indicators
            # Or use right-click menu on each indicator

            # For now, just reload the clean chart
            if self._current_symbol and self._current_timeframe:
                await self.open_chart(self._current_symbol, self._current_timeframe)
                print("[TradingViewBrowser] Chart reloaded (indicators cleared)")
                return True
            return False

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to remove indicators: {e}")
            return False

    async def _get_chart_bounds(self) -> Optional[Dict[str, float]]:
        """Get the bounding box of the chart area."""
        for selector in self.selectors["chart"]:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    box = await element.bounding_box()
                    if box and box['width'] > 100:
                        return box
            except:
                continue

        # Fallback: use viewport dimensions with margins
        return {
            'x': 100,
            'y': 100,
            'width': 1720,  # 1920 - 200 margin
            'height': 800,
        }

    async def draw_trendline(self, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        """
        Draw a trendline on the chart.
        Uses Alt+T shortcut to activate trendline tool.
        """
        try:
            print(f"[TradingViewBrowser] Drawing trendline from ({start_x},{start_y}) to ({end_x},{end_y})")

            # Activate trendline tool with keyboard shortcut
            await self.page.keyboard.press("Alt+t")
            await asyncio.sleep(0.5)

            # Draw the line
            await self.page.mouse.move(start_x, start_y)
            await asyncio.sleep(0.1)
            await self.page.mouse.down()
            await asyncio.sleep(0.1)
            await self.page.mouse.move(end_x, end_y, steps=10)
            await asyncio.sleep(0.1)
            await self.page.mouse.up()
            await asyncio.sleep(0.3)

            # Deselect tool
            await self.page.keyboard.press("Escape")

            print("[TradingViewBrowser] Trendline drawn successfully")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to draw trendline: {e}")
            return False

    async def draw_horizontal_line(self, y: int) -> bool:
        """
        Draw a horizontal line at a specific Y position.
        Uses Alt+H shortcut to activate horizontal line tool.
        """
        try:
            print(f"[TradingViewBrowser] Drawing horizontal line at y={y}")

            # Get chart center X
            bounds = await self._get_chart_bounds()
            center_x = int(bounds['x'] + bounds['width'] / 2) if bounds else 960

            # Activate horizontal line tool
            await self.page.keyboard.press("Alt+h")
            await asyncio.sleep(0.5)

            # Click to place the line
            await self.page.mouse.click(center_x, y)
            await asyncio.sleep(0.3)

            # Deselect
            await self.page.keyboard.press("Escape")

            print("[TradingViewBrowser] Horizontal line drawn successfully")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to draw horizontal line: {e}")
            return False

    async def draw_rectangle(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """
        Draw a rectangle zone on the chart.
        Uses keyboard navigation to find rectangle tool.
        """
        try:
            print(f"[TradingViewBrowser] Drawing rectangle from ({x1},{y1}) to ({x2},{y2})")

            # TradingView rectangle shortcut - try multiple approaches
            # First try direct shortcut
            await self.page.keyboard.press("Alt+Shift+r")
            await asyncio.sleep(0.5)

            # Draw the rectangle
            await self.page.mouse.move(x1, y1)
            await asyncio.sleep(0.1)
            await self.page.mouse.down()
            await asyncio.sleep(0.1)
            await self.page.mouse.move(x2, y2, steps=10)
            await asyncio.sleep(0.1)
            await self.page.mouse.up()
            await asyncio.sleep(0.3)

            # Deselect
            await self.page.keyboard.press("Escape")

            print("[TradingViewBrowser] Rectangle drawn successfully")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to draw rectangle: {e}")
            return False

    async def draw_fibonacci(self, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        """
        Draw Fibonacci retracement on the chart.
        Uses Alt+F shortcut to activate Fibonacci tool.
        """
        try:
            print(f"[TradingViewBrowser] Drawing Fibonacci from ({start_x},{start_y}) to ({end_x},{end_y})")

            # Activate Fibonacci tool
            await self.page.keyboard.press("Alt+f")
            await asyncio.sleep(0.5)

            # Draw from swing high to swing low (or vice versa)
            await self.page.mouse.move(start_x, start_y)
            await asyncio.sleep(0.1)
            await self.page.mouse.down()
            await asyncio.sleep(0.1)
            await self.page.mouse.move(end_x, end_y, steps=10)
            await asyncio.sleep(0.1)
            await self.page.mouse.up()
            await asyncio.sleep(0.3)

            # Deselect
            await self.page.keyboard.press("Escape")

            print("[TradingViewBrowser] Fibonacci drawn successfully")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to draw Fibonacci: {e}")
            return False

    async def draw_pitchfork(self, x1: int, y1: int, x2: int, y2: int, x3: int, y3: int) -> bool:
        """
        Draw a Pitchfork (Andrew's Pitchfork) on the chart.
        Requires 3 points: pivot, then two reaction points.
        """
        try:
            print(f"[TradingViewBrowser] Drawing Pitchfork with 3 points")

            # Activate Pitchfork tool
            await self.page.keyboard.press("Alt+Shift+p")
            await asyncio.sleep(0.5)

            # Click first point (pivot)
            await self.page.mouse.click(x1, y1)
            await asyncio.sleep(0.3)

            # Click second point
            await self.page.mouse.click(x2, y2)
            await asyncio.sleep(0.3)

            # Click third point
            await self.page.mouse.click(x3, y3)
            await asyncio.sleep(0.3)

            # Deselect
            await self.page.keyboard.press("Escape")

            print("[TradingViewBrowser] Pitchfork drawn successfully")
            return True

        except Exception as e:
            print(f"[TradingViewBrowser] Failed to draw Pitchfork: {e}")
            return False

    async def draw_supply_demand_zone(self, x1: int, y1: int, x2: int, y2: int, zone_type: str = "supply") -> bool:
        """
        Draw a supply or demand zone (colored rectangle).
        zone_type: "supply" (red/bearish) or "demand" (green/bullish)
        """
        # This is essentially a rectangle with specific coloring
        # TradingView applies colors via the properties dialog
        return await self.draw_rectangle(x1, y1, x2, y2)

    async def zoom(self, direction: str = "in", steps: int = 1) -> bool:
        """Zoom in or out on the chart."""
        try:
            for _ in range(steps):
                if direction == "in":
                    await self.page.keyboard.down("Control")
                    await self.page.mouse.wheel(0, -100)
                    await self.page.keyboard.up("Control")
                else:
                    await self.page.keyboard.down("Control")
                    await self.page.mouse.wheel(0, 100)
                    await self.page.keyboard.up("Control")
                await asyncio.sleep(0.2)
            return True
        except Exception as e:
            print(f"[TradingViewBrowser] Failed to zoom: {e}")
            return False

    async def scroll_chart(self, direction: str = "left", pixels: int = 200) -> bool:
        """Scroll the chart left (back in time) or right (forward)."""
        try:
            bounds = await self._get_chart_bounds()
            if bounds:
                center_x = bounds['x'] + bounds['width'] / 2
                center_y = bounds['y'] + bounds['height'] / 2

                await self.page.mouse.move(center_x, center_y)

                # Horizontal scroll
                delta = -pixels if direction == "left" else pixels
                await self.page.mouse.wheel(delta, 0)
                await asyncio.sleep(0.3)

            return True
        except Exception as e:
            print(f"[TradingViewBrowser] Failed to scroll: {e}")
            return False

    async def get_price_at_position(self, x: int, y: int) -> Optional[float]:
        """Get the price level at a specific Y position (approximation)."""
        # This is complex as it requires parsing the price scale
        # For now, return None - AI will estimate from visual context
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

    # AI Models for chart analysis
    # Models via AIML API (api.aimlapi.com)
    VISION_MODELS = {
        "chatgpt": "openai/gpt-5-2",               # Vision: YES - AIML
        "gemini": "google/gemini-3-pro-preview",   # Vision: YES - AIML
        "grok": "x-ai/grok-4-1-fast-reasoning",    # Vision: YES - AIML
        "qwen": "alibaba/qwen3-vl-32b-instruct",   # Vision: YES - AIML
        "llama": "meta-llama/llama-4-scout",       # Text analysis - AIML
        "ernie": "baidu/ernie-4.5-vl-424b-a47b",   # Vision: YES - AIML
        "kimi": "moonshotai/kimi-k2.5",            # Text analysis - NVIDIA
        "mistral": "mistralai/mistral-large-3-675b-instruct-2512",  # Text analysis - NVIDIA
    }

    # Models that use NVIDIA API instead of AIML
    NVIDIA_MODELS = {"kimi", "mistral"}

    # Models that are text-only (no vision/screenshot support)
    TEXT_ONLY_MODELS = {"llama"}

    MODEL_DISPLAY_NAMES = {
        "chatgpt": "ChatGPT 5.2",
        "gemini": "Gemini 3 Pro",
        "grok": "Grok 4.1 Fast",
        "qwen": "Qwen3 VL",
        "llama": "Llama 4 Scout",
        "ernie": "ERNIE 4.5 VL",
        "kimi": "Kimi K2.5",
        "mistral": "Mistral Large 3",
    }

    # Each AI model gets a different analysis style preference
    # NOTE: Max 2 indicators per model (TradingView Free plan limit)
    MODEL_PREFERENCES = {
        "chatgpt": {
            "style": "smc",
            "indicators": ["EMA", "Volume"],
            "focus": "Order Blocks, FVG, Liquidity"
        },
        "gemini": {
            "style": "trend",
            "indicators": ["EMA", "MACD"],
            "focus": "Trend direction and strength"
        },
        "grok": {
            "style": "volatility",
            "indicators": ["ATR", "Bollinger Bands"],
            "focus": "Volatility breakouts and mean reversion"
        },
        "qwen": {
            "style": "hybrid",
            "indicators": ["Ichimoku Cloud", "RSI"],
            "focus": "Cloud analysis with momentum"
        },
        "llama": {
            "style": "momentum",
            "indicators": ["RSI", "Stochastic"],
            "focus": "Momentum shifts and overbought/oversold"
        },
        "ernie": {
            "style": "price_action",
            "indicators": ["Volume", "EMA"],
            "focus": "Candlestick patterns and price structure"
        },
        "kimi": {
            "style": "multi_timeframe",
            "indicators": ["EMA", "RSI"],
            "focus": "Multi-timeframe confluence and key levels"
        },
        "mistral": {
            "style": "institutional",
            "indicators": ["Volume", "MACD"],
            "focus": "Institutional flow analysis and market structure"
        },
    }

    # TradingView Free plan allows max 2 indicators
    MAX_INDICATORS_FREE_PLAN = 2

    # Analysis mode configuration - timeframes and models per mode
    # 8 models available: ChatGPT, Gemini, Grok, Qwen, Llama, ERNIE (AIML) + Kimi, Mistral (NVIDIA)
    MODE_CONFIG = {
        "quick": {
            "timeframes": ["15"],  # 15 minutes
            "num_models": 2,
            "description": "Analisi rapida single-timeframe con 2 modelli AI"
        },
        "standard": {
            "timeframes": ["15", "60"],  # 15m, 1h
            "num_models": 4,
            "description": "Analisi multi-timeframe bilanciata con 4 modelli AI"
        },
        "premium": {
            "timeframes": ["15", "60", "240"],  # 15m, 1h, 4h
            "num_models": 6,
            "description": "Analisi multi-timeframe approfondita con 6 modelli AI"
        },
        "ultra": {
            "timeframes": ["5", "15", "60", "240", "D"],  # 5m, 15m, 1h, 4h, Daily
            "num_models": 8,
            "description": "Analisi multi-timeframe completa con tutti gli 8 modelli AI"
        },
    }

    def __init__(self, max_indicators: int = 2):
        """
        Initialize TradingView AI Agent.

        Args:
            max_indicators: Maximum indicators allowed by TradingView plan.
                           Default 2 (Free plan limit).
        """
        self.browser: Optional[TradingViewBrowser] = None
        self.api_key = settings.AIML_API_KEY
        self.base_url = settings.AIML_BASE_URL
        self.nvidia_api_key = settings.NVIDIA_API_KEY
        self.nvidia_base_url = settings.NVIDIA_BASE_URL
        self.timeout = 120.0
        self.max_indicators = max_indicators

    def _get_api_config(self, model_key: str = None, model_id: str = None) -> tuple:
        """Get the API base URL and key for a given model.
        Can be called with model_key (e.g. 'kimi') or model_id (e.g. 'moonshotai/kimi-k2.5').
        Always reads from env to pick up runtime changes (e.g. settings saved after bot start).
        """
        is_nvidia = False
        if model_key:
            is_nvidia = model_key in self.NVIDIA_MODELS
        elif model_id:
            # Reverse lookup: check if this model_id belongs to a NVIDIA model
            nvidia_model_ids = {self.VISION_MODELS[k] for k in self.NVIDIA_MODELS if k in self.VISION_MODELS}
            is_nvidia = model_id in nvidia_model_ids

        if is_nvidia:
            # Read fresh from env/settings to pick up keys saved after init
            nvidia_key = os.environ.get("NVIDIA_API_KEY") or settings.NVIDIA_API_KEY
            nvidia_url = os.environ.get("NVIDIA_BASE_URL", self.nvidia_base_url)
            return nvidia_url, nvidia_key
        # Read fresh from env/settings to pick up keys saved after init
        aiml_key = os.environ.get("AIML_API_KEY") or settings.AIML_API_KEY
        aiml_url = os.environ.get("AIML_BASE_URL", self.base_url)
        return aiml_url, aiml_key

    def _is_text_only(self, model_key: str = None, model_id: str = None) -> bool:
        """Check if a model is text-only (no vision/screenshot support)."""
        if model_key:
            return model_key in self.TEXT_ONLY_MODELS
        if model_id:
            text_only_ids = {self.VISION_MODELS[k] for k in self.TEXT_ONLY_MODELS if k in self.VISION_MODELS}
            return model_id in text_only_ids
        return False

    def _build_message_content(self, prompt: str, screenshot: str = None, model_key: str = None, model_id: str = None) -> list:
        """Build message content, including image only for vision models."""
        if screenshot and not self._is_text_only(model_key=model_key, model_id=model_id):
            return [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                {"type": "text", "text": prompt}
            ]
        return [{"type": "text", "text": prompt}]

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
                success = False
                drawing_type = drawing.get("type", "")

                try:
                    if drawing_type == "trendline":
                        success = await self.browser.draw_trendline(
                            drawing["start_x"], drawing["start_y"],
                            drawing["end_x"], drawing["end_y"]
                        )
                    elif drawing_type == "horizontal_line":
                        success = await self.browser.draw_horizontal_line(drawing["y"])
                    elif drawing_type == "rectangle":
                        success = await self.browser.draw_rectangle(
                            drawing["x1"], drawing["y1"],
                            drawing["x2"], drawing["y2"]
                        )
                    elif drawing_type == "fibonacci":
                        success = await self.browser.draw_fibonacci(
                            drawing["start_x"], drawing["start_y"],
                            drawing["end_x"], drawing["end_y"]
                        )
                    elif drawing_type == "pitchfork":
                        success = await self.browser.draw_pitchfork(
                            drawing["x1"], drawing["y1"],
                            drawing["x2"], drawing["y2"],
                            drawing["x3"], drawing["y3"]
                        )
                    else:
                        print(f"[TradingViewAgent] Unknown drawing type: {drawing_type}")
                        continue
                except KeyError as e:
                    print(f"[TradingViewAgent] Missing key for {drawing_type}: {e}")
                    continue

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

        prompt = f"""Stai analizzando un grafico {symbol} su TradingView.

Il tuo stile di analisi preferito: {preferences.get('style', 'mixed')}
Il tuo focus preferito: {preferences.get('focus', 'analisi generale')}

Guarda questo grafico e decidi quali indicatori vuoi aggiungere.
Puoi scegliere tra QUALSIASI indicatore disponibile su TradingView:

**Indicatori Base:**
RSI, MACD, EMA, SMA, Bollinger Bands, Stochastic, ADX, ATR, Ichimoku Cloud, VWAP, Volume, OBV, Supertrend

**Pivot Points:**
Pivot Points, Pivot Points Fibonacci, Pivot Points Camarilla, Pivot Points Woodie

**Fibonacci:**
Auto Fib Retracement, Auto Fib Extension, Fib Retracement

**Smart Money Concepts:**
Order Blocks, Fair Value Gap, Liquidity Levels, Market Structure, Supply and Demand, Smart Money Concepts

IMPORTANTE: Puoi aggiungere un MASSIMO di {max_ind} indicatori (limite del piano TradingView).
Scegli i {max_ind} indicatori più utili per il tuo stile di analisi.

Rispondi SOLO con un array JSON di nomi di indicatori (max {max_ind}), es.:
["RSI", "VWAP"]
"""

        try:
            api_url, api_key = self._get_api_config(model_id=model_id)
            content = self._build_message_content(prompt, screenshot, model_id=model_id)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{
                            "role": "user",
                            "content": content
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
        """Ask AI what to draw on the chart (trendlines, S/R, zones, fibonacci, pitchfork)."""

        prompt = f"""Stai analizzando un grafico {symbol} con indicatori.

Il tuo stile di analisi: {preferences.get('style', 'mixed')}
Il tuo focus: {preferences.get('focus', 'analisi generale')}

Il grafico è 1920x1080 pixel. L'area principale del grafico è approssimativamente:
- X: da 100 a 1800 (da sinistra a destra, da prezzi più vecchi a più recenti)
- Y: da 100 a 900 (in alto prezzi più alti, in basso prezzi più bassi)

## ANALISI SMART MONEY CONCEPTS
Cerca e identifica:
1. **Order Blocks (OB)**: L'ultima candela ribassista prima di un forte movimento rialzista (OB rialzista) o viceversa
2. **Fair Value Gaps (FVG)**: Gap di prezzo tra tre candele consecutive (imbalance)
3. **Liquidity Pools**: Zone con molti stop loss (equal highs/lows)
4. **Smart Money Traps (Inducement)**: False rotture create per cacciare gli stop dei retail
5. **Break of Structure (BOS)**: Rottura di un massimo/minimo significativo
6. **Change of Character (CHoCH)**: Primo segnale di cambio trend

## STRUMENTI DI DISEGNO DISPONIBILI
- "trendline": Collega due punti (start_x, start_y, end_x, end_y)
- "horizontal_line": Livello di prezzo specifico (posizione y)
- "rectangle": Zona (x1, y1, x2, y2) - per Order Blocks, Supply/Demand, FVG
- "fibonacci": Ritracciamento/Estensione Fibonacci (start_x, start_y, end_x, end_y)
  - Livelli chiave: 23.6%, 38.2%, 50%, 61.8% (Golden Ratio), 78.6%
  - Estensioni: 127.2%, 161.8%, 200%, 261.8%
- "pitchfork": Pitchfork di Andrew - 3 punti (x1, y1, x2, y2, x3, y3)
  - Punto 1: Pivot point (inizio del trend)
  - Punto 2: Prima reazione (swing high/low)
  - Punto 3: Seconda reazione (pullback)

## ESEMPIO OUTPUT
[
  {{"type": "rectangle", "x1": 600, "y1": 400, "x2": 750, "y2": 480, "label": "🔵 Bullish Order Block - zona di domanda istituzionale"}},
  {{"type": "rectangle", "x1": 400, "y1": 200, "x2": 500, "y2": 250, "label": "🔴 Bearish FVG - imbalance da colmare"}},
  {{"type": "horizontal_line", "y": 350, "label": "💧 Liquidity Pool - stop loss dei retail"}},
  {{"type": "fibonacci", "start_x": 300, "start_y": 600, "end_x": 700, "end_y": 200, "label": "📐 Fib Retracement - 61.8% = golden zone"}},
  {{"type": "pitchfork", "x1": 200, "y1": 500, "x2": 400, "y2": 300, "x3": 600, "y3": 450, "label": "🔱 Andrew's Pitchfork - canale di prezzo"}},
  {{"type": "trendline", "start_x": 200, "start_y": 400, "end_x": 800, "end_y": 300, "label": "📈 Trendline strutturale"}}
]

Disegna 4-6 elementi tecnici chiave. Sii preciso con le coordinate.
Rispondi SOLO con l'array JSON, nessun altro testo.
"""

        try:
            api_url, api_key = self._get_api_config(model_id=model_id)
            content = self._build_message_content(prompt, screenshot, model_id=model_id)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{
                            "role": "user",
                            "content": content
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

        prompt = f"""Hai analizzato {symbol} sul timeframe {timeframe} minuti.

Il tuo stile di analisi: {preferences.get('style', 'mixed')}
Indicatori aggiunti: {', '.join(indicators_used)}
Disegni effettuati:
{drawings_desc}

Ora fornisci la tua analisi di trading completa basata su TUTTO ciò che hai osservato.

IMPORTANTE: Scrivi TUTTO in ITALIANO (reasoning, key_observations).

Rispondi SOLO con un oggetto JSON:
{{
  "direction": "LONG" oppure "SHORT" oppure "HOLD",
  "confidence": 0-100,
  "entry_price": prezzo esatto o null,
  "stop_loss": prezzo esatto o null,
  "take_profit": [prezzo1, prezzo2, prezzo3] o [],
  "break_even_trigger": prezzo ESATTO per spostare SL all'entry (OBBLIGATORIO se LONG o SHORT),
  "trailing_stop_pips": distanza trailing stop in pips oppure null (a tua discrezione),
  "key_observations": ["osservazione1 IN ITALIANO", "osservazione2 IN ITALIANO", ...],
  "reasoning": "Spiegazione completa IN ITALIANO della tua analisi e perché raccomandi questo trade o perché dici HOLD"
}}

Sii specifico con i livelli di prezzo basandoti su ciò che vedi sul grafico.
IMPORTANTE: break_even_trigger è OBBLIGATORIO per ogni segnale LONG o SHORT. trailing_stop_pips è a tua discrezione (null se non necessario).
"""

        try:
            api_url, api_key = self._get_api_config(model_id=model_id)
            is_text_only = self._is_text_only(model_id=model_id)

            # Send all screenshots for context (only for vision models)
            content = []
            if not is_text_only:
                for i, screenshot in enumerate(screenshots[-3:]):  # Last 3 screenshots
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{screenshot}"}
                    })
            content.append({"type": "text", "text": prompt})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
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

    async def _analyze_model_from_screenshot(
        self,
        model_key: str,
        screenshot: str,
        symbol: str,
        timeframe: str,
    ) -> TradingViewAnalysisResult:
        """
        Analyze a screenshot with a specific AI model (API call only, no browser interaction).
        This is optimized for parallel execution - multiple models analyze the same screenshot.
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
            timeframe=timeframe,
        )

        start_time = datetime.now()

        # Build a comprehensive professional prompt for each AI model
        style = preferences.get('style', 'technical')
        focus = preferences.get('focus', 'general technical analysis')
        indicators = ', '.join(preferences.get('indicators', ['EMA', 'RSI']))

        prompt = f"""Sei un analista di trading senior specializzato in {style.upper()} con oltre 15 anni di esperienza nell'analisi di {symbol} sul timeframe {timeframe} minuti.

## IL TUO STILE DI ANALISI: {style.upper()}
Il tuo focus specializzato: {focus}
I tuoi indicatori preferiti: {indicators}

## REQUISITI DELL'ANALISI
Fornisci un'analisi di mercato completa e professionale. La tua analisi deve includere:

1. **ANALISI DELLA STRUTTURA DI MERCATO**:
   - Direzione del trend attuale (rialzista/ribassista/laterale)
   - Swing high e swing low chiave
   - Rotture o cambiamenti della struttura di mercato

2. **LETTURA DEGLI INDICATORI TECNICI**:
   - Cosa mostrano gli indicatori visibili (EMA, RSI, ecc.)
   - Divergenze tra prezzo e indicatori
   - Condizioni di ipercomprato/ipervenduto

3. **LIVELLI DI PREZZO CHIAVE**:
   - Identifica i livelli di supporto dal grafico
   - Identifica i livelli di resistenza dal grafico
   - Order block, zone di squilibrio o aree di liquidità se visibili

4. **STRATEGIA DI ENTRATA/USCITA**:
   - Prezzo di entrata specifico con giustificazione
   - Posizionamento dello stop loss con ragionamento
   - Obiettivi di take profit (livelli multipli)

5. **VALUTAZIONE DEL RISCHIO**:
   - Rischi chiave di questo trade
   - Scenari di invalidazione

6. **GESTIONE AVANZATA DELLA POSIZIONE** (OBBLIGATORIO per LONG/SHORT):
   - **Break Even**: A quale prezzo spostare lo stop loss al prezzo di entrata per proteggere il capitale. Tipicamente quando il prezzo raggiunge il 40-60% della distanza verso il TP1.
   - **Trailing Stop** (OPZIONALE): Se ritieni utile, indica quanti pips di distanza mantenere come trailing stop DOPO che il break even è stato attivato. Valuta in base alla volatilità e alle condizioni di mercato. Se non lo ritieni necessario, restituisci null.

## FORMATO OUTPUT
Rispondi SOLO con un oggetto JSON valido (niente markdown, niente spiegazioni fuori dal JSON):
{{
  "direction": "LONG" oppure "SHORT" oppure "HOLD",
  "confidence": 0-100 (la tua percentuale di confidenza),
  "entry_price": prezzo esatto o null,
  "stop_loss": prezzo esatto o null,
  "take_profit": [TP1, TP2, TP3] o [],
  "break_even_trigger": prezzo ESATTO al quale spostare lo SL all'entry (OBBLIGATORIO se LONG o SHORT),
  "trailing_stop_pips": distanza in pips per il trailing stop dopo il break even oppure null (a tua discrezione),
  "key_observations": [
    "Osservazione sul trend IN ITALIANO",
    "Osservazione sugli indicatori IN ITALIANO",
    "Osservazione sui livelli di prezzo IN ITALIANO",
    "Osservazione sul momentum IN ITALIANO",
    "Osservazione su volume/volatilità IN ITALIANO"
  ],
  "reasoning": "Fornisci un'analisi professionale dettagliata di 200-400 parole IN ITALIANO che spieghi la tua decisione di trading. Includi livelli di prezzo specifici, letture degli indicatori, analisi della struttura di mercato e fattori di rischio. Scrivi come se stessi presentando a clienti istituzionali."
}}

IMPORTANTE: Sii specifico con i livelli di prezzo effettivi visibili sul grafico. Non usare valori placeholder.
IMPORTANTE: Scrivi TUTTO in ITALIANO (key_observations, reasoning).
IMPORTANTE: break_even_trigger è OBBLIGATORIO per ogni segnale LONG o SHORT. trailing_stop_pips è a tua discrezione (restituisci null se non lo ritieni utile).
"""

        try:
            api_url, api_key = self._get_api_config(model_key=model_key)
            content = self._build_message_content(prompt, screenshot, model_key=model_key)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [{
                            "role": "user",
                            "content": content
                        }],
                        "max_tokens": 3000,  # Increased for longer professional analysis
                        "temperature": 0.3
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                if text is None:
                    # Some models (e.g. Kimi thinking mode) may return content=null
                    text = ""
                    print(f"[{display_name}] Response content was null, skipping")
                else:
                    print(f"[{display_name}] Raw response length: {len(text)} chars")

                # Parse JSON with improved error handling
                import re
                # Try to find JSON object in the response
                match = re.search(r'\{[\s\S]*\}', text)
                if match:
                    try:
                        json_str = match.group()
                        # Clean up common JSON issues
                        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
                        analysis = json.loads(json_str)

                        # Validate and extract fields with defaults
                        direction = analysis.get("direction", "HOLD").upper()
                        if direction not in ["LONG", "SHORT", "HOLD"]:
                            direction = "HOLD"
                        result.direction = direction

                        confidence = analysis.get("confidence", 0)
                        if isinstance(confidence, str):
                            confidence = float(confidence.replace('%', ''))
                        result.confidence = min(max(float(confidence), 0), 100)  # Clamp 0-100

                        result.entry_price = analysis.get("entry_price")
                        result.stop_loss = analysis.get("stop_loss")
                        result.take_profit = analysis.get("take_profit", [])
                        result.break_even_trigger = analysis.get("break_even_trigger")
                        result.trailing_stop_pips = analysis.get("trailing_stop_pips")
                        result.key_observations = analysis.get("key_observations", [])
                        result.reasoning = analysis.get("reasoning", "")

                        # Mark indicators used based on model preferences
                        result.indicators_used = preferences.get("indicators", ["EMA", "RSI"])

                        print(f"[{display_name}] Parsed: {result.direction} @ {result.confidence}% confidence")

                    except json.JSONDecodeError as json_err:
                        print(f"[{display_name}] JSON parse error: {json_err}")
                        print(f"[{display_name}] Problematic JSON: {json_str[:500]}...")
                        # Fallback: try to extract key values from text
                        result.direction = "HOLD"
                        result.confidence = 50
                        result.reasoning = f"Analysis completed but JSON parsing failed. Raw response: {text[:1000]}"
                        result.error = f"JSON parse error: {str(json_err)}"
                else:
                    print(f"[{display_name}] No JSON found in response")
                    result.direction = "HOLD"
                    result.confidence = 50
                    result.reasoning = f"No structured analysis returned. Raw: {text[:500]}"
                    result.error = "No JSON in response"

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - {error_body.get('error', {}).get('message', str(error_body))}"
            except:
                error_detail = f" - {e.response.text[:200]}"
            result.error = f"HTTP {e.response.status_code}{error_detail}"
            result.confidence = 0
            print(f"[{display_name}] HTTP Error {e.response.status_code}{error_detail}")
            print(f"[{display_name}] Model ID: {model_id}")

            # Check for specific error types
            if e.response.status_code == 400:
                print(f"[{display_name}] Bad Request - model may not support vision")
            elif e.response.status_code == 429:
                print(f"[{display_name}] Rate limited - too many requests")
            elif e.response.status_code == 401:
                print(f"[{display_name}] Authentication failed - check API key")

        except httpx.TimeoutException:
            result.error = "Request timed out (90s)"
            result.confidence = 0
            print(f"[{display_name}] Timeout after 90 seconds")

        except Exception as e:
            result.error = str(e)
            result.confidence = 0
            print(f"[{display_name}] Unexpected error: {type(e).__name__}: {e}")

        result.latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        result.screenshots.append(screenshot)
        return result

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
        enabled_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run multi-timeframe analysis based on the selected mode.

        Each mode uses different timeframes and number of AI models:
        - quick: 1 timeframe (15m), 3 models
        - standard: 2 timeframes (15m, 1h), 5 models
        - premium: 3 timeframes (15m, 1h, 4h), 7 models
        - ultra: 5 timeframes (5m, 15m, 1h, 4h, D), 8 models

        Each AI analyzes ALL timeframes for the mode, changing TF on TradingView.
        AI calls are parallelized per timeframe for faster execution.

        Args:
            enabled_models: List of model keys to use. If None, uses all available.
        """
        mode_config = self.MODE_CONFIG.get(mode, self.MODE_CONFIG["standard"])
        timeframes = mode_config["timeframes"]
        num_models = mode_config["num_models"]

        # Select which models to use — filter by enabled_models if provided
        all_model_keys = list(self.VISION_MODELS.keys())
        if enabled_models:
            # Keep only enabled models, preserving order
            all_model_keys = [k for k in all_model_keys if k in enabled_models]

        # Limit to num_models based on mode
        model_keys = all_model_keys[:num_models]

        all_results: List[TradingViewAnalysisResult] = []
        timeframe_analyses: Dict[str, List[TradingViewAnalysisResult]] = {tf: [] for tf in timeframes}

        print(f"\n{'='*60}")
        print(f"TradingView AI Agent - Mode: {mode.upper()} (Parallel)")
        print(f"Symbol: {symbol}")
        print(f"Timeframes: {', '.join(timeframes)}")
        print(f"AI Models: {', '.join([self.MODEL_DISPLAY_NAMES[k] for k in model_keys])}")
        print(f"Max Indicators: {self.max_indicators} (TradingView Free plan)")
        print(f"{'='*60}\n")

        # CRITICAL: Open the chart FIRST before any analysis
        if self.browser and self.browser._initialized:
            first_tf = timeframes[0]
            print(f"[TradingViewAgent] Opening chart for {symbol} on {first_tf} timeframe...")
            chart_opened = await self.browser.open_chart(symbol, first_tf)
            if not chart_opened:
                print(f"[TradingViewAgent] ERROR: Failed to open chart for {symbol}")
                return {
                    "direction": "HOLD",
                    "confidence": 0,
                    "is_strong_signal": False,
                    "models_agree": 0,
                    "total_models": 0,
                    "error": "Failed to open TradingView chart"
                }
            print(f"[TradingViewAgent] Chart opened successfully!")
        else:
            print(f"[TradingViewAgent] ERROR: Browser not initialized!")
            return {
                "direction": "HOLD",
                "confidence": 0,
                "is_strong_signal": False,
                "models_agree": 0,
                "total_models": 0,
                "error": "Browser not initialized"
            }

        # Process each timeframe with all models in parallel
        for tf_index, tf in enumerate(timeframes):
            print(f"\n--- Analyzing {symbol} on {tf} timeframe with {len(model_keys)} models in parallel ---")

            # Prepare chart for this timeframe
            screenshot = None
            if self.browser and self.browser._initialized:
                # Only change timeframe if not the first one (already set in open_chart)
                if tf_index > 0:
                    print(f"[TradingViewAgent] Changing to {tf} timeframe...")
                    await self.browser.change_timeframe(tf)
                    await asyncio.sleep(2)  # Wait for chart to fully update

                # Each AI model will use its OWN preferred indicators
                # But for the shared screenshot, we add a base set
                # Individual models specify which indicators they want in their prompts
                base_indicators = ["EMA", "RSI"][:self.max_indicators]
                print(f"[TradingViewAgent] Adding base indicators: {base_indicators}")
                for indicator in base_indicators:
                    success = await self.browser.add_indicator(indicator)
                    if success:
                        print(f"  [+] Added {indicator}")
                    else:
                        print(f"  [!] Failed to add {indicator}")

                await asyncio.sleep(1)  # Wait for indicators to render
                screenshot = await self.browser.take_screenshot()

                # Remove indicators for next timeframe (clean slate)
                if tf_index < len(timeframes) - 1:
                    print(f"[TradingViewAgent] Clearing indicators for next timeframe...")
                    await self.browser.remove_all_indicators()

            if not screenshot:
                print(f"  [WARNING] Could not capture screenshot for {tf} timeframe")
                continue

            # Run all models in parallel for this timeframe
            print(f"  Sending screenshot to {len(model_keys)} AI models simultaneously...")
            tasks = [
                self._analyze_model_from_screenshot(model_key, screenshot, symbol, tf)
                for model_key in model_keys
            ]
            tf_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in tf_results:
                if isinstance(result, Exception):
                    print(f"  [ERROR] Model analysis failed: {result}")
                    continue
                all_results.append(result)
                timeframe_analyses[tf].append(result)
                print(f"  [{result.model_display_name}] {tf}: {result.direction} ({result.confidence}% confidence)")

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

        # Collect all observations and reasoning (full text, no truncation here)
        all_observations = []
        all_reasoning = []
        for r in agreeing:
            all_observations.extend(r.key_observations)
            if r.reasoning:
                # Include full reasoning with timeframe context
                all_reasoning.append(f"**{r.model_display_name}** ({r.timeframe}m): {r.reasoning}")

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
    max_indicators: int = 2
) -> TradingViewAIAgent:
    """
    Get or create the TradingView AI agent singleton.

    Args:
        headless: Run browser in headless mode
        max_indicators: Max indicators allowed by TradingView Free plan (default 2)
    """
    global _tv_agent
    if _tv_agent is None:
        _tv_agent = TradingViewAIAgent(max_indicators=max_indicators)
        await _tv_agent.initialize(headless=headless)
    return _tv_agent
