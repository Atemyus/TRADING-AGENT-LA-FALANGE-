"""
Economic Calendar Service

Fetches economic news/events from various sources to implement news filtering
for the auto trading bot. Avoids trading during high-impact news events.

Sources:
1. Forex Factory (primary)
2. Investing.com calendar
3. FXStreet calendar
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import httpx
from bs4 import BeautifulSoup
import json


class NewsImpact(str, Enum):
    """Impact level of economic news."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HOLIDAY = "holiday"


@dataclass
class EconomicEvent:
    """An economic calendar event."""
    title: str
    currency: str  # e.g., "USD", "EUR", "GBP"
    impact: NewsImpact
    datetime_utc: datetime
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "currency": self.currency,
            "impact": self.impact.value,
            "datetime_utc": self.datetime_utc.isoformat(),
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
        }


@dataclass
class NewsFilterConfig:
    """Configuration for news filtering."""
    enabled: bool = True
    filter_high_impact: bool = True
    filter_medium_impact: bool = True
    filter_low_impact: bool = False
    minutes_before: int = 30  # Don't trade X minutes before news
    minutes_after: int = 30   # Don't trade X minutes after news
    currencies_to_filter: List[str] = field(default_factory=lambda: [
        "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"
    ])


class EconomicCalendarService:
    """
    Service for fetching and managing economic calendar events.
    """

    def __init__(self):
        self._events: List[EconomicEvent] = []
        self._last_fetch: Optional[datetime] = None
        self._cache_duration = timedelta(hours=1)  # Refresh every hour
        self._filter_config = NewsFilterConfig()

    def configure(self, config: NewsFilterConfig):
        """Update the news filter configuration."""
        self._filter_config = config

    @property
    def config(self) -> NewsFilterConfig:
        """Get current filter configuration."""
        return self._filter_config

    async def fetch_events(self, force_refresh: bool = False) -> List[EconomicEvent]:
        """
        Fetch economic events from calendar sources.

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            List of economic events for today and tomorrow
        """
        now = datetime.utcnow()

        # Check if cache is valid
        if not force_refresh and self._last_fetch:
            if now - self._last_fetch < self._cache_duration and self._events:
                return self._events

        events = []

        # Try multiple sources
        try:
            events = await self._fetch_from_forex_factory()
        except Exception as e:
            print(f"[EconomicCalendar] Forex Factory failed: {e}")

        if not events:
            try:
                events = await self._fetch_from_fxstreet()
            except Exception as e:
                print(f"[EconomicCalendar] FXStreet failed: {e}")

        if not events:
            try:
                events = await self._fetch_from_trading_economics()
            except Exception as e:
                print(f"[EconomicCalendar] Trading Economics failed: {e}")

        if events:
            self._events = events
            self._last_fetch = now
            print(f"[EconomicCalendar] Fetched {len(events)} events")

        return self._events

    async def _fetch_from_forex_factory(self) -> List[EconomicEvent]:
        """Fetch events from Forex Factory calendar."""
        events = []

        # Forex Factory calendar URL
        url = "https://www.forexfactory.com/calendar"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse calendar table
            calendar_rows = soup.select('tr.calendar__row')

            current_date = datetime.utcnow().date()

            for row in calendar_rows:
                try:
                    # Get date
                    date_cell = row.select_one('.calendar__date')
                    if date_cell:
                        date_text = date_cell.get_text(strip=True)
                        if date_text:
                            # Parse date like "Mon Jan 27"
                            try:
                                parsed_date = datetime.strptime(f"{date_text} {datetime.utcnow().year}", "%a %b %d %Y")
                                current_date = parsed_date.date()
                            except:
                                pass

                    # Get time
                    time_cell = row.select_one('.calendar__time')
                    time_text = time_cell.get_text(strip=True) if time_cell else ""

                    # Get currency
                    currency_cell = row.select_one('.calendar__currency')
                    currency = currency_cell.get_text(strip=True) if currency_cell else ""

                    # Get impact
                    impact_cell = row.select_one('.calendar__impact')
                    impact = NewsImpact.LOW
                    if impact_cell:
                        impact_span = impact_cell.select_one('span')
                        if impact_span:
                            impact_class = impact_span.get('class', [])
                            if any('high' in c for c in impact_class):
                                impact = NewsImpact.HIGH
                            elif any('medium' in c for c in impact_class):
                                impact = NewsImpact.MEDIUM
                            elif any('holiday' in c for c in impact_class):
                                impact = NewsImpact.HOLIDAY

                    # Get event title
                    event_cell = row.select_one('.calendar__event')
                    title = event_cell.get_text(strip=True) if event_cell else ""

                    # Get forecast/previous/actual
                    forecast_cell = row.select_one('.calendar__forecast')
                    previous_cell = row.select_one('.calendar__previous')
                    actual_cell = row.select_one('.calendar__actual')

                    forecast = forecast_cell.get_text(strip=True) if forecast_cell else None
                    previous = previous_cell.get_text(strip=True) if previous_cell else None
                    actual = actual_cell.get_text(strip=True) if actual_cell else None

                    if title and currency:
                        # Parse time
                        event_datetime = datetime.combine(current_date, datetime.min.time())
                        if time_text and time_text not in ["All Day", "Tentative", ""]:
                            try:
                                # Time like "8:30am" or "2:00pm"
                                time_obj = datetime.strptime(time_text.lower(), "%I:%M%p").time()
                                event_datetime = datetime.combine(current_date, time_obj)
                            except:
                                pass

                        events.append(EconomicEvent(
                            title=title,
                            currency=currency,
                            impact=impact,
                            datetime_utc=event_datetime,
                            actual=actual if actual else None,
                            forecast=forecast if forecast else None,
                            previous=previous if previous else None,
                        ))

                except Exception as e:
                    continue

        return events

    async def _fetch_from_fxstreet(self) -> List[EconomicEvent]:
        """Fetch events from FXStreet economic calendar API."""
        events = []

        # FXStreet API endpoint
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)

        url = f"https://www.fxstreet.com/economic-calendar"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            # Parse HTML for events
            soup = BeautifulSoup(response.text, 'html.parser')

            # FXStreet uses JavaScript to load events, so this may return limited results
            event_rows = soup.select('.fxs_c_row')

            for row in event_rows:
                try:
                    currency = row.select_one('.fxs_c_currency')
                    title = row.select_one('.fxs_c_event')
                    impact_el = row.select_one('.fxs_c_volatility')
                    time_el = row.select_one('.fxs_c_time')

                    if currency and title:
                        impact = NewsImpact.LOW
                        if impact_el:
                            impact_text = impact_el.get('title', '').lower()
                            if 'high' in impact_text:
                                impact = NewsImpact.HIGH
                            elif 'medium' in impact_text:
                                impact = NewsImpact.MEDIUM

                        events.append(EconomicEvent(
                            title=title.get_text(strip=True),
                            currency=currency.get_text(strip=True),
                            impact=impact,
                            datetime_utc=datetime.utcnow(),  # Simplified
                        ))
                except:
                    continue

        return events

    async def _fetch_from_trading_economics(self) -> List[EconomicEvent]:
        """Fetch events from Trading Economics (backup source)."""
        events = []

        # Trading Economics has a good calendar
        url = "https://tradingeconomics.com/calendar"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse calendar rows
            rows = soup.select('tr[data-event]')

            for row in rows:
                try:
                    country = row.select_one('.calendar-country')
                    event = row.select_one('.calendar-event')
                    importance = row.get('data-importance', '1')

                    if country and event:
                        # Map importance to impact
                        impact = NewsImpact.LOW
                        if importance == '3':
                            impact = NewsImpact.HIGH
                        elif importance == '2':
                            impact = NewsImpact.MEDIUM

                        # Map country to currency
                        country_text = country.get_text(strip=True)
                        currency_map = {
                            "United States": "USD",
                            "Euro Area": "EUR",
                            "United Kingdom": "GBP",
                            "Japan": "JPY",
                            "Switzerland": "CHF",
                            "Australia": "AUD",
                            "New Zealand": "NZD",
                            "Canada": "CAD",
                        }
                        currency = currency_map.get(country_text, country_text[:3].upper())

                        events.append(EconomicEvent(
                            title=event.get_text(strip=True),
                            currency=currency,
                            impact=impact,
                            datetime_utc=datetime.utcnow(),  # Simplified
                        ))
                except:
                    continue

        return events

    def should_avoid_trading(
        self,
        symbol: str,
        check_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[EconomicEvent]]:
        """
        Check if trading should be avoided due to upcoming news.

        Args:
            symbol: Trading symbol (e.g., "EUR/USD", "GBP/JPY")
            check_time: Time to check (default: now)

        Returns:
            Tuple of (should_avoid, causing_event)
        """
        if not self._filter_config.enabled:
            return False, None

        if check_time is None:
            check_time = datetime.utcnow()

        # Extract currencies from symbol
        symbol_currencies = self._extract_currencies(symbol)

        # Check each event
        for event in self._events:
            # Skip if currency not in our filter list
            if event.currency not in self._filter_config.currencies_to_filter:
                continue

            # Skip if currency not related to the symbol
            if event.currency not in symbol_currencies:
                continue

            # Check impact filter
            if event.impact == NewsImpact.HIGH and not self._filter_config.filter_high_impact:
                continue
            if event.impact == NewsImpact.MEDIUM and not self._filter_config.filter_medium_impact:
                continue
            if event.impact == NewsImpact.LOW and not self._filter_config.filter_low_impact:
                continue

            # Check time window
            event_time = event.datetime_utc
            window_start = event_time - timedelta(minutes=self._filter_config.minutes_before)
            window_end = event_time + timedelta(minutes=self._filter_config.minutes_after)

            if window_start <= check_time <= window_end:
                return True, event

        return False, None

    def _extract_currencies(self, symbol: str) -> List[str]:
        """Extract currency codes from a trading symbol."""
        # Clean symbol
        symbol = symbol.upper().replace("/", "").replace("_", "").replace("-", "")

        # Common currency codes
        currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"]

        found = []
        for curr in currencies:
            if curr in symbol:
                found.append(curr)

        # Handle special cases
        if "XAU" in symbol or "GOLD" in symbol:
            found.append("USD")  # Gold is priced in USD
        if "XAG" in symbol or "SILVER" in symbol:
            found.append("USD")  # Silver is priced in USD
        if "US30" in symbol or "NAS100" in symbol or "US500" in symbol:
            found.append("USD")  # US indices
        if "DE40" in symbol or "DAX" in symbol:
            found.append("EUR")  # German index
        if "UK100" in symbol or "FTSE" in symbol:
            found.append("GBP")  # UK index
        if "JP225" in symbol or "NIKKEI" in symbol:
            found.append("JPY")  # Japan index

        return list(set(found))

    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        impact_filter: Optional[List[NewsImpact]] = None
    ) -> List[EconomicEvent]:
        """
        Get upcoming economic events.

        Args:
            hours_ahead: How many hours to look ahead
            impact_filter: Filter by impact levels (None = all)

        Returns:
            List of upcoming events sorted by time
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)

        upcoming = []
        for event in self._events:
            if now <= event.datetime_utc <= cutoff:
                if impact_filter is None or event.impact in impact_filter:
                    upcoming.append(event)

        return sorted(upcoming, key=lambda e: e.datetime_utc)

    def get_events_for_currency(self, currency: str) -> List[EconomicEvent]:
        """Get all events for a specific currency."""
        return [e for e in self._events if e.currency.upper() == currency.upper()]


# Singleton instance
_calendar_service: Optional[EconomicCalendarService] = None


def get_economic_calendar_service() -> EconomicCalendarService:
    """Get or create the economic calendar service singleton."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = EconomicCalendarService()
    return _calendar_service


async def init_economic_calendar():
    """Initialize and fetch initial calendar data."""
    service = get_economic_calendar_service()
    await service.fetch_events()
    return service
