"""
Authentication routes.
Handles user registration, login, token refresh, email verification, and password reset.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.core.email import (
    email_service,
    generate_verification_token,
    get_token_expiry,
)
from src.core.models import License, LicenseStatus, User
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ============================================================================
# Request/Response Models
# ============================================================================

class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = None
    license_key: str = Field(..., min_length=10, max_length=64, description="Valid license key required for registration")


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response (public info)."""
    id: int
    email: str
    username: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    password: str = Field(..., min_length=8, max_length=100)


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""
    email: EmailStr


# ============================================================================
# Dependencies
# ============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = verify_token(token, token_type="access")
    if user_id is None:
        raise credentials_exception

    # Load user with license relationship
    result = await db.execute(
        select(User)
        .options(selectinload(User.license))
        .where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user, ensuring they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_licensed_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they have a valid license.
    Use this dependency for routes that require an active license.
    Superusers bypass license check.
    """
    # Superusers bypass license check
    if current_user.is_superuser:
        return current_user

    if not current_user.license_id or not current_user.license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No license associated with this account"
        )

    license = current_user.license

    if not license.is_active or license.status != LicenseStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your license has been revoked"
        )

    if license.is_expired:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your license has expired. Please contact support."
        )

    return current_user


# ============================================================================
# Routes
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and send verification email.

    - **email**: Valid email address (must be unique)
    - **username**: Username (3-50 chars, alphanumeric + underscore)
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    - **license_key**: Valid license key (required)
    """
    # Validate license key first
    result = await db.execute(
        select(License).where(License.key == user_data.license_key.strip().upper())
    )
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid license key"
        )

    if not license.is_active or license.status != LicenseStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License is not active"
        )

    if license.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License has expired"
        )

    if license.current_uses >= license.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License has reached maximum number of users"
        )

    normalized_email = user_data.email.strip().lower()

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == normalized_email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Generate verification token
    verification_token = generate_verification_token()

    # Create new user with license
    user = User(
        email=normalized_email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=get_token_expiry(hours=24),
        license_id=license.id,
        license_activated_at=datetime.now(UTC),
    )

    # Increment license usage
    license.current_uses += 1

    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Send verification email in background
    background_tasks.add_task(
        email_service.send_verification_email,
        to=user.email,
        token=verification_token,
        username=user.username
    )

    return user


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: VerifyEmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user's email address with the token sent via email.
    """
    # Find user with this verification token
    result = await db.execute(
        select(User).where(User.verification_token == data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Check if token is expired
    if user.verification_token_expires and user.verification_token_expires < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )

    # Verify the user
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await db.flush()

    # Send welcome email in background
    background_tasks.add_task(
        email_service.send_welcome_email,
        to=user.email,
        username=user.username
    )

    return MessageResponse(message="Email verified successfully! You can now access all features.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email.
    """
    normalized_email = data.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return MessageResponse(message="If an account exists with this email, a verification link has been sent.")

    if user.is_verified:
        return MessageResponse(message="Email is already verified.")

    # Generate new verification token
    verification_token = generate_verification_token()
    user.verification_token = verification_token
    user.verification_token_expires = get_token_expiry(hours=24)
    await db.flush()

    # Send verification email
    background_tasks.add_task(
        email_service.send_verification_email,
        to=user.email,
        token=verification_token,
        username=user.username
    )

    return MessageResponse(message="If an account exists with this email, a verification link has been sent.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset email.
    """
    normalized_email = data.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return MessageResponse(message="If an account exists with this email, a password reset link has been sent.")

    # Generate reset token
    reset_token = generate_verification_token()
    user.reset_token = reset_token
    user.reset_token_expires = get_token_expiry(hours=1)  # 1 hour for password reset
    await db.flush()

    # Send reset email
    background_tasks.add_task(
        email_service.send_password_reset_email,
        to=user.email,
        token=reset_token,
        username=user.username
    )

    return MessageResponse(message="If an account exists with this email, a password reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using the token sent via email.
    """
    result = await db.execute(
        select(User).where(User.reset_token == data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token is expired
    if user.reset_token_expires and user.reset_token_expires < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Update password
    user.hashed_password = get_password_hash(data.password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.flush()

    return MessageResponse(message="Password reset successfully! You can now login with your new password.")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email/username and password.
    Returns JWT access and refresh tokens.
    """
    username_or_email = form_data.username.strip()
    if "@" in username_or_email:
        username_or_email = username_or_email.lower()

    result = await db.execute(
        select(User).where(
            (User.email == username_or_email) | (User.username == username_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with JSON body (alternative to form-data).
    """
    normalized_email = credentials.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    user_id = verify_token(token_data.refresh_token, token_type="refresh")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    full_name: str | None = None,
    avatar_url: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    if full_name is not None:
        current_user.full_name = full_name
    if avatar_url is not None:
        current_user.avatar_url = avatar_url

    await db.flush()
    await db.refresh(current_user)

    return current_user


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout the current user."""
    return MessageResponse(message="Successfully logged out")


# Legacy endpoint
@router.post("/token", response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Legacy token endpoint."""
    return await login(form_data, db)
