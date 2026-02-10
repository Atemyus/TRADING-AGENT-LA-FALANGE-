"""
Admin routes for license and user management.
Only accessible by superusers.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.v1.routes.auth import get_current_user
from src.core.database import get_db
from src.core.models import License, LicenseStatus, User

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class LicenseCreate(BaseModel):
    """Create license request."""
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    max_uses: int = Field(1, ge=1, le=1000)
    expires_in_days: int | None = Field(None, ge=1, le=3650)  # Max 10 years


class LicenseUpdate(BaseModel):
    """Update license request."""
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    status: LicenseStatus | None = None
    max_uses: int | None = Field(None, ge=1, le=1000)
    expires_at: datetime | None = None


class LicenseResponse(BaseModel):
    """License response."""
    id: int
    key: str
    name: str | None
    description: str | None
    status: str
    is_active: bool
    max_uses: int
    current_uses: int
    expires_at: datetime | None
    created_at: datetime
    created_by: int | None
    is_valid: bool
    is_expired: bool

    class Config:
        from_attributes = True


class LicenseWithUsersResponse(LicenseResponse):
    """License response with user list."""
    users: list["UserBriefResponse"]


class UserBriefResponse(BaseModel):
    """Brief user info for license display."""
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserAdminResponse(BaseModel):
    """Full user info for admin."""
    id: int
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    license_id: int | None
    license_key: str | None = None
    license_expires_at: datetime | None = None
    license_activated_at: datetime | None
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_users: int
    active_users: int
    verified_users: int
    total_licenses: int
    active_licenses: int
    used_licenses: int
    expired_licenses: int


class BulkLicenseCreate(BaseModel):
    """Create multiple licenses at once."""
    count: int = Field(..., ge=1, le=100)
    name_prefix: str | None = Field(None, max_length=200)
    max_uses: int = Field(1, ge=1, le=1000)
    expires_in_days: int | None = Field(None, ge=1, le=3650)


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# ============================================================================
# Dependencies
# ============================================================================

async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure current user is a superuser/admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# License Routes
# ============================================================================

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics."""
    # User stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
    )
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.is_verified == True)  # noqa: E712
    )

    # License stats
    total_licenses = await db.scalar(select(func.count(License.id)))
    active_licenses = await db.scalar(
        select(func.count(License.id)).where(License.is_active == True)  # noqa: E712
    )
    used_licenses = await db.scalar(
        select(func.count(License.id)).where(License.current_uses > 0)
    )

    # Expired licenses
    now = datetime.now(UTC)
    expired_licenses = await db.scalar(
        select(func.count(License.id)).where(License.expires_at < now)
    )

    return AdminStatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        verified_users=verified_users or 0,
        total_licenses=total_licenses or 0,
        active_licenses=active_licenses or 0,
        used_licenses=used_licenses or 0,
        expired_licenses=expired_licenses or 0,
    )


@router.post("/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    data: LicenseCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new license."""
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=data.expires_in_days)

    license = License(
        key=License.generate_key(),
        name=data.name,
        description=data.description,
        max_uses=data.max_uses,
        expires_at=expires_at,
        created_by=admin.id,
        status=LicenseStatus.ACTIVE,
        is_active=True,
    )

    db.add(license)
    await db.flush()
    await db.refresh(license)

    return LicenseResponse(
        id=license.id,
        key=license.key,
        name=license.name,
        description=license.description,
        status=license.status,
        is_active=license.is_active,
        max_uses=license.max_uses,
        current_uses=license.current_uses,
        expires_at=license.expires_at,
        created_at=license.created_at,
        created_by=license.created_by,
        is_valid=license.is_valid,
        is_expired=license.is_expired,
    )


