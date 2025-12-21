"""
Unit tests for Risk Manager.
"""

from decimal import Decimal
import pytest

from src.engines.trading.risk_manager import RiskManager, PositionSizeResult
from src.engines.trading.base_broker import (
    AccountInfo,
    OrderRequest,
    OrderSide,
    OrderType,
    Position,
    PositionSide,
)


@pytest.fixture
def risk_manager() -> RiskManager:
    """Create risk manager instance."""
    return RiskManager(
        max_positions=5,
        max_daily_loss_percent=5.0,
        default_risk_per_trade=1.0,
    )


@pytest.fixture
def sample_account() -> AccountInfo:
    """Create sample account."""
    return AccountInfo(
        account_id="test-123",
        balance=Decimal("10000"),
        equity=Decimal("10000"),
        margin_used=Decimal("0"),
        margin_available=Decimal("10000"),
        unrealized_pnl=Decimal("0"),
        realized_pnl_today=Decimal("0"),
        currency="USD",
        leverage=20,
    )


class TestPositionSizing:
    """Tests for position sizing calculations."""

    def test_calculate_position_size_basic(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test basic position size calculation."""
        result = risk_manager.calculate_position_size(
            account=sample_account,
            stop_loss_pips=Decimal("20"),
            pip_value=Decimal("0.0001"),
            risk_percent=Decimal("1.0"),
        )

        assert isinstance(result, PositionSizeResult)
        assert result.size > 0
        assert result.risk_amount == Decimal("100.00")  # 1% of 10000
        assert result.risk_percent == Decimal("1.0")

    def test_calculate_position_size_zero_stop(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test position sizing with zero stop loss returns zero."""
        result = risk_manager.calculate_position_size(
            account=sample_account,
            stop_loss_pips=Decimal("0"),
            pip_value=Decimal("0.0001"),
        )

        assert result.size == Decimal("0")


class TestOrderValidation:
    """Tests for order validation."""

    def test_validate_order_without_stop_loss(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test that orders without stop loss are rejected."""
        order = OrderRequest(
            symbol="EUR_USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=Decimal("10000"),
            stop_loss=None,  # No stop loss
        )

        result = risk_manager.validate_order(
            order=order,
            account=sample_account,
            open_positions=[],
            current_price=Decimal("1.1000"),
        )

        assert result.is_valid is False
        assert "stop loss" in result.message.lower()

    def test_validate_order_max_positions_reached(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test that orders are rejected when max positions reached."""
        # Create 5 existing positions (max)
        positions = [
            Position(
                position_id=f"pos-{i}",
                symbol=f"PAIR_{i}",
                side=PositionSide.LONG,
                size=Decimal("1000"),
                entry_price=Decimal("1.0"),
                current_price=Decimal("1.0"),
                unrealized_pnl=Decimal("0"),
                margin_used=Decimal("50"),
            )
            for i in range(5)
        ]

        order = OrderRequest(
            symbol="EUR_USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=Decimal("10000"),
            stop_loss=Decimal("1.0900"),
        )

        result = risk_manager.validate_order(
            order=order,
            account=sample_account,
            open_positions=positions,
            current_price=Decimal("1.1000"),
        )

        assert result.is_valid is False
        assert "maximum positions" in result.message.lower()

    def test_validate_order_valid(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test valid order passes validation."""
        order = OrderRequest(
            symbol="EUR_USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=Decimal("10000"),
            stop_loss=Decimal("1.0900"),
        )

        result = risk_manager.validate_order(
            order=order,
            account=sample_account,
            open_positions=[],
            current_price=Decimal("1.1000"),
        )

        assert result.is_valid is True

    def test_validate_buy_order_stop_loss_above_price(
        self, risk_manager: RiskManager, sample_account: AccountInfo
    ):
        """Test buy order with stop loss above price is rejected."""
        order = OrderRequest(
            symbol="EUR_USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=Decimal("10000"),
            stop_loss=Decimal("1.1100"),  # Above current price
        )

        result = risk_manager.validate_order(
            order=order,
            account=sample_account,
            open_positions=[],
            current_price=Decimal("1.1000"),
        )

        assert result.is_valid is False
        assert "below" in result.message.lower()


class TestDailyLimits:
    """Tests for daily loss limits."""

    def test_daily_loss_limit_not_exceeded(
        self, risk_manager: RiskManager
    ):
        """Test when daily loss is within limits."""
        account = AccountInfo(
            account_id="test",
            balance=Decimal("10000"),
            equity=Decimal("9800"),
            margin_used=Decimal("0"),
            margin_available=Decimal("9800"),
            unrealized_pnl=Decimal("0"),
            realized_pnl_today=Decimal("-200"),  # 2% loss
            currency="USD",
        )

        # Should not be exceeded (2% < 5%)
        assert risk_manager._is_daily_loss_exceeded(account) is False

    def test_daily_loss_limit_exceeded(
        self, risk_manager: RiskManager
    ):
        """Test when daily loss exceeds limits."""
        account = AccountInfo(
            account_id="test",
            balance=Decimal("10000"),
            equity=Decimal("9400"),
            margin_used=Decimal("0"),
            margin_available=Decimal("9400"),
            unrealized_pnl=Decimal("0"),
            realized_pnl_today=Decimal("-600"),  # 6% loss
            currency="USD",
        )

        # Should be exceeded (6% > 5%)
        assert risk_manager._is_daily_loss_exceeded(account) is True
