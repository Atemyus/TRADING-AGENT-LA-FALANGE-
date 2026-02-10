"""
Trading Service

High-level service that coordinates trading operations.
Integrates broker, risk management, and market data.
"""

from dataclasses import dataclass
from decimal import Decimal

from src.core.config import settings
from src.engines.data.market_data import MarketDataService, get_market_data_service
from src.engines.trading.base_broker import (
    AccountInfo,
    BaseBroker,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderType,
    Position,
)
from src.engines.trading.broker_factory import BrokerFactory
from src.engines.trading.risk_manager import RiskManager, risk_manager


@dataclass
class TradeSignal:
    """Trading signal from AI or strategy."""
    symbol: str
    action: str  # "buy", "sell", "close"
    size: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    leverage: int = 1
    reason: str = ""
    confidence: float = 0.0


@dataclass
class TradeResult:
    """Result of trade execution."""
    success: bool
    order_result: OrderResult | None = None
    message: str = ""
    risk_warnings: list[str] = None

    def __post_init__(self):
        if self.risk_warnings is None:
            self.risk_warnings = []


class TradingService:
    """
    Main trading service.

    Coordinates between:
    - Broker (order execution)
    - Risk Manager (validation)
    - Market Data (prices)

    Usage:
        service = TradingService()
        await service.start()

        # Execute a signal
        result = await service.execute_signal(signal)

        # Get positions
        positions = await service.get_positions()
    """

    def __init__(self):
        self._broker: BaseBroker | None = None
        self._market_data: MarketDataService | None = None
        self._risk_manager: RiskManager = risk_manager
        self._running = False

    async def start(self) -> None:
        """Start the trading service."""
        if self._running:
            return

        # Initialize broker
        self._broker = await BrokerFactory.get_instance()

        # Initialize market data
        self._market_data = await get_market_data_service()

        self._running = True

    async def stop(self) -> None:
        """Stop the trading service."""
        self._running = False

        if self._market_data:
            await self._market_data.stop()

        await BrokerFactory.close_all()

    @property
    def is_running(self) -> bool:
        return self._running

    # ==================== Account ====================

    async def get_account_info(self) -> AccountInfo:
        """Get current account information."""
        if not self._broker:
            await self.start()
        return await self._broker.get_account_info()

    async def get_account_summary(self) -> dict:
        """Get account summary as dictionary."""
        account = await self.get_account_info()

        return {
            "account_id": account.account_id,
            "balance": str(account.balance),
            "equity": str(account.equity),
            "margin_used": str(account.margin_used),
            "margin_available": str(account.margin_available),
            "unrealized_pnl": str(account.unrealized_pnl),
            "realized_pnl_today": str(account.realized_pnl_today),
            "currency": account.currency,
            "leverage": account.leverage,
            "margin_level": str(account.margin_level) if account.margin_level else None,
        }

    # ==================== Positions ====================

    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        if not self._broker:
            await self.start()
        return await self._broker.get_positions()

    async def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol."""
        if not self._broker:
            await self.start()
        return await self._broker.get_position(symbol)

    async def get_positions_with_prices(self) -> list[dict]:
        """Get positions with current prices and P&L."""
        positions = await self.get_positions()

        if not positions:
            return []

        # Get current prices
        symbols = [p.symbol for p in positions]
        prices = await self._market_data.get_prices(symbols)

        result = []
        for pos in positions:
            price_update = prices.get(pos.symbol)
            current_price = price_update.mid if price_update else pos.current_price

            # Calculate P&L
            if pos.side.value == "long":
                pnl = (current_price - pos.entry_price) * pos.size
                pnl_percent = ((current_price - pos.entry_price) / pos.entry_price) * 100
            else:
                pnl = (pos.entry_price - current_price) * pos.size
                pnl_percent = ((pos.entry_price - current_price) / pos.entry_price) * 100

            result.append({
                "position_id": pos.position_id,
                "symbol": pos.symbol,
                "side": pos.side.value,
                "size": str(pos.size),
                "entry_price": str(pos.entry_price),
                "current_price": str(current_price),
                "unrealized_pnl": str(pnl),
                "unrealized_pnl_percent": str(pnl_percent),
                "margin_used": str(pos.margin_used),
                "leverage": pos.leverage,
                "stop_loss": str(pos.stop_loss) if pos.stop_loss else None,
                "take_profit": str(pos.take_profit) if pos.take_profit else None,
                "opened_at": str(pos.opened_at),
            })

        return result

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None,
    ) -> TradeResult:
        """Close a position."""
        if not self._broker:
            await self.start()

        try:
            order_result = await self._broker.close_position(symbol, size)
            return TradeResult(
                success=order_result.is_filled,
                order_result=order_result,
                message="Position closed successfully" if order_result.is_filled else "Close failed",
            )
        except Exception as e:
            return TradeResult(
                success=False,
                message=str(e),
            )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        """Modify position stop loss / take profit."""
        if not self._broker:
            await self.start()
        return await self._broker.modify_position(symbol, stop_loss, take_profit)

    # ==================== Orders ====================

    async def place_order(self, order: OrderRequest) -> TradeResult:
        """
        Place an order with risk validation.

        Args:
            order: Order request

        Returns:
            TradeResult with execution details
        """
        if not self._broker:
            await self.start()

        # Check if trading is enabled
        if not settings.TRADING_ENABLED:
            return TradeResult(
                success=False,
                message="Trading is disabled. Set TRADING_ENABLED=true to enable.",
            )

        try:
            # Get current account and positions
            account = await self._broker.get_account_info()
            positions = await self._broker.get_positions()

            # Get current price
            price_update = await self._market_data.get_price(order.symbol)
            if not price_update:
                return TradeResult(
                    success=False,
                    message=f"Could not get price for {order.symbol}",
                )

            current_price = price_update.mid

            # Validate with risk manager
            validation = self._risk_manager.validate_order(
                order=order,
                account=account,
                open_positions=positions,
                current_price=current_price,
            )

            if not validation.is_valid:
                return TradeResult(
                    success=False,
                    message=validation.message,
                    risk_warnings=validation.warnings,
                )

            # Adjust size if needed
            if validation.adjusted_size:
                order.size = validation.adjusted_size

            # Execute order
            order_result = await self._broker.place_order(order)

            # Update risk manager stats
            if order_result.is_filled:
                # Will be updated when position is closed
                pass

            return TradeResult(
                success=order_result.is_filled,
                order_result=order_result,
                message="Order executed successfully" if order_result.is_filled else "Order pending",
                risk_warnings=validation.warnings,
            )

        except Exception as e:
            return TradeResult(
                success=False,
                message=f"Order failed: {str(e)}",
            )

    async def execute_signal(self, signal: TradeSignal) -> TradeResult:
        """
        Execute a trading signal.

        Args:
            signal: Trading signal from AI or strategy

        Returns:
            TradeResult with execution details
        """
        if signal.action == "close":
            return await self.close_position(signal.symbol, signal.size)

        # Build order from signal
        side = OrderSide.BUY if signal.action == "buy" else OrderSide.SELL

        # Calculate size if not provided
        size = signal.size
        if size is None:
            # Use default risk-based sizing
            account = await self.get_account_info()
            price_update = await self._market_data.get_price(signal.symbol)

            if signal.stop_loss and price_update:
                current_price = price_update.mid

                # Calculate stop distance in pips (approximation)
                stop_distance = abs(current_price - signal.stop_loss)
                pip_value = Decimal("0.0001")  # Standard for most forex pairs

                sizing = self._risk_manager.calculate_position_size(
                    account=account,
                    stop_loss_pips=stop_distance / pip_value,
                    pip_value=pip_value,
                )
                size = sizing.size
            else:
                # Default to 1% of account balance
                size = account.balance * Decimal("0.01")

        order = OrderRequest(
            symbol=signal.symbol,
            side=side,
            order_type=OrderType.MARKET,
            size=size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            leverage=signal.leverage,
        )

        return await self.place_order(order)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not self._broker:
            await self.start()
        return await self._broker.cancel_order(order_id)

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Get pending orders."""
        if not self._broker:
            await self.start()
        return await self._broker.get_open_orders(symbol)

    # ==================== Market Data ====================

    async def get_price(self, symbol: str) -> dict | None:
        """Get current price for symbol."""
        if not self._market_data:
            await self.start()

        price = await self._market_data.get_price(symbol)
        if price:
            return {
                "symbol": price.symbol,
                "bid": str(price.bid),
                "ask": str(price.ask),
                "mid": str(price.mid),
                "spread": str(price.spread),
                "timestamp": str(price.timestamp),
            }
        return None

    async def get_prices(self, symbols: list[str]) -> dict[str, dict]:
        """Get current prices for multiple symbols."""
        if not self._market_data:
            await self.start()

        prices = await self._market_data.get_prices(symbols)
        return {
            symbol: {
                "symbol": p.symbol,
                "bid": str(p.bid),
                "ask": str(p.ask),
                "mid": str(p.mid),
                "spread": str(p.spread),
                "timestamp": str(p.timestamp),
            }
            for symbol, p in prices.items()
        }


# Global instance
_trading_service: TradingService | None = None


async def get_trading_service() -> TradingService:
    """Get the global trading service instance."""
    global _trading_service

    if _trading_service is None:
        _trading_service = TradingService()
        await _trading_service.start()

    return _trading_service


async def reset_trading_service() -> None:
    """Reset the trading service to force reconnection with new broker settings."""
    global _trading_service

    if _trading_service is not None:
        await _trading_service.stop()
        _trading_service = None
