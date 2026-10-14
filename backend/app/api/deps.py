
from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the user represented by the access token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise credentials_error from None

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_roles(*allowed_roles: str):
    """Create a dependency that allows only specified roles."""

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        active_roles = {
            association.role.name
            for association in current_user.user_roles
            if association.role and association.role.is_active
        }

        if not active_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return role_checker
