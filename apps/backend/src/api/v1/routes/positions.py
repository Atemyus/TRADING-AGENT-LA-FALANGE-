"""
Positions routes - Open positions management.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class PositionResponse(BaseModel):
    """Position information."""
    position_id: str
    symbol: str
    side: str  # "long" or "short"
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    margin_used: Decimal
    leverage: int
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    opened_at: str


class PositionModify(BaseModel):
    """Request to modify position."""
    stop_loss: Optional[Decimal] = Field(None, description="New stop loss price")
    take_profit: Optional[Decimal] = Field(None, description="New take profit price")


class PositionsListResponse(BaseModel):
    """List of positions."""
    positions: List[PositionResponse]
    total_unrealized_pnl: Decimal
    total_margin_used: Decimal


@router.get("", response_model=PositionsListResponse)
async def get_positions():
    """Get all open positions."""
    # TODO: Implement with broker
    return PositionsListResponse(
        positions=[],
        total_unrealized_pnl=Decimal("0"),
        total_margin_used=Decimal("0"),
    )


@router.get("/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str):
    """Get position for specific symbol."""
    # TODO: Implement with broker
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No position found for {symbol}"
    )


@router.patch("/{symbol}")
async def modify_position(symbol: str, modification: PositionModify):
    """
    Modify stop loss / take profit for a position.
    """
    # TODO: Implement position modification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Position modification not yet implemented"
    )


@router.delete("/{symbol}")
async def close_position(symbol: str, size: Optional[Decimal] = None):
    """
    Close a position (fully or partially).

    Args:
        symbol: Symbol to close
        size: Size to close (None = close all)
    """
    # TODO: Implement position closing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Position closing not yet implemented"
    )
