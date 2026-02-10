"""
Risk Management Engine

Handles all risk-related calculations and validations:
- Position sizing
- Daily loss limits
- Max positions/exposure
- Stop loss validation
- Correlation checking
"""

from dataclasses import dataclass
from decimal import Decimal

from src.core.config import settings
from src.engines.trading.base_broker import (
    AccountInfo,
    OrderRequest,
    Position,
    PositionSide,
)


@dataclass
class RiskValidationResult:
    """Result of risk validation."""
    is_valid: bool
    adjusted_size: Decimal | None = None
    message: str = ""
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""
    size: Decimal
    notional_value: Decimal
    margin_required: Decimal
    risk_amount: Decimal
    risk_percent: Decimal


class RiskManager:
    """
    Risk management for trading operations.

    Enforces:
    - Maximum positions limit
    - Daily loss limits
    - Per-trade risk limits
    - Stop loss requirements
    - Position correlation limits
    """

    def __init__(
        self,
        max_positions: int = None,
        max_daily_loss_percent: float = None,
        default_risk_per_trade: float = None,
        max_correlation: float = 0.7,
    ):
        self.max_positions = max_positions or settings.MAX_POSITIONS
        self.max_daily_loss_percent = max_daily_loss_percent or settings.MAX_DAILY_LOSS_PERCENT
        self.default_risk_per_trade = default_risk_per_trade or settings.DEFAULT_RISK_PER_TRADE
        self.max_correlation = max_correlation

        # Daily tracking (reset at midnight)
        self._daily_pnl = Decimal("0")
        self._daily_trades = 0

    def calculate_position_size(
        self,
        account: AccountInfo,
        stop_loss_pips: Decimal,
        pip_value: Decimal,
        risk_percent: Decimal | None = None,
    ) -> PositionSizeResult:
        """
        Calculate optimal position size based on risk parameters.

        Formula:
        Position Size = (Account Balance * Risk%) / (Stop Loss Pips * Pip Value)

        Args:
            account: Current account information
            stop_loss_pips: Distance to stop loss in pips
            pip_value: Value per pip for the instrument
            risk_percent: Risk per trade as percentage (default from settings)

        Returns:
            PositionSizeResult with calculated values
        """
        risk_pct = Decimal(str(risk_percent or self.default_risk_per_trade))
        risk_amount = account.balance * (risk_pct / 100)

        if stop_loss_pips <= 0 or pip_value <= 0:
            # Can't calculate without valid stop loss
            return PositionSizeResult(
                size=Decimal("0"),
                notional_value=Decimal("0"),
                margin_required=Decimal("0"),
                risk_amount=risk_amount,
                risk_percent=risk_pct,
            )

        # Calculate size
        size = risk_amount / (stop_loss_pips * pip_value)

        # Calculate notional and margin
        # Assuming 1 lot = 100,000 units for forex
        notional_value = size * pip_value * 10000  # Approximation
        margin_required = notional_value / account.leverage if account.leverage > 0 else notional_value

        return PositionSizeResult(
            size=size.quantize(Decimal("0.01")),
            notional_value=notional_value.quantize(Decimal("0.01")),
            margin_required=margin_required.quantize(Decimal("0.01")),
            risk_amount=risk_amount.quantize(Decimal("0.01")),
            risk_percent=risk_pct,
        )

    def validate_order(
        self,
        order: OrderRequest,
        account: AccountInfo,
        open_positions: list[Position],
        current_price: Decimal,
    ) -> RiskValidationResult:
        """
        Validate an order against all risk rules.

        Checks:
        1. Max positions limit
        2. Daily loss limit not exceeded
        3. Sufficient margin available
        4. Stop loss is set (required)
        5. Risk per trade within limits
        6. Position correlation

        Args:
            order: The order to validate
            account: Current account info
            open_positions: List of open positions
            current_price: Current market price

        Returns:
            RiskValidationResult with validation status
        """
        warnings = []

        # 1. Check max positions
        if len(open_positions) >= self.max_positions:
            return RiskValidationResult(
                is_valid=False,
                message=f"Maximum positions limit reached ({self.max_positions})",
            )

        # 2. Check daily loss limit
        if self._is_daily_loss_exceeded(account):
            return RiskValidationResult(
                is_valid=False,
                message=f"Daily loss limit exceeded ({self.max_daily_loss_percent}%)",
            )

        # 3. Check stop loss is set
        if order.stop_loss is None:
            return RiskValidationResult(
                is_valid=False,
                message="Stop loss is required for all trades",
            )

        # 4. Validate stop loss distance
        stop_loss_result = self._validate_stop_loss(order, current_price)
        if not stop_loss_result.is_valid:
            return stop_loss_result

        # 5. Check margin requirements
        margin_required = self._calculate_margin_required(order, current_price)
        if margin_required > account.margin_available:
            return RiskValidationResult(
                is_valid=False,
                message=f"Insufficient margin. Required: {margin_required}, Available: {account.margin_available}",
            )

        # 6. Check if already have position in same symbol
        existing = next(
            (p for p in open_positions if p.symbol == order.symbol),
            None
        )
        if existing:
            # Check if adding to position or hedging
            is_same_direction = (
                (existing.side == PositionSide.LONG and order.side.value == "buy") or
                (existing.side == PositionSide.SHORT and order.side.value == "sell")
            )
            if is_same_direction:
                warnings.append(f"Adding to existing {existing.side.value} position in {order.symbol}")
            else:
                warnings.append(f"This will reduce/close existing {existing.side.value} position")

        # 7. Check risk per trade
        risk_check = self._validate_risk_per_trade(order, account, current_price)
        if not risk_check.is_valid:
            if risk_check.adjusted_size:
                warnings.append(f"Position size reduced from {order.size} to {risk_check.adjusted_size}")
                return RiskValidationResult(
                    is_valid=True,
                    adjusted_size=risk_check.adjusted_size,
                    message="Order valid with adjusted size",
                    warnings=warnings,
                )
            return risk_check

        return RiskValidationResult(
            is_valid=True,
            message="Order validated successfully",
            warnings=warnings,
        )

    def _is_daily_loss_exceeded(self, account: AccountInfo) -> bool:
        """Check if daily loss limit is exceeded."""
        if account.realized_pnl_today >= 0:
            return False

        loss_percent = abs(account.realized_pnl_today / account.balance) * 100
        return loss_percent >= self.max_daily_loss_percent

    def _validate_stop_loss(
        self,
        order: OrderRequest,
        current_price: Decimal,
    ) -> RiskValidationResult:
        """Validate stop loss placement."""
        if order.stop_loss is None:
            return RiskValidationResult(is_valid=True)

        is_buy = order.side.value == "buy"

        if is_buy:
            # Stop loss must be below current price for buy
            if order.stop_loss >= current_price:
                return RiskValidationResult(
                    is_valid=False,
                    message="Stop loss must be below entry price for buy orders",
                )
            # Check minimum distance (0.1% by default)
            min_distance = current_price * Decimal("0.001")
            if current_price - order.stop_loss < min_distance:
                return RiskValidationResult(
                    is_valid=False,
                    message="Stop loss too close to entry price",
                )
        else:
            # Stop loss must be above current price for sell
            if order.stop_loss <= current_price:
                return RiskValidationResult(
                    is_valid=False,
                    message="Stop loss must be above entry price for sell orders",
                )
            min_distance = current_price * Decimal("0.001")
            if order.stop_loss - current_price < min_distance:
                return RiskValidationResult(
                    is_valid=False,
                    message="Stop loss too close to entry price",
                )

        return RiskValidationResult(is_valid=True)

    def _calculate_margin_required(
        self,
        order: OrderRequest,
        current_price: Decimal,
    ) -> Decimal:
        """Calculate margin required for order."""
        notional = order.size * current_price
        leverage = order.leverage if order.leverage > 0 else 1
        return notional / leverage

    def _validate_risk_per_trade(
        self,
        order: OrderRequest,
        account: AccountInfo,
        current_price: Decimal,
    ) -> RiskValidationResult:
        """Validate and potentially adjust risk per trade."""
        if order.stop_loss is None:
            return RiskValidationResult(is_valid=True)

        # Calculate risk amount
        is_buy = order.side.value == "buy"
        if is_buy:
            risk_per_unit = current_price - order.stop_loss
        else:
            risk_per_unit = order.stop_loss - current_price

        risk_amount = order.size * risk_per_unit
        risk_percent = (risk_amount / account.balance) * 100

        max_risk = Decimal(str(self.default_risk_per_trade * 2))  # Allow 2x default

        if risk_percent > max_risk:
            # Calculate adjusted size
            allowed_risk = account.balance * (max_risk / 100)
            adjusted_size = allowed_risk / risk_per_unit

            return RiskValidationResult(
                is_valid=True,
                adjusted_size=adjusted_size.quantize(Decimal("0.01")),
                message=f"Risk too high ({risk_percent:.1f}%), size adjusted",
            )

        return RiskValidationResult(is_valid=True)

    def update_daily_stats(self, pnl: Decimal):
        """Update daily P&L tracking."""
        self._daily_pnl += pnl
        self._daily_trades += 1

    def reset_daily_stats(self):
        """Reset daily statistics (call at midnight)."""
        self._daily_pnl = Decimal("0")
        self._daily_trades = 0

    def get_daily_stats(self) -> dict:
        """Get current daily statistics."""
        return {
            "daily_pnl": str(self._daily_pnl),
            "daily_trades": self._daily_trades,
        }


# Global risk manager instance
risk_manager = RiskManager()
