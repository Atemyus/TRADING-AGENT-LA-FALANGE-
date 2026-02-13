from fastapi import Header, HTTPException, status

from src.config import get_settings


def _extract_bearer(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    value = auth_header.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip() or None
    return value or None


async def verify_bridge_api_key(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_bridge_key: str | None = Header(default=None, alias="X-Bridge-Key"),
):
    settings = get_settings()
    expected = (settings.MT_BRIDGE_API_KEY or "").strip()
    if not expected:
        return

    provided = _extract_bearer(authorization) or (x_bridge_key or "").strip() or None
    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bridge API key",
        )
