"""
Positions routes - Open positions management.
"""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.engines.trading.broker_factory import NoBrokerConfiguredError
from src.services.trading_service import get_trading_service

router = APIRouter()


class PositionResponse(BaseModel):
    """Position information."""
    position_id: str
    symbol: str
    side: str  # "long" or "short"
    size: str
    entry_price: str
    current_price: str
    unrealized_pnl: str
    unrealized_pnl_percent: str
    margin_used: str
    leverage: int
    stop_loss: str | None = None
    take_profit: str | None = None
    opened_at: str


class PositionModify(BaseModel):
    """Request to modify position."""
    stop_loss: Decimal | None = Field(None, description="New stop loss price")
    take_profit: Decimal | None = Field(None, description="New take profit price")


class PositionsListResponse(BaseModel):
    """List of positions."""
    positions: list[PositionResponse]
    total_unrealized_pnl: str
    total_margin_used: str


async def _get_service_or_503():
    try:
        return await get_trading_service()
    except NoBrokerConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.get("", response_model=PositionsListResponse)
async def get_positions():
    """Get all open positions with current prices."""
    service = await _get_service_or_503()
    positions = await service.get_positions_with_prices()

    total_pnl = sum(Decimal(p["unrealized_pnl"]) for p in positions)
    total_margin = sum(Decimal(p["margin_used"]) for p in positions)

    return PositionsListResponse(
        positions=[PositionResponse(**p) for p in positions],
        total_unrealized_pnl=str(total_pnl),
        total_margin_used=str(total_margin),
    )


@router.get("/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str):
    """Get position for specific symbol."""
    service = await _get_service_or_503()
    positions = await service.get_positions_with_prices()

    # Find position for symbol
    position = next((p for p in positions if p["symbol"] == symbol), None)

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No position found for {symbol}"
        )

    return PositionResponse(**position)


@router.patch("/{symbol}")
async def modify_position(symbol: str, modification: PositionModify):
    """
    Modify stop loss / take profit for a position.
    """
    service = await _get_service_or_503()

    success = await service.modify_position(
        symbol=symbol,
        stop_loss=modification.stop_loss,
        take_profit=modification.take_profit,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to modify position for {symbol}"
        )

    return {
        "success": True,
        "symbol": symbol,
        "message": "Position modified successfully",
    }


@router.delete("/{symbol}")
async def close_position(symbol: str, size: Decimal | None = None):
    """
    Close a position (fully or partially).

    Args:
        symbol: Symbol to close
        size: Size to close (None = close all)
    """
    service = await _get_service_or_503()
    result = await service.close_position(symbol, size)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )

    return {
        "success": True,
        "symbol": symbol,
        "closed_size": str(result.order_result.filled_size) if result.order_result else None,
        "close_price": str(result.order_result.average_fill_price) if result.order_result else None,
        "message": result.message,
    }
