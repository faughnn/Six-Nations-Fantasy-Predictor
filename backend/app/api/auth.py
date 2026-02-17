from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    GoogleAuthRequest,
    AuthResponse,
    UserResponse,
)

router = APIRouter()


async def _record_login(user: User, db: AsyncSession) -> None:
    """Bump login_count and set last_login_at."""
    user.login_count = (user.login_count or 0) + 1
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
        login_count=1,
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await _record_login(user, db)
    token = create_access_token(user.id, user.email)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/google", response_model=AuthResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with Google ID token (from Sign In With Google button)."""
    import httpx

    settings = get_settings()

    # Verify the Google ID token
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={body.credential}"
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    google_data = resp.json()

    # Verify the token was intended for our app
    if google_data.get("aud") != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not intended for this application",
        )

    google_id = google_data["sub"]
    email = google_data["email"]
    name = google_data.get("name", email.split("@")[0])
    avatar = google_data.get("picture")

    # Check if user exists by google_id
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Check if email already exists (link accounts)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is not None:
            # Link Google to existing email account
            user.google_id = google_id
            user.avatar_url = avatar or user.avatar_url
        else:
            # Create new user
            user = User(
                email=email,
                name=name,
                google_id=google_id,
                avatar_url=avatar,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

    await _record_login(user, db)
    token = create_access_token(user.id, user.email)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.get("/admin/metrics")
async def get_user_metrics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Admin-only endpoint returning user metrics."""
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    total = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    active_7d = (await db.execute(
        select(func.count()).select_from(User).where(User.last_login_at >= seven_days_ago)
    )).scalar() or 0
    active_30d = (await db.execute(
        select(func.count()).select_from(User).where(User.last_login_at >= thirty_days_ago)
    )).scalar() or 0
    new_7d = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= seven_days_ago)
    )).scalar() or 0

    # Recent users list
    result = await db.execute(
        select(User).order_by(User.last_login_at.desc().nullslast()).limit(20)
    )
    users = result.scalars().all()

    return {
        "total_users": total,
        "active_7d": active_7d,
        "active_30d": active_30d,
        "new_signups_7d": new_7d,
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "login_count": u.login_count or 0,
                "is_admin": u.is_admin,
                "auth_method": "google" if u.google_id else "email",
            }
            for u in users
        ],
    }
