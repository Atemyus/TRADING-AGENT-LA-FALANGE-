"""
Trading routes - Order management and execution.
"""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.engines.trading.base_broker import OrderRequest, OrderSide, OrderType, TimeInForce
from src.engines.trading.broker_factory import NoBrokerConfiguredError
from src.services.trading_service import get_trading_service

router = APIRouter()


def handle_broker_error(e: Exception):
    """Convert broker errors to HTTP exceptions."""
    if isinstance(e, NoBrokerConfiguredError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(e),
    )


class OrderCreate(BaseModel):
    """Request to create a new order."""
    symbol: str = Field(..., description="Trading symbol (e.g., EUR_USD)")
    side: OrderSide = Field(..., description="Order side: buy or sell")
    order_type: OrderType = Field(default=OrderType.MARKET)
    size: Decimal = Field(..., gt=0, description="Order size")
    price: Decimal | None = Field(None, description="Limit price")
    stop_loss: Decimal | None = Field(None, description="Stop loss price")
    take_profit: Decimal | None = Field(None, description="Take profit price")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC)
    leverage: int = Field(default=1, ge=1, le=100)


class OrderResponse(BaseModel):
    """Order response."""
    success: bool
    order_id: str | None = None
    symbol: str
    side: str
    order_type: str
    status: str
    size: str
    filled_size: str
    price: str | None = None
    average_fill_price: str | None = None
    commission: str = "0"
    message: str = ""
    risk_warnings: list[str] = []

    class Config:
        from_attributes = True


class ClosePositionRequest(BaseModel):
    """Request to close a position."""
    size: Decimal | None = Field(None, description="Size to close (None = close all)")


class PriceResponse(BaseModel):
    """Price response."""
    symbol: str
    bid: str
    ask: str
    mid: str
    spread: str
    timestamp: str


@router.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderCreate):
    """
    Create a new trading order.

    This endpoint validates the order against risk management rules
    and submits it to the configured broker.
    """
    service = await get_trading_service()

    # Build order request
    order_request = OrderRequest(
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        size=order.size,
        price=order.price,
        stop_loss=order.stop_loss,
        take_profit=order.take_profit,
        time_in_force=order.time_in_force,
        leverage=order.leverage,
    )

    # Execute order
    result = await service.place_order(order_request)

    if not result.success and result.order_result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return OrderResponse(
        success=result.success,
        order_id=result.order_result.order_id if result.order_result else None,
        symbol=order.symbol,
        side=order.side.value,
        order_type=order.order_type.value,
        status=result.order_result.status.value if result.order_result else "failed",
        size=str(order.size),
        filled_size=str(result.order_result.filled_size) if result.order_result else "0",
        price=str(order.price) if order.price else None,
        average_fill_price=str(result.order_result.average_fill_price) if result.order_result and result.order_result.average_fill_price else None,
        commission=str(result.order_result.commission) if result.order_result else "0",
        message=result.message,
        risk_warnings=result.risk_warnings,
    )


@router.get("/orders")
async def get_orders(symbol: str | None = None):
    """Get list of pending orders with optional symbol filter."""
    service = await get_trading_service()
    orders = await service.get_open_orders(symbol)

    return {
        "orders": [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side.value,
                "order_type": o.order_type.value,
                "status": o.status.value,
                "size": str(o.size),
                "filled_size": str(o.filled_size),
                "price": str(o.price) if o.price else None,
                "created_at": str(o.created_at),
            }
            for o in orders
        ],
        "count": len(orders),
    }


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel a pending order."""
    service = await get_trading_service()
    success = await service.cancel_order(order_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel order {order_id}",
        )

    return {"success": True, "order_id": order_id, "message": "Order cancelled"}


@router.post("/close/{symbol}")
async def close_position(symbol: str, request: ClosePositionRequest | None = None):
    """
    Close a position.

    Args:
        symbol: Symbol to close
        request: Optional size to close (None = close entire position)
    """
    service = await get_trading_service()
    size = request.size if request else None

    result = await service.close_position(symbol, size)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return {
        "success": True,
        "symbol": symbol,
        "closed_size": str(result.order_result.filled_size) if result.order_result else None,
        "close_price": str(result.order_result.average_fill_price) if result.order_result else None,
        "message": result.message,
    }


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str):
    """Get current price for a symbol."""
    try:
        service = await get_trading_service()
        price = await service.get_price(symbol)

        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price not found for {symbol}",
            )

        return PriceResponse(**price)
    except NoBrokerConfiguredError as e:
        handle_broker_error(e)
    except HTTPException:
        raise
    except Exception as e:
        handle_broker_error(e)


@router.get("/prices")
async def get_prices(symbols: str):
    """
    Get current prices for multiple symbols.

    Args:
        symbols: Comma-separated list of symbols (e.g., "EUR_USD,GBP_USD")
    """
    try:
        service = await get_trading_service()
        symbol_list = [s.strip() for s in symbols.split(",")]
        prices = await service.get_prices(symbol_list)

        return {"prices": prices}
    except NoBrokerConfiguredError as e:
        handle_broker_error(e)
    except Exception as e:
        handle_broker_error(e)