@router.post("/licenses/bulk", response_model=list[LicenseResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_licenses(
    data: BulkLicenseCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple licenses at once."""
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=data.expires_in_days)

    licenses = []
    for i in range(data.count):
        name = f"{data.name_prefix} #{i + 1}" if data.name_prefix else None
        license = License(
            key=License.generate_key(),
            name=name,
            max_uses=data.max_uses,
            expires_at=expires_at,
            created_by=admin.id,
            status=LicenseStatus.ACTIVE,
            is_active=True,
        )
        db.add(license)
        licenses.append(license)

    await db.flush()
    for license in licenses:
        await db.refresh(license)

    return [
        LicenseResponse(
            id=lic.id,
            key=lic.key,
            name=lic.name,
            description=lic.description,
            status=lic.status,
            is_active=lic.is_active,
            max_uses=lic.max_uses,
            current_uses=lic.current_uses,
            expires_at=lic.expires_at,
            created_at=lic.created_at,
            created_by=lic.created_by,
            is_valid=lic.is_valid,
            is_expired=lic.is_expired,
        )
        for lic in licenses
    ]


@router.get("/licenses", response_model=list[LicenseResponse])
async def list_licenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: LicenseStatus | None = None,
    show_expired: bool = True,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all licenses with optional filters."""
    query = select(License)

    if status_filter:
        query = query.where(License.status == status_filter)

    if not show_expired:
        now = datetime.now(UTC)
        query = query.where(
            (License.expires_at.is_(None)) | (License.expires_at > now)
        )

    query = query.order_by(License.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    licenses = result.scalars().all()

    return [
        LicenseResponse(
            id=lic.id,
            key=lic.key,
            name=lic.name,
            description=lic.description,
            status=lic.status,
            is_active=lic.is_active,
            max_uses=lic.max_uses,
            current_uses=lic.current_uses,
            expires_at=lic.expires_at,
            created_at=lic.created_at,
            created_by=lic.created_by,
            is_valid=lic.is_valid,
            is_expired=lic.is_expired,
        )
        for lic in licenses
    ]


@router.get("/licenses/{license_id}", response_model=LicenseWithUsersResponse)
async def get_license(
    license_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get license details with associated users."""
    result = await db.execute(
        select(License)
        .options(selectinload(License.users))
        .where(License.id == license_id)
    )
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    return LicenseWithUsersResponse(
        id=license.id,
        key=license.key,
        name=license.name,
        description=license.description,
        status=license.status,
        is_active=license.is_active,
        max_uses=license.max_uses,
        current_uses=license.current_uses,
        expires_at=license.expires_at,
        created_at=license.created_at,
        created_by=license.created_by,
        is_valid=license.is_valid,
        is_expired=license.is_expired,
        users=[
            UserBriefResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                created_at=user.created_at,
            )
            for user in license.users
        ]
    )


@router.put("/licenses/{license_id}", response_model=LicenseResponse)
async def update_license(
    license_id: int,
    data: LicenseUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a license."""
    result = await db.execute(select(License).where(License.id == license_id))
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    if data.name is not None:
        license.name = data.name
    if data.description is not None:
        license.description = data.description
    if data.is_active is not None:
        license.is_active = data.is_active
    if data.status is not None:
        license.status = data.status
    if data.max_uses is not None:
        license.max_uses = data.max_uses
    if data.expires_at is not None:
        license.expires_at = data.expires_at

    await db.flush()
    await db.refresh(license)

    return LicenseResponse(
        id=license.id,
        key=license.key,
        name=license.name,
        description=license.description,
        status=license.status,
        is_active=license.is_active,
        max_uses=license.max_uses,
        current_uses=license.current_uses,
        expires_at=license.expires_at,
        created_at=license.created_at,
        created_by=license.created_by,
        is_valid=license.is_valid,
        is_expired=license.is_expired,
    )


@router.delete("/licenses/{license_id}", response_model=MessageResponse)
async def delete_license(
    license_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a license (only if not in use)."""
    result = await db.execute(
        select(License)
        .options(selectinload(License.users))
        .where(License.id == license_id)
    )
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    if license.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete license with {len(license.users)} active users. Revoke it instead."
        )

    await db.delete(license)
    await db.flush()

    return MessageResponse(message="License deleted successfully")


@router.post("/licenses/{license_id}/revoke", response_model=LicenseResponse)
async def revoke_license(
    license_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a license (deactivates all users using it)."""
    result = await db.execute(
        select(License)
        .options(selectinload(License.users))
        .where(License.id == license_id)
    )
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )

    license.status = LicenseStatus.REVOKED
    license.is_active = False

    # Deactivate all users with this license
    for user in license.users:
        user.is_active = False

    await db.flush()
    await db.refresh(license)

    return LicenseResponse(
        id=license.id,
        key=license.key,
        name=license.name,
        description=license.description,
        status=license.status,
        is_active=license.is_active,
        max_uses=license.max_uses,
        current_uses=license.current_uses,
        expires_at=license.expires_at,
        created_at=license.created_at,
        created_by=license.created_by,
        is_valid=license.is_valid,
        is_expired=license.is_expired,
    )


# ============================================================================
# User Management Routes
# ============================================================================

@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    licensed_only: bool = False,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users with their license info."""
    query = select(User).options(selectinload(User.license))

    if licensed_only:
        query = query.where(User.license_id.isnot(None))

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        UserAdminResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            license_id=user.license_id,
            license_key=user.license.key if user.license else None,
            license_expires_at=user.license.expires_at if user.license else None,
            license_activated_at=user.license_activated_at,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]


@router.put("/users/{user_id}/toggle-active", response_model=UserAdminResponse)
async def toggle_user_active(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle user active status."""
    result = await db.execute(
        select(User).options(selectinload(User.license)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )

    user.is_active = not user.is_active
    await db.flush()
    await db.refresh(user)

    return UserAdminResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        license_id=user.license_id,
        license_key=user.license.key if user.license else None,
        license_expires_at=user.license.expires_at if user.license else None,
        license_activated_at=user.license_activated_at,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.put("/users/{user_id}/toggle-superuser", response_model=UserAdminResponse)
async def toggle_user_superuser(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle user superuser/admin status."""
    result = await db.execute(
        select(User).options(selectinload(User.license)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin status"
        )

    user.is_superuser = not user.is_superuser
    await db.flush()
    await db.refresh(user)

    return UserAdminResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        license_id=user.license_id,
        license_key=user.license.key if user.license else None,
        license_expires_at=user.license.expires_at if user.license else None,
        license_activated_at=user.license_activated_at,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user."""
    result = await db.execute(
        select(User).options(selectinload(User.license)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Free up the license slot
    if user.license:
        user.license.current_uses = max(0, user.license.current_uses - 1)

    await db.delete(user)
    await db.flush()

    return MessageResponse(message="User deleted successfully")
